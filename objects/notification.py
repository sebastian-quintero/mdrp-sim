from dataclasses import dataclass
from enum import IntEnum
from typing import Union, Optional, Any, List

from objects.route import Route
from objects.stop import Stop

LABELS = {
    0: 'pick_and_drop',
    1: 'prepositioning'
}


class NotificationType(IntEnum):
    """Class that defines the possible values of a notification type"""

    PICK_UP_DROP_OFF = 0
    PREPOSITIONING = 1

    @property
    def label(self):
        """Property that returns the notification type's label"""

        return LABELS[self]


@dataclass
class Notification:
    """Class that represents a notification of a new Route or Stop"""

    courier: Optional[Any]
    instruction: Optional[Union[Route, List[Stop]]]
    type: NotificationType = NotificationType.PICK_UP_DROP_OFF

    def update(self, processed_order_ids: List[int]):
        """Method to update a notification if some of its orders have been processed"""

        if isinstance(self.instruction, Route):
            self.instruction.update(processed_order_ids)

        else:
            updated_stops, num_stops = [], 0
            for stop in self.instruction:
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

            self.instruction = updated_stops
