from dataclasses import dataclass
from typing import List, Optional, Dict

from objects.order import Order
from objects.stop import Stop


@dataclass
class Route:
    """Class describing a route for either moving or fulfilling"""

    stops: List[Stop]
    orders: Optional[Dict[int, Order]] = None

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
