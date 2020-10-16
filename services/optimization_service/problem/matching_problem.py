from dataclasses import dataclass
from typing import List

import numpy as np

from actors.courier import Courier
from objects.route import Route


@dataclass
class MatchingProblem:
    """Class that represents a matching problem that must be solved"""

    routes: List[Route]
    couriers: List[Courier]
    prospects: np.ndarray
    matching_prospects: np.ndarray
    costs: np.ndarray
