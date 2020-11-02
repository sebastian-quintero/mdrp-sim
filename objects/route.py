import copy
import uuid
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

from objects.location import Location
from objects.order import Order
from objects.stop import Stop, StopType
from objects.vehicle import Vehicle
from utils.datetime_utils import time_to_sec


@dataclass
class Route:
    """Class describing a route for either moving or fulfilling"""

    initial_prospect: int = None
    num_stops: Optional[int] = 0
    orders: Optional[Dict[int, Order]] = field(default_factory=lambda: dict())
    route_id: Optional[str] = ''
    stops: Optional[List[Stop]] = field(default_factory=lambda: list())
    time: Optional[Dict[Any, float]] = field(default_factory=lambda: dict())

    def __post_init__(self):
        """Post process of the route creation"""
        self.stops = [Stop()] * self.num_stops if self.num_stops else self.stops
        self.num_stops = len(self.stops)
        self.time = {v: 0 for v in Vehicle}

        if bool(self.orders):
            self.time = self._calculate_time()

        self.route_id = str(uuid.uuid4())[0:8]

    def time_since_ready(self, env_time: int) -> float:
        """Property to calculate how much time has passed since the route is ready to be picked up"""

        return max(max(env_time - time_to_sec(order.ready_time), 0) for order in self.orders.values())

    @classmethod
    def from_order(cls, order: Order):
        """Method to instantiate a route from an order"""

        orders = {order.order_id: order}
        pick_up_stop = Stop(
            location=order.pick_up_at,
            orders=orders,
            position=0,
            type=StopType.PICK_UP,
            visited=False
        )
        drop_off_stop = Stop(
            location=order.drop_off_at,
            orders=orders,
            position=1,
            type=StopType.DROP_OFF,
            visited=False
        )

        return cls(
            orders=orders,
            stops=[pick_up_stop, drop_off_stop]
        )

    def update(self, processed_order_ids: List[int]):
        """Method to update a route if some of its orders have been processed"""

        updated_stops, num_stops = [], 0
        for stop in self.stops:
            updated_orders = {
                order_id: order
                for order_id, order in stop.orders.items()
                if order_id not in processed_order_ids
            }

            if bool(updated_orders):
                updated_stops.append(
                    Stop(
                        arrive_at=stop.arrive_at,
                        location=stop.location,
                        orders=updated_orders,
                        position=num_stops,
                        type=stop.type,
                        visited=stop.visited
                    )
                )
                num_stops += 1

        self.stops = updated_stops
        self.orders = {
            order_id: order
            for order_id, order in self.orders.items()
            if order_id not in processed_order_ids
        }
        self.num_stops = len(self.stops)
        self.time = self._calculate_time()

    def add_order(self, order: Order, route_position: Optional[int] = 1):
        """Method to add an order to the route"""

        if not bool(self.orders):
            pick_up_stop = Stop(
                location=order.pick_up_at,
                orders={order.order_id: order},
                position=0,
                type=StopType.PICK_UP,
                visited=False
            )
            drop_off_stop = Stop(
                location=order.drop_off_at,
                orders={order.order_id: order},
                position=1,
                type=StopType.DROP_OFF,
                visited=False
            )
            self.orders[order.order_id] = order
            self.stops[0] = pick_up_stop
            self.stops[1] = drop_off_stop
            time = self._calculate_time()

        else:
            self.orders[order.order_id] = order
            self.stops[0].orders[order.order_id] = order
            stop = Stop(
                location=order.drop_off_at,
                orders={order.order_id: order},
                position=route_position,
                type=StopType.DROP_OFF,
                visited=False
            )

            position = max(route_position, len(self.stops) - 1)

            if position <= len(self.stops) - 1 and not bool(self.stops[position].orders):
                self.stops[position] = stop

            else:
                position = len(self.stops)
                stop.position = position
                self.stops.append(stop)

            time = self.calculate_time_update(
                destination=stop.location,
                origin=self.stops[position - 1].location,
                service_time=stop.calculate_service_time()
            )
            stop.arrive_at = copy.deepcopy(time)

        self.time = time
        self.num_stops = len(self.stops)

    def add_stops(self, target_size: int):
        """Method to add empty stops to the route based on a target size"""

        while len(self.stops) - 1 < target_size:
            self.stops.append(Stop())

        self.num_stops = len(self.stops)

    def update_stops(self):
        """Method to remove empty stops from the route"""

        stops, counter = [], 0
        for stop in self.stops:
            if bool(stop.orders):
                stops.append(
                    Stop(
                        arrive_at=stop.arrive_at,
                        location=stop.location,
                        orders=stop.orders,
                        position=counter,
                        type=stop.type,
                        visited=stop.visited
                    )
                )
                counter += 1

        self.stops = stops
        self.num_stops = len(self.stops)

    def calculate_time_update(self, destination: Location, origin: Location, service_time: float) -> Dict[Any, float]:
        """Method to update the route time based on a new stop"""

        from services.osrm_service import OSRMService

        time = {v: t for v, t in self.time.items()}
        OSRMService.update_estimate_time_for_vehicles(
            origin=origin,
            destination=destination,
            time=time,
            service_time=service_time
        )

        return time

    def _calculate_time(self) -> Dict[Any, float]:
        """Method to calculate the route time based on the available stops"""

        from services.osrm_service import OSRMService

        stops = [stop for stop in self.stops if bool(stop.orders)]
        time = {v: t for v, t in self.time.items()}

        for ix in range(len(stops) - 1):
            origin = stops[ix]
            destination = stops[ix + 1]
            OSRMService.update_estimate_time_for_vehicles(
                origin=origin.location,
                destination=destination.location,
                time=time,
                service_time=destination.calculate_service_time()
            )
            destination.arrive_at = copy.deepcopy(time)

        return time
