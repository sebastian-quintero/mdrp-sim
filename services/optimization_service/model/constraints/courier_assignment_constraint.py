from typing import List

import numpy as np
from pulp import LpConstraint

from services.optimization_service.model.constraints.model_constraint import ModelConstraint
from services.optimization_service.problem.matching_problem import MatchingProblem


class CourierAssignmentConstraint(ModelConstraint):
    """Class containing the constraint that limits the assignments per courier"""

    def express(self, problem: MatchingProblem, variable_set: np.ndarray) -> List[LpConstraint]:
        """Expression of the constraint"""

        unique_couriers = np.unique(problem.matching_prospects['i'])
        constraints = [None] * len(unique_couriers)

        for ix, courier in enumerate(unique_couriers):
            routes_indices = np.where(problem.matching_prospects['i'] == courier)
            courier_routes = variable_set[routes_indices]
            constraints[ix] = np.sum(courier_routes) <= 1

        return constraints
