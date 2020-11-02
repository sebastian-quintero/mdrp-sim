from typing import List

import numpy as np
from pulp import LpConstraint

from services.optimization_service.graph.graph import Graph
from services.optimization_service.model.constraints.model_constraint import ModelConstraint


class BalanceConstraint(ModelConstraint):
    """Class containing the main balance constraint for a network flow formulation"""

    def express(self, graph: Graph, variable_set: np.ndarray) -> List[LpConstraint]:
        """Expression of the balance constraint"""

        demands = graph.nodes['demand']
        constraints = [None] * len(graph.nodes)

        for n in range(len(graph.nodes)):
            out_flow = variable_set[np.where(graph.incidence_matrix[n] == 1)]
            in_flow = variable_set[np.where(graph.incidence_matrix[n] == -1)]
            constraints[n] = np.sum(out_flow) - np.sum(in_flow) == demands[n]

        return constraints
