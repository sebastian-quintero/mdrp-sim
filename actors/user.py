from dataclasses import dataclass
from datetime import time
from typing import Optional, Union

from simpy import Environment, Process, Interrupt

import settings
from actors.dispatcher import Dispatcher
from models.location import Location
from models.order import Order
from policies.policy import Policy
from policies.user.random_cancellation_policy import RandomCancellationPolicy


@dataclass
class User:
    """A class used to handle a user's state and events"""

    dispatcher: Dispatcher
    env: Environment
    cancellation_policy: Optional[Union[Policy, RandomCancellationPolicy]] = RandomCancellationPolicy()

    order: Optional[Order] = None
    process: Optional[Process] = None
    state: str = ''

    def __post_init__(self):
        """Immediately after the user logs on, it starts idling"""

        self.process = self.env.process(self._idle_process())

    def _idle_process(self):
        """Process that simulates a user being idle"""

        self.state = 'idle'

        while True:
            try:
                yield self.env.timeout(delay=1)

            except Interrupt:
                break

    def _waiting_process(self):
        """Process simulating the user is waiting for the order"""

        self.state = 'waiting'

        while True:
            try:
                yield self.env.timeout(delay=1)

            except Interrupt:
                break

    def _evaluate_cancellation_event(self):
        """Event detailing how a user decides to cancel an order"""

        yield self.env.timeout(delay=settings.USER_WAIT_TO_CANCEL)
        should_cancel = self.cancellation_policy.execute(courier_id=self.order.courier_id)

        if should_cancel:
            self.dispatcher.order_canceled_event(order=self.order, user=self)

        yield self.env.process(self.dispatcher.evaluate_cancellation_event(order=self.order, user=self))

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
            expected_drop_off_time=expected_drop_off_time
        )
        self.order = order
        self.process.interrupt()
        self.process = self.env.process(self._waiting_process())
        self.dispatcher.order_submitted_event(order, preparation_time, ready_time)
        yield self.env.process(self._evaluate_cancellation_event())
