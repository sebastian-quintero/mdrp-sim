from dataclasses import dataclass
from typing import List

import numpy as np
from pulp import LpMinimize, LpMaximize, LpProblem, LpConstraint, LpVariable, value, LpStatus, PULP_CBC_CMD

SOLUTION_VALUE = 0.99


@dataclass
class OptimizationModel:
    """Class that defines an optimization model to be solved"""

    variable_set: np.ndarray
    objective: np.ndarray
    constraints: List[LpConstraint]
    sense: str

    def solve(self):
        """Method for solving the optimization model"""

        sense = LpMinimize if self.sense == 'min' else LpMaximize
        prob = LpProblem('problem', sense)

        for constraint in self.constraints:
            prob += constraint

        prob += self.objective

        status = prob.solve(PULP_CBC_CMD(msg=False))
        solution = np.vectorize(self._var_sol)(self.variable_set) if LpStatus[status] == 'Optimal' else np.array([])

        return solution

    @staticmethod
    def _var_sol(var: LpVariable) -> float:
        """Method to obtain the solution of a decision variable"""

        return value(var)
