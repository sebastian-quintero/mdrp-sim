from dataclasses import dataclass
from datetime import time
from typing import Optional

from simpy import Interrupt, Event
from simpy.events import NORMAL

import settings
from actors.actor import Actor
from actors.dispatcher import Dispatcher
from objects.location import Location
from objects.order import Order
from policies.user.cancellation.random import RandomCancellationPolicy
from policies.user.cancellation.user_cancellation_policy import UserCancellationPolicy

USER_CANCELLATION_POLICIES_MAP = {
    'random': RandomCancellationPolicy()
}


@dataclass
class User(Actor):
    """A class used to handle a user's state and events"""

    dispatcher: Optional[Dispatcher] = None
    cancellation_policy: Optional[UserCancellationPolicy] = RandomCancellationPolicy()

    order: Optional[Order] = None
    user_id: Optional[int] = None

    def __post_init__(self):
        """Immediately after the actor is created, it starts idling"""

        self._log(f'Actor {self.user_id} logged on')

        self.process = self.env.process(self._idle_process())

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
            order_id=order_id,
            pick_up_at=pick_up_at,
            drop_off_at=drop_off_at,
            placement_time=placement_time,
            expected_drop_off_time=expected_drop_off_time,
            user=self
        )
        self.order = order

        self._log(f'The user submitted the order {order.order_id}')

        self.process.interrupt()
        self.process = self.env.process(self._waiting_process())
        self.dispatcher.order_submitted_event(order, preparation_time, ready_time)
        self._schedule_evaluate_cancellation_event()

    def _evaluate_cancellation_event(self):
        """Event detailing how a user decides to cancel an order"""

        should_cancel = self.cancellation_policy.execute(courier_id=self.order.courier_id)

        if should_cancel:
            self._cancel_order_event()

        else:
            self._log(f'The user decided not to cancel the order {self.order.order_id}')

    def _cancel_order_event(self):
        """Event detailing how the user cancels the order"""

        self._log(f'The user decided to cancel the order {self.order.order_id}')

        self.dispatcher.cancel_order_event(order=self.order)
        self.process.interrupt()

    def order_dropped_off_event(self, order_id: int):
        """Event detailing how the user gets the order delivered"""

        self._log(f'The user has the order {order_id} dropped off.')

        self.process.interrupt()
        self.state = 'dropped_off'

    def _schedule_evaluate_cancellation_event(self):
        """Method that allows the user to schedule the cancellation evaluation event"""

        cancellation_event = Event(env=self.env)
        cancellation_event.callbacks.append(self._evaluate_cancellation_callback)
        self.env.schedule(event=cancellation_event, priority=NORMAL, delay=settings.USER_WAIT_TO_CANCEL)

    def _evaluate_cancellation_callback(self, event: Event):
        """Callback dto activate de cancellation evaluation eventr"""

        self._evaluate_cancellation_event()
        event.succeed()
        event.callbacks = []
