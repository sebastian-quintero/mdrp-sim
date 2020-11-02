from typing import List

import numpy as np
from pulp import LpConstraint

from services.optimization_service.model.constraints.model_constraint import ModelConstraint
from services.optimization_service.model.optimization_model import OptimizationModel


class OptimizationModelBuilder:
    """Class that enables the construction of an optimization model for matching"""

    def __init__(self, sense: str, model_constraints: List[ModelConstraint]):
        """Instantiates a builder using the desired sense and constraints"""

        self._sense = sense
        self._model_constraints = model_constraints

    def build(self, *args) -> OptimizationModel:
        """Main method for building an optimization model"""

        variable_set = self._build_variables(args[0])
        objective = self._build_objective(args[0], variable_set)
        constraints = self._build_constraints(args[0], variable_set)

        return OptimizationModel(
            variable_set=variable_set,
            objective=objective,
            constraints=constraints,
            sense=self._sense
        )

    def _build_variables(self, *args, **kwargs) -> np.ndarray:
        """Method to build the model decision variables"""

        pass

    def _build_constraints(self, *args, **kwargs) -> List[LpConstraint]:
        """Method to build the linear constraints using the decision variables"""

        constraints = []
        for model_constraint in self._model_constraints:
            constraints += model_constraint.express(*args, **kwargs)

        return constraints

    def _build_objective(self, *args, **kwargs) -> np.ndarray:
        """Method to build the model's linear objective"""

        pass
