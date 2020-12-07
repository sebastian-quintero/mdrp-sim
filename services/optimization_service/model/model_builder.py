from typing import List, Union

import numpy as np
from gurobipy import Constr, GRB, Model, Env
from pulp import LpConstraint, LpMinimize, LpMaximize, LpProblem

from services.optimization_service.model.constraints.model_constraint import ModelConstraint
from services.optimization_service.model.optimization_model import OptimizationModel


class OptimizationModelBuilder:
    """Class that enables the construction of an optimization model for matching"""

    def __init__(self, sense: str, model_constraints: List[ModelConstraint], optimizer: str):
        """Instantiates a builder using the desired sense and constraints"""

        self._sense = sense
        self._model_constraints = model_constraints
        self._optimizer = optimizer

    def build(self, *args) -> OptimizationModel:
        """Main method for building an optimization model"""

        if self._optimizer == 'pulp':
            sense = LpMinimize if self._sense == 'min' else LpMaximize
            engine_model = LpProblem('problem', sense)

        else:
            sense = GRB.MINIMIZE if self._sense == 'min' else GRB.MAXIMIZE
            env = Env(empty=True)
            env.setParam('OutputFlag', 0)
            env.start()
            engine_model = Model('problem', env=env)

        variable_set = self._build_variables(args[0], engine_model)
        objective = self._build_objective(args[0], variable_set)
        constraints = self._build_constraints(args[0], variable_set)

        return OptimizationModel(
            constraints=constraints,
            engine_model=engine_model,
            objective=objective,
            optimizer=self._optimizer,
            sense=sense,
            variable_set=variable_set,
        )

    def _build_variables(self, *args, **kwargs) -> np.ndarray:
        """Method to build the model decision variables"""

        pass

    def _build_objective(self, *args, **kwargs) -> np.ndarray:
        """Method to build the model's linear objective"""

        pass

    def _build_constraints(self, *args, **kwargs) -> List[Union[LpConstraint, Constr]]:
        """Method to build the linear constraints using the decision variables"""

        constraints = []
        for model_constraint in self._model_constraints:
            constraints += model_constraint.express(*args, **kwargs)

        return constraints
