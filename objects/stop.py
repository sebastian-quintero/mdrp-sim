from dataclasses import dataclass, field
from datetime import time
from enum import IntEnum
from typing import Optional, Dict, Any

from objects.location import Location
from objects.order import Order
from objects.vehicle import Vehicle

LABELS = {
    0: 'pick_up',
    1: 'drop_off'
}


class StopType(IntEnum):
    """Class that defines the possible values of a stop type"""

    PICK_UP = 0
    DROP_OFF = 1
    PREPOSITION = 2

    @property
    def label(self):
        """Property that returns the stop type's label"""

        return LABELS[self]


@dataclass
class Stop:
    """Class describing the stop of a route"""

    arrive_at: Optional[Dict[Any, float]] = field(default_factory=lambda: dict())
    location: Optional[Location] = None
    orders: Optional[Dict[int, Order]] = None
    position: Optional[int] = 0
    type: Optional[StopType] = StopType.PICK_UP
    visited: Optional[bool] = False

    def __post_init__(self):
        """Immediate instantiation of some properties"""

        self.arrive_at = {v: 0 for v in Vehicle} if not bool(self.arrive_at) else self.arrive_at

    def calculate_service_time(self) -> float:
        """Method to calculate the service time at a stop"""

        return max(order.drop_off_service_time for order in self.orders.values())

    def calculate_latest_expected_time(self) -> time:
        """Method to calculate the latest expected time for a stop based on its type"""

        if self.type == StopType.PICK_UP:
            return max(order.ready_time for order in self.orders.values())

        elif self.type == StopType.DROP_OFF:
            return max(order.expected_drop_off_time for order in self.orders.values())
