from typing import List

import numpy as np
from pulp import LpVariable, LpConstraint

from services.optimization_service.graph.graph import Graph
from services.optimization_service.model.constraints.model_constraint import ModelConstraint
from services.optimization_service.model.optimization_model import OptimizationModel


class OptimizationModelBuilder:
    """Class that enables the construction of an optimization model for matching"""

    def __init__(self, sense: str, model_constraints: List[ModelConstraint]):
        """Instantiates a builder using the desired sense and constraints"""

        self._sense = sense
        self._model_constraints = model_constraints

    def build(self, graph: Graph) -> OptimizationModel:
        """Main method for building an optimization model"""

        variable_set = self._build_variables(graph)
        objective = self._build_objective(graph, variable_set)
        constraints = self._build_constraints(graph, variable_set)

        return OptimizationModel(
            variable_set=variable_set,
            objective=objective,
            constraints=constraints,
            sense=self._sense
        )

    def _build_variables(self, graph: Graph) -> np.ndarray:
        """Method to build the model decision variables from the graph"""

        i, j = graph.arcs['i'], graph.arcs['j']

        return np.vectorize(self._build_bool_var, otypes=[np.object])(i, j)

    def _build_constraints(self, graph: Graph, variable_set: np.ndarray) -> List[LpConstraint]:
        """Method to build the linear constraints using the graph and decision variables"""

        constraints = []
        for model_constraint in self._model_constraints:
            constraints += model_constraint.express(graph, variable_set)

        return constraints

    @staticmethod
    def _build_objective(graph: Graph, variable_set: np.ndarray) -> np.ndarray:
        """Method to build the model's linear objective from the graph"""

        return np.dot(graph.arcs['c'], variable_set)

    @staticmethod
    def _build_bool_var(i: np.ndarray, j: np.ndarray) -> LpVariable:
        """Method to build a boolean variable"""

        return LpVariable(f'x({i}, {j})', 0, 1)
