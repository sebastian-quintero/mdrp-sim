from dataclasses import dataclass
from enum import IntEnum
from typing import Union, Optional, Any

from objects.route import Route
from objects.stop import Stop

LABELS = {
    0: 'pick_and_drop',
    1: 'prepositioning'
}


class NotificationType(IntEnum):
    """Class that defines the possible values of a notification type"""

    PICK_UP_DROP_OFF: int = 0
    PREPOSITIONING: int = 1

    @property
    def label(self):
        """Property that returns the notification type's label"""

        return LABELS[self]


@dataclass
class Notification:
    """Class that represents a notification of a new Route or Stop"""

    courier: Optional[Any]
    instruction: Optional[Union[Route, Stop]]
    type: NotificationType = NotificationType.PICK_UP_DROP_OFF
