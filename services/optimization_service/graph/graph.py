from dataclasses import dataclass

import numpy as np


@dataclass
class Graph:
    """Class that repesents a directed graph"""

    nodes: np.ndarray
    arcs: np.ndarray
    incidence_matrix: np.ndarray
