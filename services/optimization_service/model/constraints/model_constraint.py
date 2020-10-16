from typing import List

import numpy as np
from pulp import LpConstraint

from services.optimization_service.graph.graph import Graph


class ModelConstraint:
    """Class that defines how a constraint is expressed for the model"""

    def express(self, graph: Graph, variable_set: np.ndarray) -> List[LpConstraint]:
        """Method to express a model constraint into a standard format"""

        pass
