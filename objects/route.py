from dataclasses import dataclass
from typing import List, Optional, Dict

from objects.order import Order
from objects.stop import Stop


@dataclass
class Route:
    """Class describing a route for either moving or fulfilling"""

    stops: List[Stop]
    orders: Optional[Dict[int, Order]] = None
