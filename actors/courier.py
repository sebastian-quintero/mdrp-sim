import random
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, date
from typing import List, Optional, Any, Dict

from simpy import Interrupt, Event
from simpy.events import NORMAL

import settings
from actors.actor import Actor
from objects.location import Location
from objects.notification import Notification, NotificationType
from objects.route import Route
from objects.stop import Stop, StopType
from objects.vehicle import Vehicle
from policies.courier.acceptance.courier_acceptance_policy import CourierAcceptancePolicy
from policies.courier.acceptance.random_uniform import UniformAcceptancePolicy
from policies.courier.movement.courier_movement_policy import CourierMovementPolicy
from policies.courier.movement.osrm import OSRMMovementPolicy
from policies.courier.movement_evaluation.courier_movement_evaluation_policy import CourierMovementEvaluationPolicy
from policies.courier.movement_evaluation.geohash_neighbors import NeighborsMoveEvalPolicy


@dataclass
class Courier(Actor):
    """A class used to handle a courier's state and events"""

    dispatcher: Optional[Any] = None
    acceptance_policy: Optional[CourierAcceptancePolicy] = UniformAcceptancePolicy()
    movement_evaluation_policy: Optional[CourierMovementEvaluationPolicy] = NeighborsMoveEvalPolicy()
    movement_policy: Optional[CourierMovementPolicy] = OSRMMovementPolicy()

    acceptance_rate: float = random.uniform(settings.COURIER_MIN_ACCEPTANCE_RATE, 1)
    active_route: Optional[Route] = None
    active_stop: Optional[Stop] = None
    courier_id: Optional[int] = None
    earnings: Optional[float] = None
    fulfilled_orders: List[int] = field(default_factory=lambda: list())
    hourly_earnings: Dict[Any, float] = field(default_factory=lambda: dict())
    location: Optional[Location] = None
    log_off_event: Optional[Event] = None
    on_time: time = None
    off_time: time = None
    rejected_orders: List[int] = field(default_factory=lambda: list())
    vehicle: Optional[Vehicle] = Vehicle.MOTORCYCLE

    def __post_init__(self):
        """Immediately after the courier logs on, the log off is scheduled and it starts idling"""

        self._log('Actor logged on')
        self._schedule_log_off()
        self.process = self.env.process(self._idle_process())

    def _idle_process(self):
        """Process that simulates a courier being idle / waiting"""

        self.state = 'idle'
        self._log(f'Courier {self.courier_id} begins idling')

        try:
            yield self.env.process(self.dispatcher.courier_idle_busy_event(courier=self, state=self.state))

        except Interrupt:
            pass

        while True:
            try:
                yield self.env.timeout(delay=settings.COURIER_WAIT_TO_MOVE)
                yield self.env.process(self._evaluate_movement_event())

            except Interrupt:
                break

    def _picking_up_process(self, service_time: float):
        """Process that simulates a courier picking up stuff at the pick up location"""

        self.state = 'picking_up'
        self._log(f'Courier {self.courier_id} begins pick up process')

        try:
            yield self.env.process(self.dispatcher.courier_available_event(courier=self))

        except Interrupt:
            pass

        while True:
            try:
                yield self.env.timeout(delay=service_time)
                break

            except Interrupt:
                break

        self._log(f'Courier {self.courier_id} finishes pick up process')

    def _dropping_off_process(self, service_time: float):
        """Process that simulates a courier dropping off stuff at the drop off location"""

        self.state = 'dropping_off'
        self._log(f'Courier {self.courier_id} begins drop off process')

        yield self.env.process(self.dispatcher.courier_idle_busy_event(courier=self, state='busy'))
        yield self.env.timeout(delay=service_time)

        self._log(f'Courier {self.courier_id} finishes drop off process')

    def _move_process(self, destination: Location):
        """Process detailing how a courier moves to a destination"""

        self.state = 'moving'
        yield self.env.process(self.dispatcher.courier_idle_busy_event(courier=self, state='busy'))

        yield self.env.process(
            self.movement_policy.execute(
                origin=self.location,
                destination=destination,
                env=self.env,
                courier=self
            )
        )

    def _execute_stop_process(self, stop: Stop):
        """Process to execute a stop"""

        self.active_stop = stop
        self._log(f'Courier {self.courier_id} is at stop {self.active_stop}')

        service_time = max(order.__getattribute__(f'{stop.type.label}_service_time') for order in stop.orders.values())
        service_process = self._picking_up_process if stop.type == StopType.PICK_UP else self._dropping_off_process
        yield self.env.process(service_process(service_time))

        if stop.type == StopType.PICK_UP:
            yield self.env.process(self.dispatcher.orders_picked_up_event(orders=stop.orders))

        elif stop.type == StopType.DROP_OFF:
            yield self.env.process(self.dispatcher.orders_dropped_off_event(orders=stop.orders, courier=self))

        stop.visited = True

    def _execute_active_route_process(self):
        """Process to execute the remainder of a route"""

        stops_remaining = [stop for stop in self.active_route.stops if not stop.visited]
        self._log(f'Courier {self.courier_id} has {len(stops_remaining)} stops remaining')

        for stop in stops_remaining:

            if self.active_stop != stop:
                self._log(f'Courier {self.courier_id} will move to next stop')
                yield self.env.process(self._move_process(destination=stop.location))

            if stop.type != StopType.PREPOSITION:
                yield self.env.process(self._execute_stop_process(stop))

        self.active_route = None
        self.active_stop = None

        self._log(f'Courier {self.courier_id} finishes route execution')

        self.process = self.env.process(self._idle_process())

    def _evaluate_movement_event(self):
        """Event detailing how a courier evaluates to move about the city"""

        destination = self.movement_evaluation_policy.execute(current_location=self.location)

        if destination is not None:
            self._log(f'Courier {self.courier_id} decided to move to {destination}')

            yield self.env.process(self._move_process(destination))

            self.state = 'idle'
            self.dispatcher.courier_idle_busy_event(courier=self, state=self.state)

        else:
            self._log(f'Courier {self.courier_id} decided not to move')

    def _log_off_callback(self, event: Event):
        """Callback detailing how a courier logs off of the system, ensuring earnings are calculated"""

        self._log(f'Courier {self.courier_id} is going to log off')

        self.earnings = self._calculate_earnings()
        self.env.process(self.dispatcher.courier_log_off_event(courier=self))
        event.succeed()
        event.callbacks = []

    def _schedule_log_off(self):
        """Method that allows the courier to schedule the log off time"""

        self.log_off_event = Event(env=self.env)
        self.log_off_event.callbacks.append(self._log_off_callback)
        log_off_delay = (
                datetime.combine(date.today(), self.off_time) - datetime.combine(date.today(), self.on_time)
        ).total_seconds()
        self.env.schedule(event=self.log_off_event, priority=NORMAL, delay=log_off_delay)

    def _calculate_earnings(self) -> float:
        """Method to calculate earnings after the shift ends"""

        earnings_per_hour = defaultdict(float)
        for timestamp, earning in self.hourly_earnings.items():
            earnings_per_hour[timestamp.hour] += earning

        adjusted_earnings = {
            hour: max(earning, settings.COURIER_EARNINGS_PER_HOUR)
            for hour, earning in earnings_per_hour.items()
        }

        earnings = sum(adjusted_earnings.values())
        self._log(
            f'Courier {self.courier_id} received earnings of ${earnings} '
            f'for {len(self.fulfilled_orders)} orders during the complete shift'
        )

        return earnings

    def notify_event(self, notification: Notification):
        """Event detailing how a courier handles a notification"""

        self._log(f'Courier {self.courier_id} received a {notification.type.label} notification')
        self.process.interrupt()

        accepts_notification = yield self.env.process(
            self.acceptance_policy.execute(self.acceptance_rate, self.env)
        )
        acceptance_log = (
            f'The instruction has {len(notification.instruction.orders)} orders'
            if notification.type == NotificationType.PICK_UP_DROP_OFF
            else ''
        )

        if accepts_notification:
            self._log(f'Courier {self.courier_id} accepted a {notification.type.label} notification. {acceptance_log}')
            yield self.env.process(self.dispatcher.notification_accepted_event(notification=notification, courier=self))
            yield self.env.process(self._execute_active_route_process())

        else:
            self._log(f'Courier {self.courier_id} rejected a {notification.type.label} notification. {acceptance_log}')
            yield self.env.process(self.dispatcher.notification_rejected_event(notification=notification, courier=self))

            if self.state == 'idle':
                self.process = self.env.process(self._idle_process())

            elif self.state == 'picking_up':
                yield self.env.process(self._execute_active_route_process())
