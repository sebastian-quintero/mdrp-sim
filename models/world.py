from dataclasses import dataclass, field
from typing import Dict

from models.order import Order


@dataclass
class World:
    """A class to handle the simulated world"""

    active_orders: Dict[int, Order] = field(default_factory=lambda: dict())

    def new_order_event(self, order: Order):
        """Event detailing the submission of a new order by a user"""

        self.active_orders[order.order_id] = order
