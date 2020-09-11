from dataclasses import dataclass, field
from datetime import time
from typing import Dict, Optional, Union, Any

from simpy import Environment, Process, Interrupt

import settings
from models.order import Order
from models.route import Route
from models.stop import Stop
from policies.dispatcher.myopic_matching_policy import MyopicMatchingPolicy
from policies.dispatcher.rolling_buffering_policy import RollingBufferingPolicy
from policies.dispatcher.static_cancellation_policy import StaticCancellationPolicy
from policies.policy import Policy
from utils.datetime_utils import sec_to_time


@dataclass
class Dispatcher:
    """A class used to handle a dispatcher's state and events"""

    env: Environment
    cancellation_policy: Optional[Union[Policy, StaticCancellationPolicy]] = StaticCancellationPolicy()
    dispatch_policy: Optional[Union[Policy, MyopicMatchingPolicy]] = MyopicMatchingPolicy()
    order_buffering_policy: Optional[Union[Policy, RollingBufferingPolicy]] = RollingBufferingPolicy()

    assigned_orders: Dict[int, Order] = field(default_factory=lambda: dict())
    canceled_orders: Dict[int, Order] = field(default_factory=lambda: dict())
    fulfilled_orders: Dict[int, Order] = field(default_factory=lambda: dict())
    unassigned_orders: Dict[int, Order] = field(default_factory=lambda: dict())

    idle_couriers: Dict[int, Any] = field(default_factory=lambda: dict())
    busy_couriers: Dict[int, Any] = field(default_factory=lambda: dict())
    available_couriers: Dict[int, Any] = field(default_factory=lambda: dict())

    process: Optional[Process] = None

    def __post_init__(self):
        """Immediately after the dispatcher is created, it starts simulating"""

        self.process = self.env.process(self._simulate())

    def _simulate(self):
        """Process that simulates the dispatcher's actions'"""

        while True:
            try:
                yield self.env.timeout(delay=self.order_buffering_policy.execute())
                # TODO: self._dispatch_event()

            except Interrupt:
                break

    def _dispatch_event(self):
        """Event detailing how the dispatcher executes the dispatch instructions: routing & matching"""

        orders = self.unassigned_orders.values()
        couriers = {**self.idle_couriers, **self.available_couriers}
        notifications = self.dispatch_policy.execute(orders, couriers.values())

        for notification in notifications:
            couriers[notification.courier_id].notidy_event(notification.instruction)

        # TODO: complete this event

    def evaluate_cancellation_event(self, order: Order, user):
        """Event detailing how the dispatcher decides to cancel an order"""

        yield self.env.timeout(delay=settings.DISPATCHER_WAIT_TO_CANCEL)
        should_cancel = self.cancellation_policy.execute(courier_id=order.courier_id)

        if should_cancel:
            self.order_canceled_event(order, user)

    def order_submitted_event(self, order: Order, preparation_time: time, ready_time: time):
        """Event detailing how the dispatcher handles the submission of a new order"""

        order.preparation_time = preparation_time
        order.ready_time = ready_time
        self.unassigned_orders[order.order_id] = order

    def order_canceled_event(self, order: Order, user):
        """Event detailing how the dispatcher handles a user cancelling an order"""

        if (
                order.state != 'canceled' and
                order.order_id in self.unassigned_orders.keys() and
                order.order_id not in self.canceled_orders.keys()
        ):
            del self.unassigned_orders[order.order_id]
            order.cancellation_time = sec_to_time(self.env.now)
            order.state = 'canceled'
            self.canceled_orders[order.order_id] = order
            user.process.interrupt()
            user.state = 'canceled'

    def orders_picked_up_event(self, orders: Dict[int, Order]):
        """Event detailing how the dispatcher handles a courier picking up an order"""

        for order_id, order in orders.items():
            order.pick_up_time = sec_to_time(self.env.now)
            order.state = 'picked_up'

    def orders_dropped_off_event(self, orders: Dict[int, Order]):
        """Event detailing how the dispatcher handles the fulfillment of an order"""

        for order_id, order in orders.items():
            del self.assigned_orders[order_id]
            order.drop_off_time = sec_to_time(self.env.now)
            order.state = 'dropped_off'
            self.fulfilled_orders[order_id] = order

    def notification_accepted_event(self, instruction: Union[Route, Stop], courier):
        """Event detailing how the dispatcher handles the acceptance of a notification by a courier"""

        for order_id, order in instruction.orders.items():
            del self.unassigned_orders[order_id]
            order.acceptance_time = sec_to_time(self.env.now)
            order.state = 'in_progress'
            order.courier_id = courier.courier_id
            self.assigned_orders[order_id] = order

        print(f'sim time: {sec_to_time(self.env.now)} | state: {courier.state} | Courier accepted notification')

        if courier.state == 'idle' and isinstance(instruction, Route):
            courier.active_route = instruction

        elif courier.state == 'picking_up' and isinstance(instruction, Stop):

            for order_id, order in instruction.orders.items():
                courier.active_route.orders[order_id] = order
                courier.active_stop.orders[order_id] = order

            courier.active_route.stops.append(
                Stop(
                    location=instruction.location,
                    position=len(courier.active_route.stops),
                    orders=instruction.orders,
                    type=instruction.type
                )
            )

    def notification_rejected_event(self, instruction: Union[Route, Stop], courier):
        """Event detailing how the dispatcher handles the rejection of a notification"""

        for order_id, order in instruction.orders.items():
            order.rejected_by.append(courier.courier_id)
            courier.rejected_orders.append(order_id)

        print(f'sim time: {sec_to_time(self.env.now)} | state: {courier.state} | Courier rejected notification')

    def courier_idle_event(self, courier):
        """Event detailing how the dispatcher handles setting a courier to idle"""

        if courier.courier_id in self.busy_couriers.keys():
            del self.busy_couriers[courier.courier_id]

        elif courier.courier_id in self.available_couriers.keys():
            del self.available_couriers[courier.courier_id]

        self.idle_couriers[courier.courier_id] = courier

    def courier_available_event(self, courier):
        """Event detailing how the dispatcher handles setting a courier to available"""

        if courier.state == 'picking_up' and courier.courier_id in self.idle_couriers.keys():
            del self.idle_couriers[courier.courier_id]

        self.available_couriers[courier.courier_id] = courier

    def courier_busy_event(self, courier):
        """Event detailing how the dispatcher handles setting a courier to busy"""

        if courier.courier_id in self.idle_couriers.keys():
            del self.idle_couriers[courier.courier_id]

        elif courier.courier_id in self.available_couriers.keys():
            del self.available_couriers[courier.courier_id]

        self.busy_couriers[courier.courier_id] = courier
