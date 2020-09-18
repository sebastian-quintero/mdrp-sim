import random
import time
from dataclasses import dataclass, field
from typing import List, Optional, Any

from simpy import Interrupt

import settings
from actors.actor import Actor
from objects.location import Location
from objects.notification import Notification
from objects.route import Route
from objects.stop import Stop
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
    earnings: Optional[float] = None  # TODO: implement earnings scheme
    location: Optional[Location] = None
    rejected_orders: List[int] = field(default_factory=lambda: list())
    vehicle: Optional[Vehicle] = Vehicle.MOTORCYCLE

    on_time: time = None
    off_time: time = None

    def _idle_process(self):
        """Process that simulates a courier being idle / waiting"""

        self.state = 'idle'
        self._log(f'Courier {self.courier_id} begins idling')

        try:
            yield self.env.process(self.dispatcher.courier_idle_event(courier=self))

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

        yield self.env.process(self.dispatcher.courier_busy_event(courier=self))
        yield self.env.timeout(delay=service_time)

        self._log(f'Courier {self.courier_id} finishes drop off process')

    def _move_process(self, destination: Location):
        """Process detailing how a courier moves to a destination"""

        self.state = 'moving'
        yield self.env.process(self.dispatcher.courier_busy_event(courier=self))

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

        service_time = max(order.__getattribute__(f'{stop.type}_service_time') for order in stop.orders.values())
        service_process = self._picking_up_process if stop.type == 'pick_up' else self._dropping_off_process
        yield self.env.process(service_process(service_time))

        if stop.type == 'pick_up':
            yield self.env.process(self.dispatcher.orders_picked_up_event(orders=stop.orders))

        elif stop.type == 'drop_off':
            yield self.env.process(self.dispatcher.orders_dropped_off_event(orders=stop.orders))

        stop.visited = True

    def _execute_active_route_process(self):
        """Process to execute the remainder of a route"""

        stops_remaining = [stop for stop in self.active_route.stops if not stop.visited]
        self._log(f'Courier {self.courier_id} has {len(stops_remaining)} stops remaining')

        for stop in stops_remaining:

            if self.active_stop != stop:
                self._log(f'Courier {self.courier_id} will move to next stop')
                yield self.env.process(self._move_process(destination=stop.location))

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
            self.dispatcher.courier_idle_event(courier=self)

        else:
            self._log(f'Courier {self.courier_id} decided not to move')

    def notify_event(self, notification: Notification):
        """Event detailing how a courier handles a notification"""

        self._log(f'Courier {self.courier_id} received a {notification.type} notification')
        self.process.interrupt()

        accepts_notification = yield self.env.process(
            self.acceptance_policy.execute(self.acceptance_rate, self.env)
        )
        acceptance_log = (
            f'The instruction has {len(notification.instruction.orders)} orders'
            if notification.type == 'pick up & drop off'
            else ''
        )

        if accepts_notification:
            self._log(f'Courier {self.courier_id} accepted a {notification.type} notification. {acceptance_log}')
            yield self.env.process(self.dispatcher.notification_accepted_event(notification=notification, courier=self))
            yield self.env.process(self._execute_active_route_process())

        else:
            self._log(f'Courier {self.courier_id} rejected a {notification.type} notification. {acceptance_log}')
            yield self.env.process(self.dispatcher.notification_rejected_event(notification=notification, courier=self))

            if self.state == 'idle':
                self.process = self.env.process(self._idle_process())

            elif self.state == 'picking_up':
                yield self.env.process(self._execute_active_route_process())

    def log_off_event(self):
        """Event detailing how a courier logs off of the system"""

        # TODO: finish this event
        yield self.env.timeout(delay=1)
