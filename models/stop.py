from dataclasses import dataclass
from typing import Optional, Dict

from models.location import Location
from models.order import Order


@dataclass
class Stop:
    """Class describing the stop of a route"""

    location: Optional[Location] = None
    position: Optional[int] = 0
    orders: Optional[Dict[int, Order]] = None
    type: Optional[str] = ''
    visited: Optional[bool] = False
