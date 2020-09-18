from dataclasses import dataclass
from typing import Union, Optional, Any

from objects.route import Route
from objects.stop import Stop


@dataclass
class Notification:
    """Class that represents a notification of a new Route or Stop"""

    courier: Optional[Any]
    instruction: Optional[Union[Route, Stop]]
    type: str = ''
