from dataclasses import dataclass
from typing import List, Union, Optional

import numpy as np
from gurobipy import GRB, Model, Var, Constr
from pulp import LpProblem, LpConstraint, LpVariable, value, PULP_CBC_CMD, LpStatusOptimal

SOLUTION_VALUE = 0.99


@dataclass
class OptimizationModel:
    """Class that defines an optimization model to be solved"""

    constraints: List[Union[LpConstraint, Constr]]
    engine_model: Optional[Union[LpProblem, Model]]
    objective: np.ndarray
    optimizer: str
    sense: int
    variable_set: np.ndarray

    def solve(self):
        """Method for solving the optimization model"""

        if self.optimizer == 'pulp':
            for constraint in self.constraints:
                self.engine_model += constraint

            self.engine_model += self.objective
            status = self.engine_model.solve(PULP_CBC_CMD(msg=False))
            solution = (
                np.vectorize(self._var_sol)(self.variable_set)
                if status == LpStatusOptimal
                else np.array([])
            )

        else:
            for constraint in self.constraints:
                self.engine_model.addConstr(constraint)

            self.engine_model.setObjective(self.objective, self.sense)
            self.engine_model.optimize()
            solution = (
                np.vectorize(self._var_sol)(self.variable_set)
                if self.engine_model.status == GRB.OPTIMAL
                else np.array([])
            )

        return solution

    def _var_sol(self, var: Union[LpVariable, Var]) -> float:
        """Method to obtain the solution of a decision variable"""

        return value(var) if self.optimizer == 'pulp' else var.x
