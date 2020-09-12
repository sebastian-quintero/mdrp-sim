import random
import unittest
from datetime import time, timedelta, datetime, date
from unittest.mock import patch

from simpy import Environment

import settings
from actors.dispatcher import Dispatcher
from actors.user import User
from objects.location import Location
from policies.user.cancellation.random import RandomCancellationPolicy
from tests.functional.actors.tests_dispatcher import TestsDispatcher, DummyMatchingPolicy
from utils.datetime_utils import min_to_sec


class TestsUser(unittest.TestCase):
    """Tests for the User actor class"""

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

    @patch('settings.USER_WAIT_TO_CANCEL', min_to_sec(5))
    def test_submit_cancel_order(self, *args):
        """Test to verify how a user submits and decides to cancel an order"""

        # Constants
        random.seed(666)
        initial_time = 12 * 3600
        time_delta = min_to_sec(10)

        # Services
        env = Environment(initial_time=initial_time)
        dispatcher = Dispatcher(env=env, matching_policy=DummyMatchingPolicy())

        # Create a user and have it submit an order immediately
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
        env.run(until=initial_time + time_delta)

        # Verify order is created and cancelled due to a courier not being assigned
        self.assertTrue(user.order)
        self.assertIsNone(user.order.courier_id)
        self.assertIsNotNone(user.order.cancellation_time)
        self.assertEqual(dispatcher.unassigned_orders, {})
        self.assertIn(self.order_id, dispatcher.canceled_orders.keys())
        self.assertEqual(
            user.order.cancellation_time,
            (
                    datetime.combine(date.today(), self.preparation_time) +
                    timedelta(seconds=settings.USER_WAIT_TO_CANCEL)
            ).time()
        )
        self.assertEqual(user.state, 'canceled')

    def test_submit_courier_assigned(self):
        """Test to verify how a user submits and order and doesn't cancel since a courier is assigned"""

        random.seed(666)

        # Services
        env = Environment(initial_time=12 * 3600)
        dispatcher = Dispatcher(env=env, matching_policy=DummyMatchingPolicy())

        # Create a user, have it submit an order immediately and after some minutes, assign a courier
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
        env.process(TestsDispatcher.assign_courier(user, env, dispatcher))
        env.run(until=13 * 3600)

        # Verify order is created but not cancelled because a courier was assigned
        self.assertTrue(user.order)
        self.assertIsNotNone(user.order.courier_id)
        self.assertIsNone(user.order.cancellation_time)
        self.assertEqual(dispatcher.assigned_orders, {self.order_id: user.order})
        self.assertEqual(dispatcher.unassigned_orders, {})
        self.assertEqual(user.state, 'waiting')

    @patch('settings.USER_CANCELLATION_PROBABILITY', 0)
    @patch('settings.DISPATCHER_WAIT_TO_CANCEL', min_to_sec(120))
    def test_submit_wait_for_order(self, *args):
        """Test to verify how a user submits an order but doesn't cancel even without courier, deciding to wait"""

        random.seed(157)

        # Services
        env = Environment(initial_time=12 * 3600)
        dispatcher = Dispatcher(env=env, matching_policy=DummyMatchingPolicy())

        # Create a user and have it submit an order immediately
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

        # Verify order is created but not cancelled, disregarding the lack of a courier
        self.assertTrue(user.order)
        self.assertIsNone(user.order.courier_id)
        self.assertIsNone(user.order.cancellation_time)
        self.assertEqual(dispatcher.unassigned_orders, {self.order_id: user.order})
        self.assertEqual(user.state, 'waiting')
