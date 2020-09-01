import random
import unittest
from datetime import time
from unittest.mock import patch

from simpy import Environment

from actors.courier import Courier
from actors.dispatcher import Dispatcher
from models.location import Location
from models.order import Order
from models.route import Route
from models.stop import Stop
from models.vehicle import Vehicle
from policies.courier.neighbors_move_eval_policy import NeighborsMoveEvalPolicy
from policies.courier.osrm_movement_policy import OSRMMovementPolicy
from policies.courier.uniform_acceptance_policy import UniformAcceptancePolicy


def mocked_get_route(origin: Location, destination: Location) -> Route:
    return Route(stops=[Stop(location=origin, position=0), Stop(location=destination, position=1)])


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
    def test_always_idle(self, *args):
        """Test to evaluate a courier never moving"""

        env = Environment()
        dispatcher = Dispatcher(env=env)

        # Creates a courier and runs a simulation
        courier = Courier(
            acceptance_policy=self.acceptance_policy,
            dispatcher=dispatcher,
            env=env,
            movement_evaluation_policy=self.movement_evaluation_policy,
            movement_policy=self.movement_policy,
            courier_id=self.courier_id,
            vehicle=self.vehicle,
            location=self.start_location
        )
        env.run(until=4 * 3600)

        # Asserts that the courier is idle and never moved
        self.assertEqual(courier.state, 'idle')
        self.assertEqual(courier.location, self.start_location)
        self.assertIn(courier.courier_id, dispatcher.idle_couriers.keys())

    @patch('policies.courier.osrm_movement_policy.OSRMMovementPolicy._get_route', side_effect=mocked_get_route)
    @patch('settings.COURIER_MOVEMENT_PROBABILITY', 0.95)
    def test_movement_process(self, *args):
        """Test to evaluate how a courier moves with dummy movement"""

        random.seed(365)

        env = Environment()
        dispatcher = Dispatcher(env=env)

        # Creates a courier and runs a simulation
        courier = Courier(
            acceptance_policy=self.acceptance_policy,
            dispatcher=dispatcher,
            env=env,
            movement_evaluation_policy=self.movement_evaluation_policy,
            movement_policy=self.movement_policy,
            courier_id=self.courier_id,
            vehicle=self.vehicle,
            location=self.start_location
        )
        env.run(until=4 * 3600)

        # Asserts that the courier moved and is is in a different location
        self.assertEqual(courier.state, 'moving')
        self.assertNotEqual(courier.location, self.start_location)
        self.assertIn(courier.courier_id, dispatcher.busy_couriers.keys())

    @patch('policies.courier.osrm_movement_policy.OSRMMovementPolicy._get_route', side_effect=mocked_get_route)
    @patch('settings.COURIER_MOVEMENT_PROBABILITY', 0.1)
    @patch('settings.COURIER_MIN_ACCEPTANCE_RATE', 0.99)
    def test_notify_event_accept_idle(self, *args):
        """Test to evaluate how a courier handles a notification while being idle and accepts it"""

        random.seed(126)

        env = Environment(initial_time=12 * 3600)
        dispatcher = Dispatcher(env=env)

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
            acceptance_rate=0.99
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
        env.process(courier.notify_event(instruction))
        env.run(until=14 * 3600)

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

    @patch('policies.courier.osrm_movement_policy.OSRMMovementPolicy._get_route', side_effect=mocked_get_route)
    @patch('settings.COURIER_MOVEMENT_PROBABILITY', 0.1)
    @patch('settings.COURIER_MIN_ACCEPTANCE_RATE', 0.99)
    def test_notify_event_reject_idle(self, *args):
        """Test to evaluate how a courier handles a notification while being idle and rejects it"""

        random.seed(122)

        env = Environment(initial_time=12 * 3600)
        dispatcher = Dispatcher(env=env)

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
            acceptance_rate=0.01
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
        env.process(courier.notify_event(instruction))
        env.run(until=14 * 3600)

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

    @patch('policies.courier.osrm_movement_policy.OSRMMovementPolicy._get_route', side_effect=mocked_get_route)
    @patch('settings.COURIER_MOVEMENT_PROBABILITY', 0.1)
    @patch('settings.COURIER_MIN_ACCEPTANCE_RATE', 0.99)
    def test_notify_event_accept_picking_up(self, *args):
        """Test to evaluate how a courier handles a notification while picking up and accepts it"""

        random.seed(183)

        env = Environment(initial_time=12 * 3600 + 12 * 60)
        dispatcher = Dispatcher(env=env)

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
            courier_id=self.courier_id
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
            ready_time=self.ready_time
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
            )
        )

        instruction = Stop(
            location=new_order.drop_off_at,
            position=1,
            orders={new_order.order_id: new_order},
            type='drop_off',
            visited=False
        )
        courier.process.interrupt()
        courier.active_stop = courier.active_route.stops[0]
        courier.process = env.process(courier._picking_up_process(active_order.pick_up_service_time))
        env.process(courier.notify_event(instruction))
        env.run(until=14 * 3600)

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
        self.assertEqual(courier.state, 'idle')
        self.assertIn(courier.courier_id, dispatcher.idle_couriers.keys())

    @patch('policies.courier.osrm_movement_policy.OSRMMovementPolicy._get_route', side_effect=mocked_get_route)
    @patch('settings.COURIER_MOVEMENT_PROBABILITY', 0.01)
    @patch('settings.COURIER_MIN_ACCEPTANCE_RATE', 0.99)
    def test_notify_event_reject_picking_up(self, *args):
        """Test to evaluate how a courier handles a notification while picking up and rejects it"""

        random.seed(4747474)

        env = Environment(initial_time=12 * 3600 + 12 * 60)
        dispatcher = Dispatcher(env=env)

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
            courier_id=self.courier_id
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
            ready_time=self.ready_time
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
            )
        )

        instruction = Stop(
            location=new_order.drop_off_at,
            position=1,
            orders={new_order.order_id: new_order},
            type='drop_off',
            visited=False
        )
        courier.process.interrupt()
        courier.active_stop = courier.active_route.stops[0]
        courier.process = env.process(courier._picking_up_process(active_order.pick_up_service_time))
        env.process(courier.notify_event(instruction))
        env.run(until=14 * 3600)

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
