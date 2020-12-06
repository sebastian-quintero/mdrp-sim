from dataclasses import dataclass
from typing import Any, Dict

from numpy import int64


@dataclass
class MatchingMetric:
    """Class to store results of a dispatch event"""

    constraints: int64
    couriers: int
    matches: int
    matching_time: float
    orders: int
    routes: int
    routing_time: float
    variables: int64

    def calculate_metrics(self) -> Dict[str, Any]:
        """Method to calculate metrics of a dispatch event"""

        return self.__dict__
