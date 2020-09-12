from dataclasses import dataclass
from datetime import time, datetime, date
from typing import Optional

from simpy import Interrupt

import settings
from actors.actor import Actor
from actors.dispatcher import Dispatcher
from objects.location import Location
from objects.order import Order
from policies.user.cancellation.random import RandomCancellationPolicy
from policies.user.cancellation.user_cancellation_policy import UserCancellationPolicy
from utils.datetime_utils import sec_to_time


@dataclass
class User(Actor):
    """A class used to handle a user's state and events"""

    dispatcher: Optional[Dispatcher] = None
    cancellation_policy: Optional[UserCancellationPolicy] = RandomCancellationPolicy()

    order: Optional[Order] = None

    def _idle_process(self):
        """Process that simulates a user being idle"""

        self.state = 'idle'
        self._log(f'New user begins idling')

        while True:
            try:
                yield self.env.timeout(delay=1)

            except Interrupt:
                break

    def _waiting_process(self):
        """Process simulating the user is waiting for the order"""

        self.state = 'waiting'
        self._log(f'User with order {self.order.order_id} begins waiting')

        while True:
            try:
                yield self.env.timeout(delay=1)

            except Interrupt:
                break

    def _evaluate_cancellation_event(self):
        """Event detailing how a user decides to cancel an order"""

        base_delay = abs((
                datetime.combine(date.today(), self.order.preparation_time) -
                datetime.combine(date.today(), sec_to_time(self.env.now))
        ).total_seconds())
        yield self.env.timeout(delay=base_delay + settings.USER_WAIT_TO_CANCEL)

        should_cancel = self.cancellation_policy.execute(courier_id=self.order.courier_id)

        if should_cancel:
            self._log(f'The user decided to cancel the order {self.order.order_id}')
            self.dispatcher.order_canceled_event(order=self.order)

        else:
            self._log(f'The user decided not to cancel the order {self.order.order_id}')

        yield self.env.process(self.dispatcher.evaluate_cancellation_event(order=self.order))

    def submit_order_event(
            self,
            order_id: int,
            pick_up_at: Location,
            drop_off_at: Location,
            placement_time: time,
            expected_drop_off_time: time,
            preparation_time: time,
            ready_time: time
    ):
        """Event detailing how a user submits an order"""

        order = Order(
            env=self.env,
            order_id=order_id,
            pick_up_at=pick_up_at,
            drop_off_at=drop_off_at,
            placement_time=placement_time,
            expected_drop_off_time=expected_drop_off_time,
            user=self
        )
        self.order = order

        self._log(f'The user submitted the order {order.order_id}')

        yield self.env.process(self.dispatcher.order_submitted_event(order, preparation_time, ready_time))

        self.process.interrupt()
        self.process = self.env.process(self._waiting_process())

        yield self.env.process(self._evaluate_cancellation_event())
