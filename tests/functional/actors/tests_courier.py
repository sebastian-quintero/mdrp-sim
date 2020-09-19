import math
import random
import unittest
from datetime import time, datetime, date
from unittest import mock

from simpy import Environment

import settings
from actors.courier import Courier
from actors.dispatcher import Dispatcher
from actors.user import User
from objects.location import Location
from objects.notification import Notification
from objects.order import Order
from objects.route import Route
from objects.stop import Stop
from objects.vehicle import Vehicle
from policies.courier.acceptance.random_uniform import UniformAcceptancePolicy
from policies.courier.movement.osrm import OSRMMovementPolicy
from policies.courier.movement_evaluation.geohash_neighbors import NeighborsMoveEvalPolicy
from tests.test_utils import DummyMatchingPolicy, mocked_get_route
from utils.datetime_utils import min_to_sec, hour_to_sec


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

    @mock.patch('settings.COURIER_MOVEMENT_PROBABILITY', 0.01)
    @mock.patch('policies.courier.movement.osrm.OSRMMovementPolicy._get_route', side_effect=mocked_get_route)
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

    @mock.patch('policies.courier.movement.osrm.OSRMMovementPolicy._get_route', side_effect=mocked_get_route)
    @mock.patch('settings.COURIER_MOVEMENT_PROBABILITY', 0.95)
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
        env.run(until=hour_to_sec(4))

        # Asserts that the courier moved and is is in a different location
        self.assertEqual(courier.state, 'moving')
        self.assertNotEqual(courier.location, self.start_location)
        self.assertIn(courier.courier_id, dispatcher.busy_couriers.keys())

    @mock.patch('policies.courier.movement.osrm.OSRMMovementPolicy._get_route', side_effect=mocked_get_route)
    @mock.patch('settings.COURIER_MOVEMENT_PROBABILITY', 0.1)
    @mock.patch('settings.COURIER_MIN_ACCEPTANCE_RATE', 0.99)
    def test_notify_event_accept_idle(self, osrm):
        """Test to evaluate how a courier handles a notification while being idle and accepts it"""

        # Constants
        random.seed(126)
        initial_time = hour_to_sec(12)
        time_delta = min_to_sec(20)
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
            env=env,
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
                    type='pick_up',
                    visited=False
                ),
                Stop(
                    location=self.drop_off_at,
                    position=1,
                    orders={self.order_id: order},
                    type='drop_off',
                    visited=False
                )
            ]
        )
        notification = Notification(
            courier=courier,
            instruction=instruction
        )
        env.process(courier.notify_event(notification))
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

    @mock.patch('policies.courier.movement.osrm.OSRMMovementPolicy._get_route', side_effect=mocked_get_route)
    @mock.patch('settings.COURIER_MOVEMENT_PROBABILITY', 0.1)
    @mock.patch('settings.COURIER_MIN_ACCEPTANCE_RATE', 0.99)
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
            env=env,
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
                    type='pick_up',
                    visited=False
                ),
                Stop(
                    location=self.drop_off_at,
                    position=1,
                    orders={self.order_id: order},
                    type='drop_off',
                    visited=False
                )
            ]
        )
        notification = Notification(
            courier=courier,
            instruction=instruction
        )
        env.process(courier.notify_event(notification))
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

    @mock.patch('policies.courier.movement.osrm.OSRMMovementPolicy._get_route', side_effect=mocked_get_route)
    @mock.patch('settings.COURIER_MOVEMENT_PROBABILITY', 0.99)
    @mock.patch('settings.COURIER_MIN_ACCEPTANCE_RATE', 0.99)
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
            env=env,
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
            env=env,
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
                        type='pick_up',
                        visited=False
                    ),
                    Stop(
                        location=self.drop_off_at,
                        position=1,
                        orders={self.order_id: active_order},
                        type='drop_off',
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
            type='drop_off',
            visited=False
        )
        notification = Notification(
            courier=courier,
            instruction=instruction
        )
        courier.process.interrupt()
        courier.active_stop = courier.active_route.stops[0]
        courier.process = env.process(courier._picking_up_process(active_order.pick_up_service_time))
        env.process(courier.notify_event(notification))
        env.run(until=hour_to_sec(14))

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
        self.assertIn(courier.courier_id, dispatcher.busy_couriers.keys())

    @mock.patch('policies.courier.movement.osrm.OSRMMovementPolicy._get_route', side_effect=mocked_get_route)
    @mock.patch('settings.COURIER_MOVEMENT_PROBABILITY', 0.01)
    @mock.patch('settings.COURIER_MIN_ACCEPTANCE_RATE', 0.99)
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
            env=env,
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
            env=env,
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
                        type='pick_up',
                        visited=False
                    ),
                    Stop(
                        location=self.drop_off_at,
                        position=1,
                        orders={self.order_id: active_order},
                        type='drop_off',
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
            type='drop_off',
            visited=False
        )
        notification = Notification(
            courier=courier,
            instruction=instruction
        )
        courier.process.interrupt()
        courier.active_stop = courier.active_route.stops[0]
        courier.process = env.process(courier._picking_up_process(active_order.pick_up_service_time))
        env.process(courier.notify_event(notification))
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

    @mock.patch('settings.COURIER_MOVEMENT_PROBABILITY', 0.01)
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

    @mock.patch('settings.COURIER_EARNINGS_PER_ORDER', 3)
    @mock.patch('settings.COURIER_EARNINGS_PER_HOUR', 8)
    @mock.patch('settings.COURIER_MOVEMENT_PROBABILITY', 0.01)
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
        courier.hourly_earnings = {
            time(0, 10, 0): 2,
            time(0, 20, 0): 3,
            time(0, 30, 0): 4,
            time(0, 40, 0): 5,
            time(0, 50, 0): 6,
            time(1, 10, 0): 10,
            time(1, 30, 0): 12
        }
        courier_earnings = courier._calculate_earnings()
        self.assertEqual(courier_earnings, sum(courier.hourly_earnings.values()))

        # Test 2. Creates courier earnings to select the hourly earnings rate.
        # Asserts that these earnings are selected over the order earnings
        courier.hourly_earnings = {
            time(0, 10, 0): 1,
            time(0, 20, 0): 1,
            time(0, 30, 0): 0.5,
            time(0, 40, 0): 1,
            time(0, 50, 0): 0.4,
            time(1, 10, 0): 0.3,
            time(1, 30, 0): 3
        }
        courier_earnings = courier._calculate_earnings()
        number_of_hours = math.floor(
            (
                    datetime.combine(date.today(), off_time) - datetime.combine(date.today(), on_time)
            ).total_seconds() / 3600
        )
        self.assertEqual(
            courier_earnings,
            number_of_hours * settings.COURIER_EARNINGS_PER_HOUR
        )
