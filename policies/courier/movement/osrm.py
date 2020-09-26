from haversine import haversine
from simpy import Environment

from objects.location import Location
from policies.courier.movement.courier_movement_policy import CourierMovementPolicy
from services.osrm_service import OSRMService


class OSRMMovementPolicy(CourierMovementPolicy):
    """
    Class containing the policy that implements the movement of a courier to a destination.
    It uses the Open Source Routing Machine with Open Street Maps.
    """

    def execute(self, origin: Location, destination: Location, env: Environment, courier):
        """Execution of the Movement Policy"""

        route = OSRMService.get_route(origin, destination)

        for ix in range(len(route.stops) - 1):
            stop = route.stops[ix]
            next_stop = route.stops[ix + 1]

            distance = haversine(stop.location.coordinates, next_stop.location.coordinates)
            time = int(distance / courier.vehicle.average_velocity)

            yield env.timeout(delay=time)

            courier.location = next_stop.location
