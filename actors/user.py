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
from utils.datetime_utils import sec_to_time, time_diff

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

        self.process = self.env.process(self._idle_process())
        self._log(f'Actor {self.user_id} logged on')

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
        self._schedule_cancellation_evaluation_event()

    def _cancellation_evaluation_event(self):
        """Event detailing how a user decides to cancel an order"""

        should_cancel = self.cancellation_policy.execute(courier_id=self.order.courier_id)

        if should_cancel:
            self._log(f'The user decided to cancel the order {self.order.order_id}')
            self.dispatcher.order_canceled_event(order=self.order)

        else:
            self._log(f'The user decided not to cancel the order {self.order.order_id}')

    def _schedule_cancellation_evaluation_event(self):
        """Method that allows the user to schedule the cancellation evaluation event"""

        cancellation_event = Event(env=self.env)
        cancellation_event.callbacks.append(self._cancellation_evaluation_callback)
        delay = abs(time_diff(self.order.preparation_time, sec_to_time(self.env.now))) + settings.USER_WAIT_TO_CANCEL
        self.env.schedule(event=cancellation_event, priority=NORMAL, delay=delay)

    def _cancellation_evaluation_callback(self, event: Event):
        """Callback dto activate de cancellation evaluation eventr"""

        self._cancellation_evaluation_event()

        event.succeed()
        event.callbacks = []
