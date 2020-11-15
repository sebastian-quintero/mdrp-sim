from typing import List

import numpy as np
from pulp import LpConstraint

from services.optimization_service.model.constraints.model_constraint import ModelConstraint
from services.optimization_service.problem.matching_problem import MatchingProblem


class RouteAssignmentConstraint(ModelConstraint):
    """Class containing the constraint that limits the assignments per route"""

    def express(self, problem: MatchingProblem, variable_set: np.ndarray) -> List[LpConstraint]:
        """Expression of the constraint"""

        unique_routes = np.unique(problem.matching_prospects['j'])
        constraints = [None] * len(unique_routes)

        for ix, route in enumerate(unique_routes):
            courier_indices = np.where(problem.matching_prospects['j'] == route)
            route_couriers = variable_set[courier_indices]
            supply_courier = variable_set[len(problem.matching_prospects) + ix]
            constraints[ix] = np.sum(route_couriers) + supply_courier == 1

        return constraints
