from dataclasses import dataclass, field
from datetime import time, datetime, date
from typing import Dict, Optional

from simpy import Interrupt

import settings
from actors.actor import Actor
from actors.courier import Courier
from objects.notification import Notification, NotificationType
from objects.order import Order
from objects.route import Route
from objects.stop import Stop
from policies.dispatcher.buffering.dispatcher_buffering_policy import DispatcherBufferingPolicy
from policies.dispatcher.buffering.rolling_horizon import RollingBufferingPolicy
from policies.dispatcher.cancellation.dispatcher_cancellation_policy import DispatcherCancellationPolicy
from policies.dispatcher.cancellation.static import StaticCancellationPolicy
from policies.dispatcher.matching.dispatcher_matching_policy import DispatcherMatchingPolicy
from policies.dispatcher.matching.greedy import GreedyMatchingPolicy
from policies.dispatcher.prepositioning.dispatcher_prepositioning_policy import DispatcherPrepositioningPolicy
from policies.dispatcher.prepositioning.naive import NaivePrepositioningPolicy
from policies.dispatcher.prepositioning_timing.dispatcher_prepositioning_timing_policy import \
    DispatcherPrepositioningTimingPolicy
from policies.dispatcher.prepositioning_timing.fixed import FixedPrepositioningTimingPolicy
from utils.datetime_utils import sec_to_time

DISPATCHER_CANCELLATION_POLICIES_MAP = {
    'static': StaticCancellationPolicy()
}
DISPATCHER_BUFFERING_POLICIES_MAP = {
    'rolling_horizon': RollingBufferingPolicy()
}
DISPATCHER_MATCHING_POLICIES_MAP = {
    'greedy': GreedyMatchingPolicy()
}
DISPATCHER_PREPOSITIONING_POLICIES_MAP = {
    'naive': NaivePrepositioningPolicy()
}
DISPATCHER_PREPOSITIONING_TIMING_POLICIES_MAP = {
    'fixed': FixedPrepositioningTimingPolicy()
}


@dataclass
class Dispatcher(Actor):
    """A class used to handle a dispatcher's state and events"""

    cancellation_policy: Optional[DispatcherCancellationPolicy] = StaticCancellationPolicy()
    buffering_policy: Optional[DispatcherBufferingPolicy] = RollingBufferingPolicy()
    matching_policy: Optional[DispatcherMatchingPolicy] = GreedyMatchingPolicy()
    prepositioning_policy: Optional[DispatcherPrepositioningPolicy] = NaivePrepositioningPolicy()
    prepositioning_timing_policy: Optional[DispatcherPrepositioningTimingPolicy] = FixedPrepositioningTimingPolicy()

    assigned_orders: Dict[int, Order] = field(default_factory=lambda: dict())
    canceled_orders: Dict[int, Order] = field(default_factory=lambda: dict())
    fulfilled_orders: Dict[int, Order] = field(default_factory=lambda: dict())
    placed_orders: Dict[int, Order] = field(default_factory=lambda: dict())
    unassigned_orders: Dict[int, Order] = field(default_factory=lambda: dict())

    available_couriers: Dict[int, Courier] = field(default_factory=lambda: dict())
    busy_couriers: Dict[int, Courier] = field(default_factory=lambda: dict())
    idle_couriers: Dict[int, Courier] = field(default_factory=lambda: dict())
    logged_off_couriers: Dict[int, Courier] = field(default_factory=lambda: dict())

    buffering_interval = buffering_policy.execute()
    prepositioning_interval = prepositioning_timing_policy.execute()

    def _idle_process(self):
        """Process that simulates the dispatcher listening for events"""

        self.state = 'listening'
        self._log('Dispatcher is listening')

        while True:
            try:
                yield self.env.timeout(delay=self.buffering_interval)
                self._dispatch_event()
                yield self.env.timeout(delay=self.prepositioning_interval)
                self._prepositioning_event()

            except Interrupt:
                break

    def _buffer_order_event(self, order: Order):
        """Event detailing how the dispatcher receives an order and based on its schedule, buffers it"""

        delay = (
                datetime.combine(date.today(), order.preparation_time) -
                datetime.combine(date.today(), order.placement_time)
        ).total_seconds()
        yield self.env.timeout(delay=delay)

        del self.placed_orders[order.order_id]
        self.unassigned_orders[order.order_id] = order

        self._log(f'Dispatcher has moved the order {order.order_id} to the unassigned buffer')

    def _dispatch_event(self):
        """Event detailing how the dispatcher executes the dispatch instructions: routing & matching"""

        orders = self.unassigned_orders.values()
        couriers = {**self.idle_couriers, **self.available_couriers}
        self._log(f'Buffering time fulfilled, will dispatch {len(orders)} orders and {len(couriers)} couriers')

        notifications = self.matching_policy.execute(orders=list(orders), couriers=list(couriers.values()))
        self._log(f'Dispatcher will send {len(notifications)} notifications')

        for notification in notifications:
            if notification.instruction is not None and notification.courier is not None:
                notification.type = NotificationType.PICK_UP_DROP_OFF
                couriers[notification.courier.courier_id].notify_event(notification)

    def _prepositioning_event(self):
        """Event detailing how the dispatcher executes the preposition instructions, sending them to couriers"""

        self._log(f'Prepositioning time fulfilled, will consider {len(self.idle_couriers)} couriers for prepositioning')

        notifications = self.prepositioning_policy.execute(
            orders=self.placed_orders.values(),
            couriers=self.idle_couriers.values()
        )
        self._log(f'Dispatcher will send {len(notifications)} prepositioning notifications')

        for notification in notifications:
            if notification.instruction is not None and notification.courier is not None:
                notification.type = NotificationType.PREPOSITIONING
                self.idle_couriers[notification.courier.courier_id].notify_event(notification)

    def evaluate_cancellation_event(self, order: Order):
        """Event detailing how the dispatcher decides to cancel an order"""

        yield self.env.timeout(delay=settings.DISPATCHER_WAIT_TO_CANCEL)
        should_cancel = self.cancellation_policy.execute(courier_id=order.courier_id)

        if should_cancel:
            self._log(f'Dispatcher decided to cancel the order {order.order_id}')
            self.order_canceled_event(order)

    def order_submitted_event(self, order: Order, preparation_time: time, ready_time: time):
        """Event detailing how the dispatcher handles the submission of a new order"""

        self._log(f'Dispatcher received the order {order.order_id} and moved it to the placed orders')

        order.preparation_time = preparation_time
        order.ready_time = ready_time
        self.placed_orders[order.order_id] = order

        yield self.env.process(self._buffer_order_event(order))

    def order_canceled_event(self, order: Order):
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
            order.user.process.interrupt()
            order.user.state = 'canceled'

        self._log(f'Dispatcher cancelled the order {order.order_id}')

    def orders_picked_up_event(self, orders: Dict[int, Order]):
        """Event detailing how the dispatcher handles a courier picking up an order"""

        self._log(f'Dispatcher will set these orders to be picked up: {list(orders.keys())}')

        for order_id, order in orders.items():
            order.pick_up_time = sec_to_time(self.env.now)
            order.state = 'picked_up'

        yield self.env.timeout(delay=1)

    def orders_dropped_off_event(self, orders: Dict[int, Order], courier: Courier):
        """Event detailing how the dispatcher handles the fulfillment of an order"""

        self._log(f'Dispatcher will set these orders to be dropped off: {list(orders.keys())}')

        for order_id, order in orders.items():
            del self.assigned_orders[order_id]
            order.drop_off_time = sec_to_time(self.env.now)
            order.state = 'dropped_off'
            order.user.state = 'dropped_off'
            self.fulfilled_orders[order_id] = order
            courier.fulfilled_orders.append(order_id)
            courier.hourly_earnings[order.drop_off_time] = settings.COURIER_EARNINGS_PER_ORDER

        yield self.env.timeout(delay=1)

    def notification_accepted_event(self, notification: Notification, courier: Courier):
        """Event detailing how the dispatcher handles the acceptance of a notification by a courier"""

        self._log(
            f'Dispatcher will handle acceptance of a {notification.type.label} notification '
            f'from courier {courier.courier_id} (state = {courier.state})'
        )

        if notification.type == NotificationType.PREPOSITIONING:
            courier.active_route = notification.instruction

        elif notification.type == NotificationType.PICK_UP_DROP_OFF:
            self._log(
                f'Dispatcher will handle acceptance of orders {list(notification.instruction.orders.keys())} '
                f'from courier {courier.courier_id} (state = {courier.state}). '
                f'Instruction is a {"Route" if isinstance(notification.instruction, Route) else "Stop"}'
            )

            for order_id, order in notification.instruction.orders.items():
                del self.unassigned_orders[order_id]

                order.acceptance_time = sec_to_time(self.env.now)
                order.state = 'in_progress'
                order.courier_id = courier.courier_id

                self.assigned_orders[order_id] = order

            if courier.state == 'idle' and isinstance(notification.instruction, Route):
                courier.active_route = notification.instruction

            elif courier.state == 'picking_up' and isinstance(notification.instruction, Stop):

                for order_id, order in notification.instruction.orders.items():
                    courier.active_route.orders[order_id] = order
                    courier.active_stop.orders[order_id] = order

                courier.active_route.stops.append(
                    Stop(
                        location=notification.instruction.location,
                        position=len(courier.active_route.stops),
                        orders=notification.instruction.orders,
                        type=notification.instruction.type
                    )
                )

        yield self.env.timeout(delay=1)

    def notification_rejected_event(self, notification: Notification, courier: Courier):
        """Event detailing how the dispatcher handles the rejection of a notification"""

        self._log(
            f'Dispatcher will handle rejection of a {notification.type.label} notification '
            f'from courier {courier.courier_id} (state = {courier.state})'
        )

        if notification.type == NotificationType.PICK_UP_DROP_OFF:
            self._log(
                f'Dispatcher will handle rejection of orders {list(notification.instruction.orders.keys())} '
                f'from courier {courier.courier_id} (state = {courier.state}). '
                f'Instruction is a {"Route" if isinstance(notification.instruction, Route) else "Stop"}'
            )

            for order_id, order in notification.instruction.orders.items():
                order.rejected_by.append(courier.courier_id)
                courier.rejected_orders.append(order_id)

        yield self.env.timeout(delay=1)

    def courier_idle_busy_event(self, courier: Courier, state: str):
        """Event detailing how the dispatcher handles setting a courier to idle or busy"""

        self._log(f'Dispatcher will set courier {courier.courier_id} to {state}')

        if courier.courier_id in self.busy_couriers.keys():
            del self.busy_couriers[courier.courier_id]

        elif courier.courier_id in self.available_couriers.keys():
            del self.available_couriers[courier.courier_id]

        elif courier.courier_id in self.idle_couriers.keys():
            del self.idle_couriers[courier.courier_id]

        if state == 'idle':
            self.idle_couriers[courier.courier_id] = courier

        elif state == 'busy':
            self.busy_couriers[courier.courier_id] = courier

        yield self.env.timeout(delay=1)

    def courier_available_event(self, courier: Courier):
        """Event detailing how the dispatcher handles setting a courier to available (can receive notifications)"""

        self._log(f'Dispatcher will set courier {courier.courier_id} to available')

        if courier.state == 'picking_up' and courier.courier_id in self.idle_couriers.keys():
            del self.idle_couriers[courier.courier_id]

        self.available_couriers[courier.courier_id] = courier

        yield self.env.timeout(delay=1)

    def courier_log_off_event(self, courier: Courier):
        """Event detailing how the dispatcher handles when a courier wants to log off"""

        self._log(f'Dispatcher will set courier {courier.courier_id} to logged off')

        courier.process.interrupt()
        courier.state = 'logged_off'

        if courier.courier_id in self.idle_couriers.keys():
            del self.idle_couriers[courier.courier_id]

        elif courier.courier_id in self.available_couriers.keys():
            del self.available_couriers[courier.courier_id]

        elif courier.courier_id in self.busy_couriers.keys():
            del self.busy_couriers[courier.courier_id]

        self.logged_off_couriers[courier.courier_id] = courier

        yield self.env.timeout(delay=1)
