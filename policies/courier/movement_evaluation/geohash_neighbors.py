import random
from typing import Optional

import geohash

from settings import settings
from objects.location import Location
from policies.courier.movement_evaluation.courier_movement_evaluation_policy import CourierMovementEvaluationPolicy


class NeighborsMoveEvalPolicy(CourierMovementEvaluationPolicy):
    """
    Class containing the policy that decides how a courier evaluates moving about the city.
    It decides the destination randomly from the geohash neighbors, using a precision of 6.
    The destination is the center of the chosen geohash.
    """

    def execute(self, current_location: Location) -> Optional[Location]:
        """Execution of the Movement Evaluation Policy"""

        if random.random() <= settings.COURIER_MOVEMENT_PROBABILITY:
            current_geohash = geohash.encode(*current_location.coordinates, precision=6)
            geohash_neighbors = geohash.neighbors(current_geohash)
            destination_geohash = random.choice(geohash_neighbors)
            destination_coordinates = geohash.decode(destination_geohash)

            return Location(lat=destination_coordinates[0], lng=destination_coordinates[1])

        return None
