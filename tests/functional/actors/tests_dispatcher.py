import random
import unittest
from datetime import time, timedelta, datetime, date
from unittest import mock

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
from policies.dispatcher.buffering.rolling_horizon import RollingBufferingPolicy
from policies.dispatcher.cancellation.static import StaticCancellationPolicy
from policies.user.cancellation.random import RandomCancellationPolicy
from tests.test_utils import mocked_get_route, DummyMatchingPolicy
from utils.datetime_utils import min_to_sec, sec_to_time, hour_to_sec


class TestsDispatcher(unittest.TestCase):
    """Tests for the Dispatcher actor class"""

    # Order properties to be reused
    order_id = 0
    pick_up_at = Location(lat=4.689697, lng=-74.055495)
    drop_off_at = Location(lat=4.690296, lng=-74.043929)
    placement_time = time(12, 0, 0)
    expected_drop_off_time = time(12, 40, 0)
    preparation_time = time(12, 1, 0)
    ready_time = time(12, 11, 0)

    # Services to be reused
    cancellation_policy = RandomCancellationPolicy()
    dispatcher_cancellation_policy = StaticCancellationPolicy()

    @staticmethod
    def assign_courier(_user: User, _env: Environment, _dispatcher: Dispatcher):
        """Dummy method to assign a courier"""

        yield _env.timeout(delay=min_to_sec(8))
        _user.order.courier_id = 999
        del _dispatcher.unassigned_orders[_user.order.order_id]
        _dispatcher.assigned_orders[_user.order.order_id] = _user.order

    @mock.patch('settings.USER_CANCELLATION_PROBABILITY', 0)
    def test_cancel_order_event(self, *args):
        """Test to verify how the dispatcher cancels an order after certain time"""

        random.seed(741)

        # Services
        env = Environment(initial_time=hour_to_sec(12))
        dispatcher = Dispatcher(
            env=env,
            cancellation_policy=self.dispatcher_cancellation_policy,
            matching_policy=DummyMatchingPolicy()
        )

        # Create a user and have it submit an order immediately, avoiding user cancellation
        user = User(cancellation_policy=self.cancellation_policy, dispatcher=dispatcher, env=env)
        env.process(
            user.submit_order_event(
                order_id=self.order_id,
                pick_up_at=self.pick_up_at,
                drop_off_at=self.drop_off_at,
                placement_time=self.placement_time,
                expected_drop_off_time=self.expected_drop_off_time,
                preparation_time=self.preparation_time,
                ready_time=self.ready_time
            )
        )
        env.run(until=hour_to_sec(13))

        # Verify order is cancelled by the dispatcher
        self.assertTrue(user.order)
        self.assertIsNone(user.order.courier_id)
        self.assertIsNotNone(user.order.cancellation_time)
        self.assertEqual(dispatcher.unassigned_orders, {})
        self.assertIn(self.order_id, dispatcher.canceled_orders.keys())
        self.assertEqual(
            user.order.cancellation_time,
            (
                    datetime.combine(date.today(), self.preparation_time) +
                    timedelta(seconds=settings.DISPATCHER_WAIT_TO_CANCEL + settings.USER_WAIT_TO_CANCEL)
            ).time()
        )
        self.assertEqual(user.state, 'canceled')

    @mock.patch('settings.USER_CANCELLATION_PROBABILITY', 0)
    def test_order_not_cancelled(self):
        """
        Test to verify that the dispatcher doesn't cancel an order if it has a courier assigned.
        The user doesn't see a courier but decides not to cancel.
        """

        random.seed(192)

        # Services
        env = Environment(initial_time=hour_to_sec(12))
        dispatcher = Dispatcher(
            env=env,
            cancellation_policy=self.dispatcher_cancellation_policy,
            matching_policy=DummyMatchingPolicy()
        )

        # Create a user, have it submit an order immediately and after some minutes, assign a courier.
        # Courier is assigned after user cancellation time has expired
        user = User(cancellation_policy=self.cancellation_policy, dispatcher=dispatcher, env=env)
        env.process(
            user.submit_order_event(
                order_id=self.order_id,
                pick_up_at=self.pick_up_at,
                drop_off_at=self.drop_off_at,
                placement_time=self.placement_time,
                expected_drop_off_time=self.expected_drop_off_time,
                preparation_time=self.preparation_time,
                ready_time=self.ready_time
            )
        )
        env.process(self.assign_courier(user, env, dispatcher))
        env.run(until=hour_to_sec(13))

        # Verify order is created but not cancelled because a courier was assigned
        self.assertTrue(user.order)
        self.assertIsNotNone(user.order.courier_id)
        self.assertIsNone(user.order.cancellation_time)
        self.assertEqual(dispatcher.assigned_orders, {self.order_id: user.order})
        self.assertEqual(dispatcher.unassigned_orders, {})
        self.assertEqual(user.state, 'waiting')

    def test_order_submitted_event(self):
        """Test to verify the mechanics of the order submitted event"""

        # Constants
        initial_time = hour_to_sec(15)
        placement_time = time(15, 0, 0)
        preparation_time = time(15, 1, 0)
        ready_time = time(15, 15, 0)

        # Services
        env = Environment(initial_time=initial_time)
        dispatcher = Dispatcher(env=env, matching_policy=DummyMatchingPolicy())

        # Creates an order and submits it to the dispatcher
        order = Order(env=env, order_id=32, placement_time=placement_time)
        env.process(dispatcher.order_submitted_event(order, preparation_time, ready_time))
        env.run(until=initial_time + 121)

        # Verify order properties are set and it is correctly allocated
        self.assertEqual(order.preparation_time, preparation_time)
        self.assertEqual(order.ready_time, ready_time)
        self.assertIn(order.order_id, dispatcher.unassigned_orders.keys())

    def test_orders_picked_up_event(self):
        """Test to verify the mechanics of orders being picked up"""

        # Constants
        initial_time = hour_to_sec(14)

        # Services
        env = Environment(initial_time=initial_time)
        dispatcher = Dispatcher(env=env, matching_policy=DummyMatchingPolicy())

        # Creates an order and sends the picked up event
        order = Order(env=env, order_id=45)
        env.process(dispatcher.orders_picked_up_event(orders={order.order_id: order}))
        env.run(until=initial_time + hour_to_sec(1))

        # Verify order properties are modified
        self.assertEqual(order.state, 'picked_up')
        self.assertEqual(order.pick_up_time, sec_to_time(initial_time))

    @mock.patch('settings.COURIER_MOVEMENT_PROBABILITY', 0.01)
    def test_orders_dropped_off_event(self):
        """Test to verify the mechanics of orders being dropped off"""

        # Constants
        initial_time = hour_to_sec(14)
        on_time = time(14, 0, 0)
        off_time = time(16, 0, 0)

        # Services
        env = Environment(initial_time=initial_time)
        dispatcher = Dispatcher(env=env, matching_policy=DummyMatchingPolicy())

        # Creates an order and sends the picked up event
        order = Order(env=env, order_id=45, user=User(env=env))
        dispatcher.assigned_orders[order.order_id] = order
        courier = Courier(on_time=on_time, off_time=off_time)
        env.process(dispatcher.orders_dropped_off_event(orders={order.order_id: order}, courier=courier))
        env.run(until=initial_time + hour_to_sec(1))

        # Verify order properties are modified and it is allocated correctly
        self.assertEqual(order.state, 'dropped_off')
        self.assertEqual(order.drop_off_time, sec_to_time(initial_time))
        self.assertIn(order.order_id, dispatcher.fulfilled_orders.keys())
        self.assertEqual(dispatcher.assigned_orders, {})
        self.assertIn(order.order_id, courier.fulfilled_orders)
        self.assertNotEqual(courier.hourly_earnings, {})

    def test_notification_accepted_event(self):
        """Test to verify the mechanics of a notification being accepted by a courier"""

        # Constants
        initial_time = hour_to_sec(14)
        on_time = time(14, 0, 0)
        off_time = time(15, 0, 0)

        # Services
        env = Environment(initial_time=initial_time)
        dispatcher = Dispatcher(env=env, matching_policy=DummyMatchingPolicy())

        # Creates an instruction with an order, a courier and sends the accepted event
        order = Order(env=env, order_id=45)
        instruction = Route(
            stops=[
                Stop(orders={order.order_id: order}, position=0),
                Stop(orders={order.order_id: order}, position=1)
            ],
            orders={order.order_id: order}
        )
        dispatcher.unassigned_orders[order.order_id] = order
        courier = Courier(dispatcher=dispatcher, env=env, courier_id=89, on_time=on_time, off_time=off_time)
        notification = Notification(
            courier=courier,
            instruction=instruction
        )
        env.process(dispatcher.notification_accepted_event(notification=notification, courier=courier))
        env.run(until=initial_time + min_to_sec(10))

        # Verify order and courier properties are modified and it is allocated correctly
        self.assertEqual(order.state, 'in_progress')
        self.assertEqual(order.acceptance_time, sec_to_time(initial_time))
        self.assertEqual(order.courier_id, courier.courier_id)
        self.assertIn(order.order_id, dispatcher.assigned_orders.keys())
        self.assertIsNotNone(courier.active_route)
        self.assertEqual(courier.active_route, instruction)
        self.assertEqual(dispatcher.unassigned_orders, {})

    @mock.patch('settings.COURIER_MOVEMENT_PROBABILITY', 0.01)
    def test_notification_rejected_event(self):
        """Test to verify the mechanics of a notification being rejected by a courier"""

        # Constants
        initial_time = hour_to_sec(14)
        on_time = time(14, 0, 0)
        off_time = time(15, 0, 0)

        # Services
        env = Environment(initial_time=initial_time)
        dispatcher = Dispatcher(env=env, matching_policy=DummyMatchingPolicy())

        # Creates an instruction with an order, a courier and sends the rejected event
        order = Order(env=env, order_id=45)
        instruction = Route(
            stops=[
                Stop(orders={order.order_id: order}, position=0),
                Stop(orders={order.order_id: order}, position=1)
            ],
            orders={order.order_id: order}
        )
        dispatcher.unassigned_orders[order.order_id] = order
        courier = Courier(dispatcher=dispatcher, env=env, courier_id=89, on_time=on_time, off_time=off_time)
        notification = Notification(
            courier=courier,
            instruction=instruction
        )
        env.process(dispatcher.notification_rejected_event(notification=notification, courier=courier))
        env.run(until=initial_time + min_to_sec(30))

        # Verify order and courier properties are modified and it is allocated correctly
        self.assertEqual(order.state, 'unassigned')
        self.assertIsNone(order.acceptance_time)
        self.assertIsNone(order.courier_id)
        self.assertIn(order.order_id, dispatcher.unassigned_orders.keys())
        self.assertIsNone(courier.active_route)
        self.assertIn(courier.courier_id, order.rejected_by)
        self.assertIn(order.order_id, courier.rejected_orders)

    @mock.patch('settings.COURIER_MOVEMENT_PROBABILITY', 0.01)
    def test_courier_idle_event(self, *args):
        """Test to verifiy the mechanics of how a courier is set to idle by the dispatcher"""

        # Constants
        initial_time = hour_to_sec(14)
        courier_id = 85
        time_delta = min_to_sec(10)
        random.seed(26)
        on_time = time(14, 0, 0)
        off_time = time(15, 0, 0)

        # Verifies 3 test cases: when the courier is busy, available or idle.
        # For each test case, assert the courier starts in a set and ends up in the idle set

        # Test 1: courier is busy
        env = Environment(initial_time=initial_time)
        dispatcher = Dispatcher(env=env, matching_policy=DummyMatchingPolicy())
        courier = Courier(dispatcher=dispatcher, env=env, courier_id=courier_id, on_time=on_time, off_time=off_time)
        dispatcher.busy_couriers = {courier.courier_id: courier}
        dispatcher.courier_idle_busy_event(courier, state='idle')
        env.run(until=initial_time + time_delta)
        self.assertIn(courier.courier_id, dispatcher.idle_couriers.keys())
        self.assertEqual(dispatcher.busy_couriers, {})
        self.assertEqual(dispatcher.available_couriers, {})

        # Test 2: courier is available
        env = Environment(initial_time=initial_time)
        dispatcher = Dispatcher(env=env, matching_policy=DummyMatchingPolicy())
        courier = Courier(dispatcher=dispatcher, env=env, courier_id=courier_id, on_time=on_time, off_time=off_time)
        dispatcher.available_couriers = {courier.courier_id: courier}
        dispatcher.courier_idle_busy_event(courier, state='idle')
        env.run(until=initial_time + time_delta)
        self.assertIn(courier.courier_id, dispatcher.idle_couriers.keys())
        self.assertEqual(dispatcher.busy_couriers, {})
        self.assertEqual(dispatcher.available_couriers, {})

        # Test 3: courier is idle
        env = Environment(initial_time=initial_time)
        dispatcher = Dispatcher(env=env, matching_policy=DummyMatchingPolicy())
        courier = Courier(dispatcher=dispatcher, env=env, courier_id=courier_id, on_time=on_time, off_time=off_time)
        dispatcher.idle_couriers = {courier.courier_id: courier}
        dispatcher.courier_idle_busy_event(courier, state='idle')
        env.run(until=initial_time + time_delta)
        self.assertIn(courier.courier_id, dispatcher.idle_couriers.keys())
        self.assertEqual(dispatcher.busy_couriers, {})
        self.assertEqual(dispatcher.available_couriers, {})

    def test_courier_available_event(self):
        """Test to verify the mechanics of how the dispatcher sets a courier to available"""

        # Constants
        initial_time = hour_to_sec(14)
        on_time = time(14, 0, 0)
        off_time = time(15, 0, 0)

        # Services
        env = Environment(initial_time=initial_time)
        dispatcher = Dispatcher(env=env, matching_policy=DummyMatchingPolicy())

        # Creates a courier and sets it to the picking process
        courier = Courier(dispatcher=dispatcher, env=env, courier_id=32, on_time=on_time, off_time=off_time)
        dispatcher.idle_couriers = {courier.courier_id: courier}
        env.process(courier._picking_up_process(service_time=600))
        env.run(until=initial_time + min_to_sec(10))

        # Verify courier properties are modified and it is allocated correctly
        self.assertEqual(courier.state, 'picking_up')
        self.assertIn(courier.courier_id, dispatcher.available_couriers.keys())
        self.assertEqual(dispatcher.idle_couriers, {})

    @mock.patch('policies.courier.movement.osrm.OSRMMovementPolicy._get_route', side_effect=mocked_get_route)
    def test_courier_busy_event(self, *args):
        """Test to verify the mechanics of how the dispatcher sets a courier to busy"""

        # Constants
        initial_time = hour_to_sec(14)
        courier_id = 14
        time_delta = min_to_sec(10)
        on_time = time(14, 0, 0)
        off_time = time(15, 0, 0)

        # Verifies 2 test cases for how the courier transitions to being busy
        # For each test case, assert the courier starts in a set and ends up in the busy set

        # Test 1: courier starts dropping off process
        env = Environment(initial_time=initial_time)
        dispatcher = Dispatcher(env=env, matching_policy=DummyMatchingPolicy())
        courier = Courier(dispatcher=dispatcher, env=env, courier_id=courier_id, on_time=on_time, off_time=off_time)
        env.process(courier._dropping_off_process(service_time=60))
        env.run(until=initial_time + time_delta)
        self.assertEqual(courier.state, 'dropping_off')
        self.assertEqual(dispatcher.busy_couriers, {courier.courier_id: courier})
        self.assertEqual(dispatcher.idle_couriers, {})

        # Test 2: courier start moving process
        env = Environment(initial_time=initial_time)
        dispatcher = Dispatcher(env=env, matching_policy=DummyMatchingPolicy())
        courier = Courier(
            dispatcher=dispatcher,
            env=env,
            courier_id=courier_id,
            location=Location(lat=4.690296, lng=-74.043929),
            on_time=on_time,
            off_time=off_time
        )
        env.process(courier._move_process(destination=Location(lat=4.689697, lng=-74.055495)))
        env.run(until=initial_time + time_delta)
        self.assertEqual(courier.state, 'moving')
        self.assertEqual(dispatcher.busy_couriers, {courier.courier_id: courier})
        self.assertEqual(dispatcher.idle_couriers, {})

    def test_buffer_event(self):
        """Test to verify how the mechanics of the dispatcher buffering orders work"""

        # Constants
        initial_time = hour_to_sec(16)
        placement_time = time(16, 0, 0)
        time_delta = min_to_sec(10)

        # Verifies two test cases for how the dispatcher buffers orders
        # For each test, assert the correct number of orders are buffered

        # Test 1: schedules the submission of three orders and assert that only two are buffered
        env = Environment(initial_time=initial_time)
        dispatcher = Dispatcher(
            env=env,
            buffering_policy=RollingBufferingPolicy(),
            matching_policy=DummyMatchingPolicy()
        )
        order_1 = Order(env=env, order_id=1, placement_time=placement_time)
        order_2 = Order(env=env, order_id=2, placement_time=placement_time)
        order_3 = Order(env=env, order_id=3, placement_time=placement_time)
        env.process(
            dispatcher.order_submitted_event(order_1, preparation_time=time(16, 0, 27), ready_time=time(16, 10, 0))
        )
        env.process(
            dispatcher.order_submitted_event(order_2, preparation_time=time(16, 0, 43), ready_time=time(16, 10, 0))
        )
        env.process(
            dispatcher.order_submitted_event(order_3, preparation_time=time(18, 0, 0), ready_time=time(18, 10, 0))
        )
        env.run(until=initial_time + time_delta)
        self.assertEqual(len(dispatcher.unassigned_orders), 2)

        # Test 2: schedules the submission of three orders and assert that all three orders are buffered
        env = Environment(initial_time=initial_time)
        dispatcher = Dispatcher(
            env=env,
            buffering_policy=RollingBufferingPolicy(),
            matching_policy=DummyMatchingPolicy()
        )
        order_1 = Order(env=env, order_id=1, placement_time=placement_time)
        order_2 = Order(env=env, order_id=2, placement_time=placement_time)
        order_3 = Order(env=env, order_id=3, placement_time=placement_time)
        env.process(
            dispatcher.order_submitted_event(order_1, preparation_time=time(16, 0, 27), ready_time=time(16, 10, 0))
        )
        env.process(
            dispatcher.order_submitted_event(order_2, preparation_time=time(16, 0, 43), ready_time=time(16, 10, 0))
        )
        env.process(
            dispatcher.order_submitted_event(order_3, preparation_time=time(16, 4, 1), ready_time=time(16, 14, 0))
        )
        env.run(until=initial_time + time_delta)
        self.assertEqual(len(dispatcher.unassigned_orders), 3)

    @mock.patch('settings.COURIER_MOVEMENT_PROBABILITY', 0.01)
    def test_courier_log_off(self):
        """Test to verify how the dispatcher handles a courier logging off"""

        # Constants
        random.seed(12)
        initial_time = hour_to_sec(12)
        time_delta = hour_to_sec(2)
        service_time = min_to_sec(4)

        # Tests 3 cases: when the courier is idle, busy or available.
        # For each test, assert that the courier ends up being logged off

        # Test 1: the courier is idle
        env = Environment(initial_time=initial_time)
        dispatcher = Dispatcher(env=env, matching_policy=DummyMatchingPolicy())
        courier = Courier(
            env=env,
            dispatcher=dispatcher,
            courier_id=69,
            on_time=time(12, 0, 0),
            off_time=time(13, 0, 0)
        )
        env.run(until=initial_time + time_delta)
        self.assertEqual(dispatcher.idle_couriers, {})
        self.assertEqual(dispatcher.busy_couriers, {})
        self.assertEqual(dispatcher.available_couriers, {})
        self.assertEqual(dispatcher.logged_off_couriers, {courier.courier_id: courier})

        # Test 2: the courier is busy
        env = Environment(initial_time=initial_time)
        dispatcher = Dispatcher(env=env, matching_policy=DummyMatchingPolicy())
        courier = Courier(
            env=env,
            dispatcher=dispatcher,
            courier_id=69,
            on_time=time(12, 0, 0),
            off_time=time(13, 0, 0)
        )
        courier.process.interrupt()
        env.process(courier._dropping_off_process(service_time=service_time))
        env.run(until=initial_time + time_delta)
        self.assertEqual(dispatcher.idle_couriers, {})
        self.assertEqual(dispatcher.busy_couriers, {})
        self.assertEqual(dispatcher.available_couriers, {})
        self.assertEqual(dispatcher.logged_off_couriers, {courier.courier_id: courier})

        # Test 3: the courier is available
        env = Environment(initial_time=initial_time)
        dispatcher = Dispatcher(env=env, matching_policy=DummyMatchingPolicy())
        courier = Courier(
            env=env,
            dispatcher=dispatcher,
            courier_id=69,
            on_time=time(12, 0, 0),
            off_time=time(13, 0, 0)
        )
        courier.process.interrupt()
        env.process(courier._picking_up_process(service_time=service_time))
        env.run(until=initial_time + time_delta)
        self.assertEqual(dispatcher.idle_couriers, {})
        self.assertEqual(dispatcher.busy_couriers, {})
        self.assertEqual(dispatcher.available_couriers, {})
        self.assertEqual(dispatcher.logged_off_couriers, {courier.courier_id: courier})

    def test_prepositioning_notification_accepted_event(self):
        """Test to verify the mechanics of a prepositioning notification being accepted by a courier"""

        # Constants
        initial_time = hour_to_sec(14)
        on_time = time(14, 0, 0)
        off_time = time(15, 0, 0)

        # Services
        env = Environment(initial_time=initial_time)
        dispatcher = Dispatcher(env=env, matching_policy=DummyMatchingPolicy())

        # Creates a prepositioning notification, a courier and sends the accepted event
        instruction = Route(
            stops=[
                Stop(position=0, type=StopType.PREPOSITION),
                Stop(position=1, type=StopType.PREPOSITION)
            ]
        )
        courier = Courier(dispatcher=dispatcher, env=env, courier_id=666, on_time=on_time, off_time=off_time)
        notification = Notification(courier=courier, instruction=instruction, type=NotificationType.PREPOSITIONING)
        env.process(dispatcher.notification_accepted_event(notification=notification, courier=courier))
        env.run(until=initial_time + min_to_sec(10))

        # Verify order and courier properties are modified and it is allocated correctly
        self.assertIsNotNone(courier.active_route)
        self.assertEqual(courier.active_route, instruction)

    @mock.patch('settings.COURIER_MOVEMENT_PROBABILITY', 0.01)
    def test_prepositioning_notification_rejected_event(self):
        """Test to verify the mechanics of a prepositioning notification being rejected by a courier"""

        # Constants
        initial_time = hour_to_sec(14)
        on_time = time(14, 0, 0)
        off_time = time(15, 0, 0)

        # Services
        env = Environment(initial_time=initial_time)
        dispatcher = Dispatcher(env=env, matching_policy=DummyMatchingPolicy())

        # Creates a prepositioning notification, a courier and sends the rejected event
        instruction = Route(
            stops=[
                Stop(position=0, type=StopType.PREPOSITION),
                Stop(position=1, type=StopType.PREPOSITION)
            ]
        )
        courier = Courier(dispatcher=dispatcher, env=env, courier_id=981, on_time=on_time, off_time=off_time)
        notification = Notification(courier=courier, instruction=instruction, type=NotificationType.PREPOSITIONING)
        env.process(dispatcher.notification_rejected_event(notification=notification, courier=courier))
        env.run(until=initial_time + min_to_sec(30))

        # Verify order and courier properties are modified and it is allocated correctly
        self.assertIsNone(courier.active_route)
