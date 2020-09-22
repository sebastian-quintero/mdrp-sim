from dataclasses import dataclass
from enum import IntEnum
from typing import Optional, Dict

from objects.location import Location
from objects.order import Order

LABELS = {
    0: 'pick_up',
    1: 'drop_off'
}


class StopType(IntEnum):
    """Class that defines the possible values of a stop type"""

    PICK_UP: int = 0
    DROP_OFF: int = 1
    PREPOSITION: int = 2

    @property
    def label(self):
        """Property that returns the stop type's label"""

        return LABELS[self]


@dataclass
class Stop:
    """Class describing the stop of a route"""

    location: Optional[Location] = None
    position: Optional[int] = 0
    orders: Optional[Dict[int, Order]] = None
    type: Optional[StopType] = StopType.PICK_UP
    visited: Optional[bool] = False
