from typing import Union

import numpy as np
from gurobipy import Var, Model, GRB
from pulp import LpVariable, LpProblem

from services.optimization_service.graph.graph import Graph
from services.optimization_service.model.model_builder import OptimizationModelBuilder


class GraphOptimizationModelBuilder(OptimizationModelBuilder):
    """Class that enables the construction of an optimization model for matching based on a network formulation"""

    def _build_variables(self, graph: Graph, engine_model: Union[LpProblem, Model]) -> np.ndarray:
        """Method to build the model decision variables from the graph"""

        i, j = graph.arcs['i'], graph.arcs['j']

        return np.vectorize(self._build_cont_bool_var, otypes=[np.object])(i, j, engine_model)

    @staticmethod
    def _build_objective(graph: Graph, variable_set: np.ndarray) -> np.ndarray:
        """Method to build the model's linear objective from the graph"""

        return np.dot(graph.arcs['c'], variable_set)

    def _build_cont_bool_var(
            self,
            i: np.ndarray,
            j: np.ndarray,
            engine_model: Union[LpProblem, Model]
    ) -> Union[LpVariable, Var]:
        """Method to build a continuous boolean variable"""

        if self._optimizer == 'pulp':
            var = LpVariable(f'x({i}, {j})', 0, 1)
        else:
            var = engine_model.addVar(lb=0, ub=1, vtype=GRB.CONTINUOUS, name=f'x({i}, {j})')

        return var
