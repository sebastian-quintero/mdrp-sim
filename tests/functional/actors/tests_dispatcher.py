import random
import unittest
from datetime import time, timedelta, datetime, date
from unittest.mock import patch

from simpy import Environment

import settings
from actors.courier import Courier
from actors.dispatcher import Dispatcher
from actors.user import User
from models.location import Location
from models.order import Order
from models.route import Route
from models.stop import Stop
from policies.dispatcher.static_cancellation_policy import StaticCancellationPolicy
from policies.user.random_cancellation_policy import RandomCancellationPolicy
from utils.datetime_utils import min_to_sec


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

    @patch('settings.USER_CANCELLATION_PROBABILITY', 0)
    def test_cancel_order_event(self, *args):
        """Test to verify how the dispatcher cancels an order after certain time"""

        random.seed(741)

        # Services
        env = Environment(initial_time=12 * 3600)
        dispatcher = Dispatcher(env=env, cancellation_policy=self.dispatcher_cancellation_policy)

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
        env.run(until=13 * 3600)

        # Verify order is cancelled by the dispatcher
        self.assertTrue(user.order)
        self.assertIsNone(user.order.courier_id)
        self.assertIsNotNone(user.order.cancellation_time)
        self.assertEqual(dispatcher.unassigned_orders, {})
        self.assertIn(self.order_id, dispatcher.canceled_orders.keys())
        self.assertEqual(
            user.order.cancellation_time,
            (
                    datetime.combine(date.today(), self.placement_time) +
                    timedelta(seconds=settings.DISPATCHER_WAIT_TO_CANCEL + settings.USER_WAIT_TO_CANCEL)
            ).time()
        )
        self.assertEqual(user.state, 'canceled')

    @patch('settings.USER_CANCELLATION_PROBABILITY', 0)
    def test_order_not_cancelled(self):
        """
        Test to verify that the dispatcher doesn't cancel an order if it has a courier assigned.
        The user doesn't see a courier but decides not to cancel.
        """

        random.seed(192)

        # Services
        env = Environment(initial_time=12 * 3600)
        dispatcher = Dispatcher(env=env, cancellation_policy=self.dispatcher_cancellation_policy)

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
        env.timeout(delay=settings.USER_WAIT_TO_CANCEL + min_to_sec(6))
        env.process(self.assign_courier(user, env, dispatcher))
        env.run(until=13 * 3600)

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
        initial_time = 15 * 3600
        preparation_time = time(15, 1, 0)
        ready_time = time(15, 15, 0)

        # Services
        env = Environment(initial_time=initial_time)
        dispatcher = Dispatcher(env=env)

        # Creates an order and submits it to the dispatcher
        order = Order(env=env, order_id=32)
        yield env.process(dispatcher.order_submitted_event(order, preparation_time, ready_time))
        env.run(until=initial_time + 3600)

        # Verify order properties are set and it is correctly allocated
        self.assertEqual(order.preparation_time, preparation_time)
        self.assertEqual(order.ready_time, ready_time)
        self.assertIn(order.order_id, dispatcher.unassigned_orders.keys())

    def test_orders_picked_up_event(self):
        """Test to verify the mechanics of orders being picked up"""

        # Constants
        initial_time = 14 * 3600

        # Services
        env = Environment(initial_time=initial_time)
        dispatcher = Dispatcher(env=env)

        # Creates an order and sends the picked up event
        order = Order(env=env, order_id=45)
        yield env.process(dispatcher.orders_picked_up_event(orders={order.order_id: order}))
        env.run(until=initial_time + 3600)

        # Verify order properties are modified
        self.assertEqual(order.state, 'picked_up')
        self.assertEqual(order.pick_up_time, initial_time)

    def test_orders_dropped_off_event(self):
        """Test to verify the mechanics of orders being dropped off"""

        # Constants
        initial_time = 14 * 3600

        # Services
        env = Environment(initial_time=initial_time)
        dispatcher = Dispatcher(env=env)

        # Creates an order and sends the picked up event
        order = Order(env=env, order_id=45)
        dispatcher.assigned_orders[order.order_id] = order
        yield env.process(dispatcher.orders_dropped_off_event(orders={order.order_id: order}))
        env.run(until=initial_time + 3600)

        # Verify order properties are modified and it is allocated correctly
        self.assertEqual(order.state, 'dropped_off')
        self.assertEqual(order.drop_off_time, initial_time)
        self.assertIn(order.order_id, dispatcher.fulfilled_orders.keys())
        self.assertEqual(dispatcher.assigned_orders, {})

    def test_notification_accepted_event(self):
        """Test to verify the mechanics of a notification being accepted by a courier"""

        # Constants
        initial_time = 14 * 3600

        # Services
        env = Environment(initial_time=initial_time)
        dispatcher = Dispatcher(env=env)

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
        courier = Courier(dispatcher=dispatcher, env=env, courier_id=89)
        yield env.process(dispatcher.notification_accepted_event(instruction=instruction, courier=courier))
        env.run(until=initial_time + 3600)

        # Verify order and coureir properties are modified and it is allocated correctly
        self.assertEqual(order.state, 'in_progress')
        self.assertEqual(order.acceptance_time, initial_time)
        self.assertEqual(order.courier_id, courier.courier_id)
        self.assertIn(order.order_id, dispatcher.assigned_orders.keys())
        self.assertIsNotNone(courier.active_route)
        self.assertEqual(courier.active_route, instruction)
        self.assertEqual(dispatcher.unassigned_orders, {})
