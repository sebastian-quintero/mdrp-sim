import random
from typing import Optional

import geohash

import settings
from models.location import Location
from policies.policy import Policy


class NeighborsMoveEvalPolicy(Policy):
    """
    Class containing the policy that decides how a courier evaluates moving about the city.
    It decides the destination randomly from the geohash neighbors.
    """

    def execute(self, current_location: Location) -> Optional[Location]:
        """Execution of the Movement Evaluation Policy"""

        if random.random() <= settings.COURIER_MOVEMENT_PROBABILITY:
            current_geohash = geohash.encode(*current_location.coordinates, precision=6)
            geohash_neighbors = geohash.neighbors(current_geohash)
            destination_geohash = random.choice(geohash_neighbors)
            destination_coordinates = geohash.decode(destination_geohash)
            destination = Location(lat=destination_coordinates[0], lng=destination_coordinates[1])

        else:
            destination = None

        return destination
