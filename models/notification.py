from dataclasses import dataclass
from typing import Union

from models.route import Route
from models.stop import Stop


@dataclass
class Notification:
    """Class that represents a notification of a new Route or Stop"""

    courier_id: int
    instruction: Union[Route, Stop]
