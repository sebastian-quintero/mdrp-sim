import logging

import requests
from haversine import haversine
from simpy import Environment

from models.location import Location
from models.route import Route
from models.stop import Stop
from policies.policy import Policy
from utils.datetime_utils import sec_to_time


class OSRMMovementPolicy(Policy):
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
            print(f'sim time: {sec_to_time(env.now)} | state: {courier.state} | Courier will move from {stop.location} to {next_stop.location}')
            yield env.timeout(delay=time)
            print(f'sim time: {sec_to_time(env.now)} | state: {courier.state} | Courier has moved, is now at {next_stop.location}')
            courier.location = next_stop.location

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
