from dataclasses import dataclass, field
from datetime import time
from typing import Dict, Optional, List, Tuple

from simpy import Interrupt, Event
from simpy.events import NORMAL

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
from policies.dispatcher.matching.myopic import MyopicMatchingPolicy
from policies.dispatcher.prepositioning.dispatcher_prepositioning_policy import DispatcherPrepositioningPolicy
from policies.dispatcher.prepositioning.naive import NaivePrepositioningPolicy
from policies.dispatcher.prepositioning_evaluation.dispatcher_prepositioning_evaluation_policy import \
    DispatcherPrepositioningEvaluationPolicy
from policies.dispatcher.prepositioning_evaluation.fixed import FixedPrepositioningEvaluationPolicy
from utils.datetime_utils import sec_to_time, time_diff, time_add

DISPATCHER_CANCELLATION_POLICIES_MAP = {
    'static': StaticCancellationPolicy()
}
DISPATCHER_BUFFERING_POLICIES_MAP = {
    'rolling_horizon': RollingBufferingPolicy()
}
DISPATCHER_MATCHING_POLICIES_MAP = {
    'greedy': GreedyMatchingPolicy(),
    'myopic': MyopicMatchingPolicy()
}
DISPATCHER_PREPOSITIONING_POLICIES_MAP = {
    'naive': NaivePrepositioningPolicy()
}
DISPATCHER_PREPOSITIONING_EVALUATION_POLICIES_MAP = {
    'fixed': FixedPrepositioningEvaluationPolicy()
}


@dataclass
class Dispatcher(Actor):
    """A class used to handle a dispatcher's state and events"""

    cancellation_policy: Optional[DispatcherCancellationPolicy] = StaticCancellationPolicy()
    buffering_policy: Optional[DispatcherBufferingPolicy] = RollingBufferingPolicy()
    matching_policy: Optional[DispatcherMatchingPolicy] = GreedyMatchingPolicy()
    prepositioning_policy: Optional[DispatcherPrepositioningPolicy] = NaivePrepositioningPolicy()
    prepositioning_evaluation_policy: Optional[
        DispatcherPrepositioningEvaluationPolicy
    ] = FixedPrepositioningEvaluationPolicy()

    assigned_orders: Dict[int, Order] = field(default_factory=lambda: dict())
    canceled_orders: Dict[int, Order] = field(default_factory=lambda: dict())
    fulfilled_orders: Dict[int, Order] = field(default_factory=lambda: dict())
    placed_orders: Dict[int, Tuple[time, Order]] = field(default_factory=lambda: dict())
    scheduled_cancellation_evaluation_orders: Dict[int, Tuple[time, Order]] = field(default_factory=lambda: dict())
    unassigned_orders: Dict[int, Order] = field(default_factory=lambda: dict())

    dropping_off_couriers: Dict[int, Courier] = field(default_factory=lambda: dict())
    idle_couriers: Dict[int, Courier] = field(default_factory=lambda: dict())
    logged_off_couriers: Dict[int, Courier] = field(default_factory=lambda: dict())
    moving_couriers: Dict[int, Courier] = field(default_factory=lambda: dict())
    picking_up_couriers: Dict[int, Courier] = field(default_factory=lambda: dict())

    notifications: List[Notification] = field(default_factory=lambda: list())

    def _idle_process(self):
        """Process that simulates the dispatcher listening for events"""

        self.state = 'listening'

        self._log('Dispatcher is listening')

        while True:
            try:
                self._evaluate_buffering_event()
                self._evaluate_prepositioning_event()
                yield self.env.timeout(delay=1)

            except Interrupt:
                break

    def order_submitted_event(self, order: Order, preparation_time: time, ready_time: time):
        """Event detailing how the dispatcher handles the submission of a new order"""

        self._log(f'Dispatcher received the order {order.order_id} and moved it to the placed orders')

        order.preparation_time = preparation_time
        order.ready_time = ready_time
        self.placed_orders[order.order_id] = (preparation_time, order)
        self.scheduled_cancellation_evaluation_orders[order.order_id] = (
            time_add(preparation_time, settings.DISPATCHER_WAIT_TO_CANCEL),
            order
        )
        self._schedule_buffer_order_event(order)

    def _buffer_order_event(self):
        """Event detailing how the dispatcher buffers an order"""

        orders_for_buffering = [
            order
            for order_id, (scheduled_time, order) in self.placed_orders.items()
            if sec_to_time(self.env.now) >= scheduled_time
        ]

        for order in orders_for_buffering:
            del self.placed_orders[order.order_id]
            self.unassigned_orders[order.order_id] = order

            self._log(f'Dispatcher has moved the order {order.order_id} to the unassigned buffer')

    def _evaluate_cancellation_event(self):
        """Event detailing how the dispatcher evaluates if it should cancel an order"""

        orders_for_evaluation = [
            order
            for order_id, (scheduled_time, order) in self.scheduled_cancellation_evaluation_orders.items()
            if sec_to_time(self.env.now) >= scheduled_time
        ]

        for order in orders_for_evaluation:
            should_cancel = self.cancellation_policy.execute(courier_id=order.courier_id)

            if should_cancel:
                self._log(f'Dispatcher decided to cancel the order {order.order_id}')
                self.cancel_order_event(order)

            else:
                self._log(f'Dispatcher decided not to cancel the order {order.order_id}')

    def cancel_order_event(self, order: Order):
        """Event detailing how the dispatcher handles a user canceling an order"""

        if (
                order.state != 'canceled' and
                (
                        order.order_id in self.placed_orders.keys() or
                        order.order_id in self.unassigned_orders.keys()

                ) and
                order.order_id not in self.canceled_orders.keys() and
                order.order_id not in self.assigned_orders.keys() and
                order.order_id not in self.fulfilled_orders.keys()
        ):
            if order.order_id in self.placed_orders.keys():
                del self.placed_orders[order.order_id]

            if order.order_id in self.unassigned_orders.keys():
                del self.unassigned_orders[order.order_id]

            order.cancellation_time = sec_to_time(self.env.now)
            order.state = 'canceled'
            order.user.state = 'canceled'
            self.canceled_orders[order.order_id] = order

        self._log(f'Dispatcher canceled the order {order.order_id}')

    def _evaluate_buffering_event(self):
        """Event detailing how the dispatcher evaluates if it should flush the buffer and begin dispatching"""

        if self.buffering_policy.execute(env_time=self.env.now):
            self._log('Buffering time fulfilled, begin dispatch event.')

            self._dispatch_event()

    def _dispatch_event(self):
        """Event detailing how the dispatcher executes the dispatch instructions: routing & matching"""

        orders = self.unassigned_orders.values()
        couriers = {
            courier.courier_id: courier
            for courier in {**self.idle_couriers, **self.picking_up_couriers}.values()
            if (
                len(courier.active_route.orders) < settings.DISPATCHER_PROSPECTS_MAX_ORDERS
                if courier.active_route is not None
                else True
            )
        }
        self._log(f'Attempting dispatch of {len(orders)} orders and {len(couriers)} couriers.')

        if bool(orders) and bool(couriers):
            notifications = self.matching_policy.execute(
                orders=list(orders),
                couriers=list(couriers.values()),
                env_time=self.env.now
            )
            notifications_log = [
                ([order_id for order_id in notification.instruction.orders.keys()], notification.courier.courier_id)
                for notification in notifications
            ]
            self._log(
                f'Dispatcher will send {len(notifications)} notifications ([order_id\'s], courier_id): '
                f'{notifications_log}'
            )

            for notification in notifications:
                if notification.instruction is not None and notification.courier is not None:
                    self.notifications.append(notification)
                    self.env.process(couriers[notification.courier.courier_id].notification_event(notification))

    def _prepositioning_event(self):
        """Event detailing how the dispatcher executes the preposition instructions, sending them to couriers"""

        self._log(f'Prepositioning time fulfilled, attempting prepositioning of {len(self.idle_couriers)} couriers')

        notifications = self.prepositioning_policy.execute(
            orders=[order for _, order in self.placed_orders.values()],
            couriers=self.idle_couriers.values()
        )
        if bool(notifications):
            self._log(f'Dispatcher will send {len(notifications)} prepositioning notifications')

            for notification in notifications:
                if notification.instruction is not None and notification.courier is not None:
                    notification.type = NotificationType.PREPOSITIONING
                    self.notifications.append(notification)
                    self.env.process(
                        self.idle_couriers[notification.courier.courier_id].notification_event(notification))

    def _evaluate_prepositioning_event(self):
        """Event detailing how the dispatcher evaluates if it should flush the buffer and begin dispatching"""

        if self.prepositioning_evaluation_policy.execute(env_time=self.env.now):
            self._prepositioning_event()
            self._log('Prepositioning time fulfilled, begin prepositioning event.')

            self._prepositioning_event()

    def notification_accepted_event(self, notification: Notification, courier: Courier):
        """Event detailing how the dispatcher handles the acceptance of a notification by a courier"""

        self._log(
            f'Dispatcher will handle acceptance of a {notification.type.label} notification '
            f'from courier {courier.courier_id} (state = {courier.state})'
        )

        if notification.type == NotificationType.PREPOSITIONING:
            courier.active_route = notification.instruction

        elif notification.type == NotificationType.PICK_UP_DROP_OFF:
            order_ids = (
                list(notification.instruction.orders.keys())
                if isinstance(notification.instruction, Route)
                else [order_id for stop in notification.instruction for order_id in stop.orders.keys()]
            )
            processed_order_ids = [
                order_id
                for order_id in order_ids
                if (
                        order_id in self.canceled_orders.keys() or
                        order_id in self.assigned_orders.keys() or
                        order_id in self.fulfilled_orders.keys()
                )
            ]

            if bool(processed_order_ids):
                self._log(
                    f'Dispatcher will update the notification to courier {courier.courier_id} '
                    f'based on these orders being already processed: {processed_order_ids}'
                )
                notification.update(processed_order_ids)

            if (
                    (
                            isinstance(notification.instruction, Route) and
                            bool(notification.instruction.orders) and
                            bool(notification.instruction.stops)
                    ) or
                    (
                            isinstance(notification.instruction, list) and
                            bool(notification.instruction) and
                            bool(notification.instruction[0].orders)
                    )
            ):
                order_ids = (
                    list(notification.instruction.orders.keys())
                    if isinstance(notification.instruction, Route)
                    else [order_id for stop in notification.instruction for order_id in stop.orders.keys()]
                )
                self._log(
                    f'Dispatcher will handle acceptance of orders {order_ids} '
                    f'from courier {courier.courier_id} (state = {courier.state}). '
                    f'Instruction is a {"Route" if isinstance(notification.instruction, Route) else "List[Stop]"}'
                )

                instruction_orders = (
                    notification.instruction.orders.items()
                    if isinstance(notification.instruction, Route)
                    else [
                        (order_id, order)
                        for stop in notification.instruction for order_id, order in stop.orders.items()
                    ]
                )
                for order_id, order in instruction_orders:
                    del self.unassigned_orders[order_id]
                    order.acceptance_time = sec_to_time(self.env.now)
                    order.state = 'in_progress'
                    order.courier_id = courier.courier_id
                    self.assigned_orders[order_id] = order

                if courier.state == 'idle' and isinstance(notification.instruction, Route):
                    courier.active_route = notification.instruction

                elif courier.state == 'picking_up' and isinstance(notification.instruction, list):
                    for stop in notification.instruction:
                        for order_id, order in stop.orders.items():
                            courier.active_route.orders[order_id] = order
                            courier.active_stop.orders[order_id] = order

                        courier.active_route.stops.append(
                            Stop(
                                location=stop.location,
                                position=len(courier.active_route.stops),
                                orders=stop.orders,
                                type=stop.type
                            )
                        )

                courier.accepted_notifications.append(notification)

            else:
                self._log(
                    f'Dispatcher will nullify notification to courier {courier.courier_id}. All orders canceled.'
                )

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

    def orders_in_store_event(self, orders: Dict[int, Order]):
        """Event detailing how the dispatcher handles a courier arriving to the store"""

        self._log(f'Dispatcher will set these orders to be in store: {list(orders.keys())}')

        for order_id, order in orders.items():
            order.in_store_time = sec_to_time(self.env.now)
            order.state = 'in_store'

    def orders_picked_up_event(self, orders: Dict[int, Order]):
        """Event detailing how the dispatcher handles a courier picking up an order"""

        self._log(f'Dispatcher will set these orders to be picked up: {list(orders.keys())}')

        for order_id, order in orders.items():
            order.pick_up_time = sec_to_time(self.env.now)
            order.state = 'picked_up'

    def orders_dropped_off_event(self, orders: Dict[int, Order], courier: Courier):
        """Event detailing how the dispatcher handles the fulfillment of an order"""

        self._log(
            f'Dispatcher will set these orders to be dropped off: {list(orders.keys())}; '
            f'by courier {courier.courier_id}'
        )

        for order_id, order in orders.items():
            if order_id not in self.fulfilled_orders.keys() and order_id in self.assigned_orders.keys():
                del self.assigned_orders[order_id]
                order.drop_off_time = sec_to_time(self.env.now)
                order.state = 'dropped_off'
                self.fulfilled_orders[order_id] = order
                courier.fulfilled_orders.append(order_id)
                order.user.order_dropped_off_event(order_id)

    def courier_idle_event(self, courier: Courier):
        """Event detailing how the dispatcher handles setting a courier to idle"""

        self._log(f'Dispatcher will set courier {courier.courier_id} to idle')

        if courier.courier_id in self.dropping_off_couriers.keys():
            del self.dropping_off_couriers[courier.courier_id]

        elif courier.courier_id in self.moving_couriers.keys():
            del self.moving_couriers[courier.courier_id]

        elif courier.courier_id in self.picking_up_couriers.keys():
            del self.picking_up_couriers[courier.courier_id]

        self.idle_couriers[courier.courier_id] = courier

    def courier_moving_event(self, courier: Courier):
        """Event detailing how the dispatcher handles setting a courier to dropping off"""

        self._log(f'Dispatcher will set courier {courier.courier_id} to moving')

        if courier.courier_id in self.idle_couriers.keys():
            del self.idle_couriers[courier.courier_id]

        elif courier.courier_id in self.dropping_off_couriers.keys():
            del self.dropping_off_couriers[courier.courier_id]

        elif courier.courier_id in self.picking_up_couriers.keys():
            del self.picking_up_couriers[courier.courier_id]

        self.moving_couriers[courier.courier_id] = courier

    def courier_picking_up_event(self, courier: Courier):
        """Event detailing how the dispatcher handles setting a courier to picking up"""

        self._log(f'Dispatcher will set courier {courier.courier_id} to picking up')

        if courier.courier_id in self.idle_couriers.keys():
            del self.idle_couriers[courier.courier_id]

        elif courier.courier_id in self.dropping_off_couriers.keys():
            del self.dropping_off_couriers[courier.courier_id]

        elif courier.courier_id in self.moving_couriers.keys():
            del self.moving_couriers[courier.courier_id]

        self.picking_up_couriers[courier.courier_id] = courier

    def courier_dropping_off_event(self, courier: Courier):
        """Event detailing how the dispatcher handles setting a courier to dropping off"""

        self._log(f'Dispatcher will set courier {courier.courier_id} to dropping off')

        if courier.courier_id in self.idle_couriers.keys():
            del self.idle_couriers[courier.courier_id]

        elif courier.courier_id in self.moving_couriers.keys():
            del self.moving_couriers[courier.courier_id]

        elif courier.courier_id in self.picking_up_couriers.keys():
            del self.picking_up_couriers[courier.courier_id]

        self.dropping_off_couriers[courier.courier_id] = courier

    def courier_log_off_event(self, courier: Courier):
        """Event detailing how the dispatcher handles when a courier wants to log off"""

        self._log(f'Dispatcher will set courier {courier.courier_id} to logged off')

        if courier.courier_id in self.idle_couriers.keys():
            del self.idle_couriers[courier.courier_id]

        elif courier.courier_id in self.dropping_off_couriers.keys():
            del self.dropping_off_couriers[courier.courier_id]

        elif courier.courier_id in self.moving_couriers.keys():
            del self.moving_couriers[courier.courier_id]

        elif courier.courier_id in self.picking_up_couriers.keys():
            del self.picking_up_couriers[courier.courier_id]

        self.logged_off_couriers[courier.courier_id] = courier

    def _schedule_evaluate_cancellation_event(self):
        """Method that allows the dispatcher to schedule the cancellation evaluation event"""

        evaluate_cancellation_event = Event(env=self.env)
        evaluate_cancellation_event.callbacks.append(self._evaluate_cancellation_callback)
        self.env.schedule(event=evaluate_cancellation_event, priority=NORMAL, delay=settings.DISPATCHER_WAIT_TO_CANCEL)

    def _schedule_buffer_order_event(self, order: Order):
        """Method that allows the dispatcher to schedule the order buffering event"""

        buffering_event = Event(env=self.env)
        buffering_event.callbacks.append(self._buffer_order_callback)
        self.env.schedule(
            event=buffering_event,
            priority=NORMAL,
            delay=time_diff(order.preparation_time, order.placement_time)
        )

    def _evaluate_cancellation_callback(self, event: Event):
        """Callback detailing how the dispatcher evaluates canceling an order"""

        self._evaluate_cancellation_event()

        event.succeed()
        event.callbacks = []

    def _buffer_order_callback(self, event: Event):
        """Callback detailing how the dispatcher buffers an order once it's placed"""

        self._buffer_order_event()
        self._schedule_evaluate_cancellation_event()

        event.succeed()
        event.callbacks = []
