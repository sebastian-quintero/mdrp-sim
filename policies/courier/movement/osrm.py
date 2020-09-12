import logging

import requests
from haversine import haversine
from simpy import Environment

from objects.location import Location
from objects.route import Route
from objects.stop import Stop
from policies.courier.movement.courier_movement_policy import CourierMovementPolicy
from utils.logging_utils import log


class OSRMMovementPolicy(CourierMovementPolicy):
    """
    Class containing the policy that implements the movement of a courier to a destination.
    It uses the Open Source Routing Machine with Open Street Maps.
    """

    URL = 'http://127.0.0.1:5000/route/v1/driving/{lng_0},{lat_0};{lng_1},{lat_1}?alternatives=false&steps=true'

    def execute(self, origin: Location, destination: Location, env: Environment, courier):
        """Execution of the Movement Policy"""

        route = self._get_route(origin, destination)

        for ix in range(len(route.stops) - 1):
            stop = route.stops[ix]
            next_stop = route.stops[ix + 1]

            distance = haversine(stop.location.coordinates, next_stop.location.coordinates)
            time = int(distance / courier.vehicle.average_velocity)

            log(env, 'Courier', courier.state, f'Courier {courier.courier_id} will move from {stop.location}')

            yield env.timeout(delay=time)
            courier.location = next_stop.location

            log(env, 'Courier', courier.state, f'Courier {courier.courier_id} has moved to {next_stop.location}')

    def _get_route(self, origin: Location, destination: Location) -> Route:
        """Method to obtain a movement route using docker-mounted OSRM"""

        lat_0, lng_0 = origin.coordinates
        lat_1, lng_1 = destination.coordinates

        url = self.URL.format(lng_0=lng_0, lat_0=lat_0, lng_1=lng_1, lat_1=lat_1)

        try:
            response = requests.get(url)

            if response and response.status_code in [requests.codes.ok, requests.codes.no_content]:
                response_data = response.json()
                steps = response_data.get('routes', [])[0].get('legs', [])[0].get('steps', [])

                stops = []
                for ix, step in enumerate(steps):
                    lng, lat = step.get('maneuver', {}).get('location', [])
                    stop = Stop(
                        location=Location(lat=lat, lng=lng),
                        position=ix
                    )
                    stops.append(stop)

                return Route(stops=stops)

        except:
            logging.exception('Exception captured in OSRMMovementPolicy._get_route. Check Docker.')

            return Route(stops=[])
