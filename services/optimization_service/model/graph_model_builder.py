import numpy as np
from pulp import LpVariable

from services.optimization_service.graph.graph import Graph
from services.optimization_service.model.model_builder import OptimizationModelBuilder


class GraphOptimizationModelBuilder(OptimizationModelBuilder):
    """Class that enables the construction of an optimization model for matching based on a network formulation"""

    def _build_variables(self, graph: Graph) -> np.ndarray:
        """Method to build the model decision variables from the graph"""

        i, j = graph.arcs['i'], graph.arcs['j']

        return np.vectorize(self._build_cont_bool_var, otypes=[np.object])(i, j)

    @staticmethod
    def _build_objective(graph: Graph, variable_set: np.ndarray) -> np.ndarray:
        """Method to build the model's linear objective from the graph"""

        return np.dot(graph.arcs['c'], variable_set)

    @staticmethod
    def _build_cont_bool_var(i: np.ndarray, j: np.ndarray) -> LpVariable:
        """Method to build a continuous boolean variable"""

        return LpVariable(f'x({i}, {j})', 0, 1)
