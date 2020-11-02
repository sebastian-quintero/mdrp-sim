from typing import List

import numpy as np
import numpy.lib.recfunctions as rfn

from actors.courier import Courier
from objects.route import Route
from services.optimization_service.problem.matching_problem import MatchingProblem


class MatchingProblemBuilder:
    """Class to build a matching problem that must be solved"""

    @classmethod
    def build(cls, routes: List[Route], couriers: List[Courier], prospects: np.ndarray, costs: np.ndarray):
        """Main method to build a matching problem"""

        return MatchingProblem(
            routes=routes,
            couriers=couriers,
            prospects=prospects,
            matching_prospects=cls._build_matching_prospects(routes, couriers, prospects),
            costs=costs
        )

    @staticmethod
    def _build_matching_prospects(routes: List[Route], couriers: List[Courier], prospects: np.ndarray) -> np.ndarray:
        """Method to build prospects that relate id's instead of indices"""

        if not prospects.tolist():
            return np.empty([0])

        courier_ids = np.array([courier.courier_id for courier in couriers], dtype=[('i', '<U100')])
        route_ids = np.array([route.route_id for route in routes], dtype=[('j', '<U100')])

        courier_ids_ix, route_ids_ix = prospects[:, 0], prospects[:, 1]
        selected_couriers, selected_routes = courier_ids[courier_ids_ix], route_ids[route_ids_ix]

        return rfn.merge_arrays([selected_couriers, selected_routes], flatten=True, usemask=False)
