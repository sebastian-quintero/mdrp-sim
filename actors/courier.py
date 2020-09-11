import random
import time
from dataclasses import dataclass, field
from typing import List, Optional, Union, Any

from simpy import Environment, Interrupt, Process

import settings
from models.location import Location
from models.route import Route
from models.stop import Stop
from models.vehicle import Vehicle
from policies.courier.osrm_movement_policy import OSRMMovementPolicy
from policies.courier.neighbors_move_eval_policy import NeighborsMoveEvalPolicy
from policies.courier.uniform_acceptance_policy import UniformAcceptancePolicy
from policies.policy import Policy
from utils.datetime_utils import sec_to_time


@dataclass
class Courier:
    """A class used to handle a courier's state and events."""

    dispatcher: Any
    env: Environment
    acceptance_policy: Optional[Union[Policy, UniformAcceptancePolicy]] = UniformAcceptancePolicy()
    movement_evaluation_policy: Optional[Union[Policy, NeighborsMoveEvalPolicy]] = NeighborsMoveEvalPolicy()
    movement_policy: Optional[Union[Policy, OSRMMovementPolicy]] = OSRMMovementPolicy()

    courier_id: Optional[int] = None
    vehicle: Optional[Vehicle] = Vehicle.MOTORCYCLE
    acceptance_rate: float = random.uniform(settings.COURIER_MIN_ACCEPTANCE_RATE, 1)
    active_route: Optional[Route] = None
    active_stop: Optional[Stop] = None
    location: Optional[Location] = None
    process: Optional[Process] = None
    rejected_orders: List[int] = field(default_factory=lambda: list())
    state: str = ''

    on_time: time = None
    off_time: time = None

    def __post_init__(self):
        """Immediately after the courier logs on, it starts idling"""

        self.process = self.env.process(self._idle_process())

    def _idle_process(self):
        """Process that simulates a courier being idle / waiting"""

        self.state = 'idle'
        self.dispatcher.courier_idle_event(courier=self)

        while True:
            try:
                yield self.env.timeout(delay=settings.COURIER_WAIT_TO_MOVE)
                yield self.env.process(self._evaluate_movement_event())

            except Interrupt:
                break

    def _picking_up_process(self, service_time: float):
        """Process that simulates a courier picking up stuff at the pick up location"""

        self.state = 'picking_up'
        self.dispatcher.courier_available_event(courier=self)

        while True:
            try:
                yield self.env.timeout(delay=service_time)
                break

            except Interrupt:
                break

    def _dropping_off_process(self, service_time: float):
        """Process that simulates a courier dropping off stuff at the drop off location"""

        self.state = 'dropping_off'
        self.dispatcher.courier_busy_event(courier=self)
        yield self.env.timeout(delay=service_time)

    def _move_process(self, destination: Location):
        """Process detailing how a courier moves to a destination"""

        self.state = 'moving'
        self.dispatcher.courier_busy_event(courier=self)
        yield self.env.process(
            self.movement_policy.execute(
                origin=self.location,
                destination=destination,
                env=self.env,
                courier=self
            )
        )
        self.state = 'idle'
        self.dispatcher.courier_idle_event(courier=self)

    def _execute_stop_process(self, stop: Stop):
        """Process to execute a stop"""

        if self.active_stop != stop:
            print(
                f'sim time: {sec_to_time(self.env.now)} | state: {self.state} | Courier will move to next stop'
            )
            yield self.env.process(self._move_process(destination=stop.location))

        self.active_stop = stop
        print(
            f'sim time: {sec_to_time(self.env.now)} | state: {self.state} | Courier is at stop {self.active_stop}'
        )
        print(
            f'sim time: {sec_to_time(self.env.now)} | state: {self.state} | Courier begins {stop.type} process'
        )
        service_time = sum(order.__getattribute__(f'{stop.type}_service_time') for order in stop.orders.values())
        service_process = self._picking_up_process if stop.type == 'pick_up' else self._dropping_off_process
        self.process = self.env.process(service_process(service_time))
        print(
            f'sim time: {sec_to_time(self.env.now)} | state: {self.state} | Courier finishes {stop.type} process'
        )

        if stop.type == 'pick_up':
            self.dispatcher.orders_picked_up_event(orders=stop.orders)
        elif stop.type == 'drop_off':
            self.dispatcher.orders_dropped_off_event(orders=stop.orders)

        stop.visited = True

    def _execute_active_route_process(self):
        """Process to execute the remainder of a route"""

        stops_remaining = [stop for stop in self.active_route.stops if not stop.visited]
        print(
            f'sim time: {sec_to_time(self.env.now)} | state: {self.state} | '
            f'Courier has {len(stops_remaining)} stops remaining'
        )
        for stop in stops_remaining:
            yield self.env.process(self._execute_stop_process(stop))

        self.active_route = None
        self.active_stop = None
        print(
            f'sim time: {sec_to_time(self.env.now)} | state: {self.state} | Courier finishes route execution'
        )
        self.process = self.env.process(self._idle_process())

    def _evaluate_movement_event(self):
        """Event detailing how a courier evaluates to move about the city"""

        destination = self.movement_evaluation_policy.execute(current_location=self.location)

        if destination is not None:
            print(
                f'sim time: {sec_to_time(self.env.now)} | state: {self.state} | Courier decided to move to {destination}')
            yield self.env.process(self._move_process(destination))

        else:
            print(f'sim time: {sec_to_time(self.env.now)} | state: {self.state} | Courier decided not to move')

    def notify_event(self, instruction: Union[Route, Stop]):
        """Event detailing how a courier handles a notification"""

        print(f'sim time: {sec_to_time(self.env.now)} | state: {self.state} | Courier received notification')
        self.process.interrupt()

        accepts_notification = yield self.env.process(
            self.acceptance_policy.execute(self.acceptance_rate, self.env)
        )

        if accepts_notification:
            self.dispatcher.notification_accepted_event(instruction=instruction, courier=self)
            yield self.env.process(self._execute_active_route_process())

        else:
            self.dispatcher.notification_rejected_event(instruction=instruction, courier=self)

            if self.state == 'idle':
                self.process = self.env.process(self._idle_process())

            elif self.state == 'picking_up':
                yield self.env.process(self._execute_active_route_process())
