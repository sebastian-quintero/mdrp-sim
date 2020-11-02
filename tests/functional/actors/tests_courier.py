import random
import unittest
from datetime import time
from unittest.mock import patch

from simpy import Environment

import settings
from actors.courier import Courier
from actors.dispatcher import Dispatcher
from actors.user import User
from objects.location import Location
from objects.notification import Notification, NotificationType
from objects.order import Order
from objects.route import Route
from objects.stop import Stop, StopType
from objects.vehicle import Vehicle
from policies.courier.acceptance.random_uniform import UniformAcceptancePolicy
from policies.courier.movement.osrm import OSRMMovementPolicy
from policies.courier.movement_evaluation.geohash_neighbors import NeighborsMoveEvalPolicy
from tests.test_utils import DummyMatchingPolicy, mocked_get_route
from utils.datetime_utils import min_to_sec, hour_to_sec, sec_to_hour, time_diff


class TestsCourier(unittest.TestCase):
    """Tests for the Courier actor class"""

    # Properties to be reused
    courier_id = 56
    vehicle = Vehicle.MOTORCYCLE
    start_location = Location(lat=4.697893, lng=-74.051565)

    order_id = 0
    pick_up_at = Location(lat=4.689697, lng=-74.055495)
    drop_off_at = Location(lat=4.690296, lng=-74.043929)
    placement_time = time(12, 0, 0)
    expected_drop_off_time = time(12, 40, 0)
    preparation_time = time(12, 2, 0)
    ready_time = time(12, 12, 0)

    # Services to be reused
    acceptance_policy = UniformAcceptancePolicy()
    movement_evaluation_policy = NeighborsMoveEvalPolicy()
    movement_policy = OSRMMovementPolicy()

    @patch('settings.COURIER_MOVEMENT_PROBABILITY', 0.01)
    @patch('services.osrm_service.OSRMService.get_route', side_effect=mocked_get_route)
    def test_always_idle(self, osrm):
        """Test to evaluate a courier never moving"""

        # Constants
        random.seed(187)
        on_time = time(0, 0, 0)
        off_time = time(5, 0, 0)

        # Services
        env = Environment()
        dispatcher = Dispatcher(env=env, matching_policy=DummyMatchingPolicy())

        # Creates a courier and runs a simulation
        courier = Courier(
            acceptance_policy=self.acceptance_policy,
            dispatcher=dispatcher,
            env=env,
            movement_evaluation_policy=self.movement_evaluation_policy,
            movement_policy=self.movement_policy,
            courier_id=self.courier_id,
            vehicle=self.vehicle,
            location=self.start_location,
            on_time=on_time,
            off_time=off_time
        )
        env.run(until=hour_to_sec(4))

        # Asserts that the courier is idle and never moved
        self.assertEqual(courier.state, 'idle')
        self.assertEqual(courier.location, self.start_location)
        self.assertIn(courier.courier_id, dispatcher.idle_couriers.keys())

    @patch('services.osrm_service.OSRMService.get_route', side_effect=mocked_get_route)
    @patch('settings.COURIER_MOVEMENT_PROBABILITY', 0.95)
    @patch('settings.COURIER_WAIT_TO_MOVE', min_to_sec(7))
    def test_movement_process(self, osrm):
        """Test to evaluate how a courier moves with dummy movement"""

        # Constants
        random.seed(365)
        on_time = time(0, 0, 0)
        off_time = time(5, 0, 0)

        env = Environment()
        dispatcher = Dispatcher(env=env, matching_policy=DummyMatchingPolicy())

        # Creates a courier and runs a simulation
        courier = Courier(
            acceptance_policy=self.acceptance_policy,
            dispatcher=dispatcher,
            env=env,
            movement_evaluation_policy=self.movement_evaluation_policy,
            movement_policy=self.movement_policy,
            courier_id=self.courier_id,
            vehicle=self.vehicle,
            location=self.start_location,
            on_time=on_time,
            off_time=off_time
        )
        env.run(until=hour_to_sec(4) + min_to_sec(5))

        # Asserts that the courier moved and is is in a different location
        self.assertEqual(courier.state, 'moving')
        self.assertNotEqual(courier.location, self.start_location)
        self.assertIn(courier.courier_id, dispatcher.moving_couriers.keys())

    @patch('services.osrm_service.OSRMService.get_route', side_effect=mocked_get_route)
    @patch('settings.COURIER_MOVEMENT_PROBABILITY', 0.1)
    @patch('settings.COURIER_MIN_ACCEPTANCE_RATE', 0.99)
    def test_notify_event_accept_idle(self, osrm):
        """Test to evaluate how a courier handles a notification while being idle and accepts it"""

        # Constants
        random.seed(126)
        initial_time = hour_to_sec(12)
        time_delta = min_to_sec(40)
        on_time = time(12, 0, 0)
        off_time = time(13, 0, 0)

        # Services
        env = Environment(initial_time=initial_time)
        dispatcher = Dispatcher(env=env, matching_policy=DummyMatchingPolicy())

        # Creates a courier with high acceptance rate and immediately send a new instruction, composed of a single order
        courier = Courier(
            acceptance_policy=self.acceptance_policy,
            dispatcher=dispatcher,
            env=env,
            movement_evaluation_policy=self.movement_evaluation_policy,
            movement_policy=self.movement_policy,
            courier_id=self.courier_id,
            vehicle=self.vehicle,
            location=self.start_location,
            acceptance_rate=0.99,
            on_time=on_time,
            off_time=off_time
        )

        order = Order(
            order_id=self.order_id,
            drop_off_at=self.drop_off_at,
            pick_up_at=self.pick_up_at,
            placement_time=self.placement_time,
            expected_drop_off_time=self.expected_drop_off_time,
            preparation_time=self.preparation_time,
            ready_time=self.ready_time,
            user=User(env=env)
        )
        dispatcher.unassigned_orders[order.order_id] = order
        instruction = Route(
            orders={self.order_id: order},
            stops=[
                Stop(
                    location=self.pick_up_at,
                    position=0,
                    orders={self.order_id: order},
                    type=StopType.PICK_UP,
                    visited=False
                ),
                Stop(
                    location=self.drop_off_at,
                    position=1,
                    orders={self.order_id: order},
                    type=StopType.DROP_OFF,
                    visited=False
                )
            ]
        )
        notification = Notification(
            courier=courier,
            instruction=instruction
        )
        env.process(courier.notification_event(notification))
        env.run(until=initial_time + time_delta)

        # Asserts that the courier fulfilled the route and is at a different start location
        self.assertIsNotNone(order.pick_up_time)
        self.assertIsNotNone(order.drop_off_time)
        self.assertEqual(order.courier_id, courier.courier_id)
        self.assertTrue(order.pick_up_time < order.drop_off_time)
        self.assertIsNone(courier.active_route)
        self.assertIsNone(courier.active_stop)
        self.assertEqual(dispatcher.fulfilled_orders, {order.order_id: order})
        self.assertEqual(order.state, 'dropped_off')
        self.assertNotEqual(courier.location, self.start_location)
        self.assertEqual(courier.state, 'idle')
        self.assertIn(courier.courier_id, dispatcher.idle_couriers.keys())

    @patch('services.osrm_service.OSRMService.get_route', side_effect=mocked_get_route)
    @patch('settings.COURIER_MOVEMENT_PROBABILITY', 0.1)
    @patch('settings.COURIER_MIN_ACCEPTANCE_RATE', 0.99)
    def test_notify_event_reject_idle(self, osrm):
        """Test to evaluate how a courier handles a notification while being idle and rejects it"""

        # Constants
        random.seed(122)
        on_time = time(12, 0, 0)
        off_time = time(15, 0, 0)

        # Services
        env = Environment(initial_time=hour_to_sec(12))
        dispatcher = Dispatcher(env=env, matching_policy=DummyMatchingPolicy())

        # Creates a courier with low acceptance rate and immediately send a new instruction, composed of a single order
        courier = Courier(
            acceptance_policy=self.acceptance_policy,
            dispatcher=dispatcher,
            env=env,
            movement_evaluation_policy=self.movement_evaluation_policy,
            movement_policy=self.movement_policy,
            courier_id=self.courier_id,
            vehicle=self.vehicle,
            location=self.start_location,
            acceptance_rate=0.01,
            on_time=on_time,
            off_time=off_time
        )

        order = Order(
            order_id=self.order_id,
            drop_off_at=self.drop_off_at,
            pick_up_at=self.pick_up_at,
            placement_time=self.placement_time,
            expected_drop_off_time=self.expected_drop_off_time,
            preparation_time=self.preparation_time,
            ready_time=self.ready_time
        )
        dispatcher.unassigned_orders[order.order_id] = order
        instruction = Route(
            orders={self.order_id: order},
            stops=[
                Stop(
                    location=self.pick_up_at,
                    position=0,
                    orders={self.order_id: order},
                    type=StopType.PICK_UP,
                    visited=False
                ),
                Stop(
                    location=self.drop_off_at,
                    position=1,
                    orders={self.order_id: order},
                    type=StopType.DROP_OFF,
                    visited=False
                )
            ]
        )
        notification = Notification(
            courier=courier,
            instruction=instruction
        )
        env.process(courier.notification_event(notification))
        env.run(until=hour_to_sec(14))

        # Asserts that the courier didn't fulfill the route
        self.assertIsNone(order.pick_up_time)
        self.assertIsNone(order.drop_off_time)
        self.assertIsNone(order.courier_id)
        self.assertIsNone(courier.active_route)
        self.assertIsNone(courier.active_stop)
        self.assertIn(courier.courier_id, order.rejected_by)
        self.assertIn(order.order_id, courier.rejected_orders)
        self.assertEqual(dispatcher.unassigned_orders, {order.order_id: order})
        self.assertEqual(order.state, 'unassigned')
        self.assertEqual(courier.location, self.start_location)
        self.assertEqual(courier.state, 'idle')
        self.assertIn(courier.courier_id, dispatcher.idle_couriers.keys())

    @patch('services.osrm_service.OSRMService.get_route', side_effect=mocked_get_route)
    @patch('settings.COURIER_MOVEMENT_PROBABILITY', 0.99)
    @patch('settings.COURIER_MIN_ACCEPTANCE_RATE', 0.99)
    def test_notify_event_accept_picking_up(self, osrm):
        """Test to evaluate how a courier handles a notification while picking up and accepts it"""

        # Constants
        random.seed(183)
        on_time = time(12, 0, 0)
        off_time = time(15, 0, 0)

        # Services
        env = Environment(initial_time=hour_to_sec(12) + min_to_sec(12))
        dispatcher = Dispatcher(env=env, matching_policy=DummyMatchingPolicy())

        # Creates a courier with high acceptance rate, an active route and in process of picking up.
        # Sends a new instruction, composed of a single new order
        active_order = Order(
            order_id=self.order_id,
            drop_off_at=self.drop_off_at,
            pick_up_at=self.pick_up_at,
            placement_time=self.placement_time,
            expected_drop_off_time=self.expected_drop_off_time,
            preparation_time=self.preparation_time,
            ready_time=self.ready_time,
            courier_id=self.courier_id,
            user=User(env=env)
        )
        dispatcher.assigned_orders[active_order.order_id] = active_order
        new_order = Order(
            order_id=17,
            drop_off_at=Location(lat=4.694627, lng=-74.038886),
            pick_up_at=self.pick_up_at,
            placement_time=self.placement_time,
            expected_drop_off_time=self.expected_drop_off_time,
            preparation_time=self.preparation_time,
            ready_time=self.ready_time,
            user=User(env=env)
        )
        dispatcher.unassigned_orders[new_order.order_id] = new_order
        courier = Courier(
            acceptance_policy=self.acceptance_policy,
            dispatcher=dispatcher,
            env=env,
            movement_evaluation_policy=self.movement_evaluation_policy,
            movement_policy=self.movement_policy,
            courier_id=self.courier_id,
            vehicle=self.vehicle,
            location=active_order.pick_up_at,
            acceptance_rate=0.99,
            active_route=Route(
                orders={self.order_id: active_order},
                stops=[
                    Stop(
                        location=self.pick_up_at,
                        position=0,
                        orders={self.order_id: active_order},
                        type=StopType.PICK_UP,
                        visited=False
                    ),
                    Stop(
                        location=self.drop_off_at,
                        position=1,
                        orders={self.order_id: active_order},
                        type=StopType.DROP_OFF,
                        visited=False
                    )
                ]
            ),
            on_time=on_time,
            off_time=off_time
        )

        instruction = [Stop(
            location=new_order.drop_off_at,
            position=1,
            orders={new_order.order_id: new_order},
            type=StopType.DROP_OFF,
            visited=False
        )]
        notification = Notification(
            courier=courier,
            instruction=instruction
        )
        courier.process.interrupt()
        courier.active_stop = courier.active_route.stops[0]
        courier.process = env.process(courier._picking_up_process(orders={active_order.order_id: active_order}))
        env.process(courier.notification_event(notification))
        env.run(until=hour_to_sec(13) + min_to_sec(12))

        # Asserts that the courier fulfilled the active and new order and is at a different start location
        self.assertIsNotNone(active_order.pick_up_time)
        self.assertIsNotNone(active_order.drop_off_time)
        self.assertEqual(active_order.courier_id, courier.courier_id)
        self.assertTrue(active_order.pick_up_time < active_order.drop_off_time)
        self.assertEqual(active_order.state, 'dropped_off')

        self.assertIsNotNone(new_order.pick_up_time)
        self.assertIsNotNone(new_order.drop_off_time)
        self.assertEqual(new_order.courier_id, courier.courier_id)
        self.assertTrue(new_order.pick_up_time < new_order.drop_off_time)
        self.assertEqual(new_order.state, 'dropped_off')

        self.assertIsNone(courier.active_route)
        self.assertIsNone(courier.active_stop)
        self.assertNotEqual(courier.location, self.start_location)
        self.assertEqual(
            dispatcher.fulfilled_orders,
            {
                active_order.order_id: active_order,
                new_order.order_id: new_order
            }
        )
        self.assertEqual(courier.state, 'moving')
        self.assertIn(courier.courier_id, dispatcher.moving_couriers.keys())

    @patch('services.osrm_service.OSRMService.get_route', side_effect=mocked_get_route)
    @patch('settings.COURIER_MOVEMENT_PROBABILITY', 0.01)
    @patch('settings.COURIER_MIN_ACCEPTANCE_RATE', 0.99)
    def test_notify_event_reject_picking_up(self, osrm):
        """Test to evaluate how a courier handles a notification while picking up and rejects it"""

        # Constants
        random.seed(4747474)
        on_time = time(12, 0, 0)
        off_time = time(15, 0, 0)

        # Services
        env = Environment(initial_time=hour_to_sec(12) + min_to_sec(12))
        dispatcher = Dispatcher(env=env, matching_policy=DummyMatchingPolicy())

        # Creates a courier with low acceptance rate, an active route and in process of picking up.
        # Sends a new instruction, composed of a single new order
        active_order = Order(
            order_id=self.order_id,
            drop_off_at=self.drop_off_at,
            pick_up_at=self.pick_up_at,
            placement_time=self.placement_time,
            expected_drop_off_time=self.expected_drop_off_time,
            preparation_time=self.preparation_time,
            ready_time=self.ready_time,
            courier_id=self.courier_id,
            user=User(env=env)
        )
        dispatcher.assigned_orders[active_order.order_id] = active_order
        new_order = Order(
            order_id=17,
            drop_off_at=Location(lat=4.694627, lng=-74.038886),
            pick_up_at=self.pick_up_at,
            placement_time=self.placement_time,
            expected_drop_off_time=self.expected_drop_off_time,
            preparation_time=self.preparation_time,
            ready_time=self.ready_time,
            user=User(env=env)
        )
        dispatcher.unassigned_orders[new_order.order_id] = new_order
        courier = Courier(
            acceptance_policy=self.acceptance_policy,
            dispatcher=dispatcher,
            env=env,
            movement_evaluation_policy=self.movement_evaluation_policy,
            movement_policy=self.movement_policy,
            courier_id=self.courier_id,
            vehicle=self.vehicle,
            location=active_order.pick_up_at,
            acceptance_rate=0.01,
            active_route=Route(
                orders={self.order_id: active_order},
                stops=[
                    Stop(
                        location=self.pick_up_at,
                        position=0,
                        orders={self.order_id: active_order},
                        type=StopType.PICK_UP,
                        visited=False
                    ),
                    Stop(
                        location=self.drop_off_at,
                        position=1,
                        orders={self.order_id: active_order},
                        type=StopType.DROP_OFF,
                        visited=False
                    )
                ]
            ),
            on_time=on_time,
            off_time=off_time
        )

        instruction = Stop(
            location=new_order.drop_off_at,
            position=1,
            orders={new_order.order_id: new_order},
            type=StopType.DROP_OFF,
            visited=False
        )
        notification = Notification(
            courier=courier,
            instruction=instruction
        )
        courier.process.interrupt()
        courier.active_stop = courier.active_route.stops[0]
        courier.process = env.process(courier._picking_up_process(orders={active_order.order_id: active_order}))
        env.process(courier.notification_event(notification))
        env.run(until=hour_to_sec(14))

        # Asserts:
        # - the courier didn't fulfill the new order,
        # - fulfilled the active order and
        # - is at a different start location.
        self.assertIsNone(new_order.pick_up_time)
        self.assertIsNone(new_order.drop_off_time)
        self.assertIsNone(new_order.courier_id)
        self.assertIn(courier.courier_id, new_order.rejected_by)
        self.assertIn(new_order.order_id, courier.rejected_orders)
        self.assertEqual(new_order.state, 'unassigned')

        self.assertIsNotNone(active_order.pick_up_time)
        self.assertIsNotNone(active_order.drop_off_time)
        self.assertEqual(active_order.courier_id, courier.courier_id)
        self.assertTrue(active_order.pick_up_time < active_order.drop_off_time)
        self.assertEqual(active_order.state, 'dropped_off')

        self.assertIsNone(courier.active_route)
        self.assertIsNone(courier.active_stop)
        self.assertNotEqual(courier.location, self.start_location)
        self.assertEqual(dispatcher.fulfilled_orders, {active_order.order_id: active_order})
        self.assertEqual(dispatcher.unassigned_orders, {new_order.order_id: new_order})
        self.assertEqual(courier.state, 'idle')
        self.assertIn(courier.courier_id, dispatcher.idle_couriers.keys())

    @patch('settings.COURIER_MOVEMENT_PROBABILITY', 0.01)
    def test_log_off(self):
        """Test to evaluate the scheduling of the courier logging off works correctly"""

        # Constants
        random.seed(888)
        on_time = time(8, 0, 0)
        off_time = time(14, 0, 0)
        initial_time = hour_to_sec(8)

        # Verifies for two test cases the scheduling of the courier logging off works correctly.
        # In one case, the courier log off event doesn't yet happen. In the other test, it does

        # Test 1: the courier achieves the log off after a given time
        env = Environment(initial_time=initial_time)
        dispatcher = Dispatcher(env=env, matching_policy=DummyMatchingPolicy())
        courier = Courier(
            env=env,
            dispatcher=dispatcher,
            courier_id=84,
            on_time=on_time,
            off_time=off_time
        )
        env.run(until=initial_time + hour_to_sec(10))
        self.assertEqual(dispatcher.logged_off_couriers, {courier.courier_id: courier})
        self.assertEqual(dispatcher.idle_couriers, {})
        self.assertEqual(courier.state, 'logged_off')

        # Test 2: the courier doesn't achieve the log off because the simulation ends before
        env = Environment(initial_time=initial_time)
        dispatcher = Dispatcher(env=env, matching_policy=DummyMatchingPolicy())
        courier = Courier(
            env=env,
            dispatcher=dispatcher,
            courier_id=84,
            on_time=on_time,
            off_time=off_time
        )
        env.run(until=initial_time + hour_to_sec(2))
        self.assertEqual(dispatcher.idle_couriers, {courier.courier_id: courier})
        self.assertEqual(dispatcher.logged_off_couriers, {})
        self.assertEqual(courier.state, 'idle')

    @patch('settings.COURIER_EARNINGS_PER_ORDER', 3)
    @patch('settings.COURIER_EARNINGS_PER_HOUR', 8)
    @patch('settings.COURIER_MOVEMENT_PROBABILITY', 0.01)
    def test_calculate_earnings(self):
        """Test to verify the mechanics of calculating the shift's earnings"""

        # Constants
        random.seed(523)
        on_time = time(0, 0, 0)
        off_time = time(2, 0, 0)

        # Services
        env = Environment()

        # Creates a two hour - shift courier
        courier = Courier(env=env, on_time=on_time, off_time=off_time)

        # Verifies for two scenarios how the earnings are calculated.
        # In the first test, raw earnings from orders are chosen.
        # In the second test, the hourly earnings rate is chosen.

        # Test 1. Creates courier earnings to select the raw earnings from orders.
        # Asserts that these earnings are selected over the hourly earnings rate
        courier.fulfilled_orders = [Order()] * 7
        courier.earnings = courier._calculate_earnings()
        self.assertEqual(courier.earnings, len(courier.fulfilled_orders) * settings.COURIER_EARNINGS_PER_ORDER)

        # Test 2. Creates courier earnings to select the hourly earnings rate.
        # Asserts that these earnings are selected over the order earnings
        courier.fulfilled_orders = [Order()] * 2
        courier.earnings = courier._calculate_earnings()
        self.assertEqual(
            courier.earnings,
            sec_to_hour(time_diff(courier.off_time, courier.on_time)) * settings.COURIER_EARNINGS_PER_HOUR
        )

    @patch('services.osrm_service.OSRMService.get_route', side_effect=mocked_get_route)
    @patch('settings.COURIER_MOVEMENT_PROBABILITY', 0.1)
    def test_notify_prepositioning_event_accept_idle(self, osrm):
        """Test to evaluate how a courier handles a prepositioning notification while being idle and accepts it"""

        # Constants
        random.seed(348)
        initial_time = hour_to_sec(17)
        time_delta = min_to_sec(10)
        on_time = time(17, 0, 0)
        off_time = time(17, 30, 0)

        # Services
        env = Environment(initial_time=initial_time)
        dispatcher = Dispatcher(env=env, matching_policy=DummyMatchingPolicy())

        # Creates a courier with high acceptance rate and immediately send a prepositioning notification
        courier = Courier(
            acceptance_policy=self.acceptance_policy,
            dispatcher=dispatcher,
            env=env,
            movement_evaluation_policy=self.movement_evaluation_policy,
            movement_policy=self.movement_policy,
            courier_id=self.courier_id,
            vehicle=self.vehicle,
            location=self.start_location,
            acceptance_rate=0.99,
            on_time=on_time,
            off_time=off_time
        )

        instruction = Route(
            orders=None,
            stops=[
                Stop(
                    location=self.pick_up_at,
                    position=0,
                    orders=None,
                    type=StopType.PREPOSITION,
                    visited=False
                )
            ]
        )
        notification = Notification(courier=courier, instruction=instruction, type=NotificationType.PREPOSITIONING)
        env.process(courier.notification_event(notification))
        env.run(until=initial_time + time_delta)

        # Asserts that the courier fulfilled the route and is at a different start location
        self.assertIsNone(courier.active_route)
        self.assertIsNone(courier.active_stop)
        self.assertEqual(dispatcher.fulfilled_orders, {})
        self.assertNotEqual(courier.location, self.start_location)
        self.assertEqual(courier.state, 'idle')
        self.assertIn(courier.courier_id, dispatcher.idle_couriers.keys())

    @patch('services.osrm_service.OSRMService.get_route', side_effect=mocked_get_route)
    @patch('settings.COURIER_MOVEMENT_PROBABILITY', 0.01)
    def test_notify_prepositioning_event_reject_idle(self, osrm):
        """Test to evaluate how a courier handles a prepositioning notification while being idle and rejects it"""

        # Constants
        random.seed(672)
        on_time = time(6, 0, 0)
        off_time = time(8, 0, 0)

        # Services
        env = Environment(initial_time=hour_to_sec(6))
        dispatcher = Dispatcher(env=env, matching_policy=DummyMatchingPolicy())

        # Creates a courier with low acceptance rate and immediately send a prepositioning notification
        courier = Courier(
            acceptance_policy=self.acceptance_policy,
            dispatcher=dispatcher,
            env=env,
            movement_evaluation_policy=self.movement_evaluation_policy,
            movement_policy=self.movement_policy,
            courier_id=self.courier_id,
            vehicle=self.vehicle,
            location=self.start_location,
            acceptance_rate=0.01,
            on_time=on_time,
            off_time=off_time
        )
        instruction = Route(
            orders=None,
            stops=[
                Stop(
                    location=self.pick_up_at,
                    position=0,
                    orders=None,
                    type=StopType.PREPOSITION,
                    visited=False
                )
            ]
        )
        notification = Notification(courier=courier, instruction=instruction, type=NotificationType.PREPOSITIONING)
        env.process(courier.notification_event(notification))
        env.run(until=hour_to_sec(7))

        # Asserts that the courier didn't fulfill the route
        self.assertIsNone(courier.active_route)
        self.assertIsNone(courier.active_stop)
        self.assertEqual(courier.location, self.start_location)
        self.assertEqual(courier.state, 'idle')
        self.assertIn(courier.courier_id, dispatcher.idle_couriers.keys())

    @patch('services.osrm_service.OSRMService.get_route', side_effect=mocked_get_route)
    @patch('settings.COURIER_MOVEMENT_PROBABILITY', 0.01)
    def test_pick_up_waiting_time(self, osrm):
        """Test to verify the mechanics of the waiting time are correctly designed"""

        # Constants
        random.seed(290)
        on_time = time(6, 0, 0)
        off_time = time(8, 0, 0)

        # Services
        env = Environment(initial_time=hour_to_sec(6))
        dispatcher = Dispatcher(env=env, matching_policy=DummyMatchingPolicy())

        # Creates a courier and sets it to pick up stuff
        courier = Courier(
            acceptance_policy=self.acceptance_policy,
            dispatcher=dispatcher,
            env=env,
            movement_evaluation_policy=self.movement_evaluation_policy,
            movement_policy=self.movement_policy,
            courier_id=self.courier_id,
            vehicle=self.vehicle,
            location=self.start_location,
            acceptance_rate=0.01,
            on_time=on_time,
            off_time=off_time
        )
        order = Order(ready_time=time(6, 15, 0), order_id=23)
        stop = Stop(orders={order.order_id: order}, type=StopType.PICK_UP)
        env.process(courier._execute_stop(stop))
        dispatcher.process.interrupt()

        # Run until there are no more events and assert the courier experienced waiting time.
        env.run(until=hour_to_sec(7))
        self.assertTrue(order.pick_up_time >= time(6, int(order.ready_time.minute + order.pick_up_service_time / 60)))

        # For another test, if the order's ready time has expired, the courier doesn't experience waiting time
        env = Environment(initial_time=hour_to_sec(6))
        dispatcher = Dispatcher(env=env, matching_policy=DummyMatchingPolicy())
        courier = Courier(
            acceptance_policy=self.acceptance_policy,
            dispatcher=dispatcher,
            env=env,
            movement_evaluation_policy=self.movement_evaluation_policy,
            movement_policy=self.movement_policy,
            courier_id=self.courier_id,
            vehicle=self.vehicle,
            location=self.start_location,
            acceptance_rate=0.01,
            on_time=on_time,
            off_time=off_time
        )
        order = Order(ready_time=time(4, 0, 0), order_id=23)
        stop = Stop(orders={order.order_id: order}, type=StopType.PICK_UP)
        env.process(courier._execute_stop(stop))
        dispatcher.process.interrupt()
        env.run(until=hour_to_sec(7))
        self.assertTrue(
            time(order.pick_up_time.hour, order.pick_up_time.minute) <= time(6, int(order.pick_up_service_time / 60))
        )
