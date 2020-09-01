from enum import IntEnum

from utils.datetime_utils import hour_to_sec

DEFAULT_VELOCITY = {
    0: 5 / hour_to_sec(1),
    1: 15 / hour_to_sec(1),
    2: 23 / hour_to_sec(1),
    3: 25 / hour_to_sec(1)

}

LABELS = {
    0: 'walking',
    1: 'bicycle',
    2: 'motorcycle',
    3: 'car'
}

LABELS_MAP = {
    'walking': 0,
    'bicycle': 1,
    'motorcycle': 2,
    'car': 3
}


class Vehicle(IntEnum):
    """A class that handles courier vehicles"""

    WALKER = 0
    BICYCLE = 1
    MOTORCYCLE = 2
    CAR = 3

    @property
    def average_velocity(self) -> float:
        """Property indicating the vehicle's average velocity"""

        return DEFAULT_VELOCITY[self]

    @property
    def label(self):
        """Property that returns the vehicle's label"""

        return LABELS[self]

    @classmethod
    def from_label(cls, label: str):
        """Method to create a vehicle from a label"""

        return cls(LABELS_MAP[label])
