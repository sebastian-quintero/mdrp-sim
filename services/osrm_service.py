import logging
from typing import Tuple

import requests
from haversine import haversine

from objects.location import Location
from objects.route import Route
from objects.stop import Stop
from objects.vehicle import Vehicle


class OSRMService:
    """Class that contains the Open Source Routing Machine service to obtain city routes"""

    URL = 'http://127.0.0.1:5000/route/v1/driving/{lng_0},{lat_0};{lng_1},{lat_1}?alternatives=false&steps=true'

    @classmethod
    def get_route(cls, origin: Location, destination: Location) -> Route:
        """Method to obtain a movement route using docker-mounted OSRM"""

        lat_0, lng_0 = origin.coordinates
        lat_1, lng_1 = destination.coordinates

        url = cls.URL.format(lng_0=lng_0, lat_0=lat_0, lng_1=lng_1, lat_1=lat_1)

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
            logging.exception('Exception captured in OSRMService.get_route. Check Docker.')

            return Route(stops=[])

    @classmethod
    def estimate_route_properties(cls, origin: Location, route: Route, vehicle: Vehicle) -> Tuple[float, float]:
        """Method to estimate the distance and time it would take to fulfill a route from an origin"""

        complete_route = Route(
            stops=[
                      Stop(location=origin, position=0)
                  ] + [
                      Stop(location=stop.location, position=ix + 1)
                      for ix, stop in enumerate(route.stops)
                  ]
        )

        route_distance, route_time = 0, 0

        try:
            for ix in range(len(complete_route.stops) - 1):
                travelling_route = cls.get_route(
                    origin=complete_route.stops[ix].location,
                    destination=complete_route.stops[ix + 1].location
                )

                for travelling_ix in range(len(travelling_route.stops) - 1):
                    distance = haversine(
                        point1=travelling_route.stops[travelling_ix].location.coordinates,
                        point2=travelling_route.stops[travelling_ix + 1].location.coordinates
                    )
                    time = int(distance / vehicle.average_velocity)

                    route_distance += distance
                    route_time += time

        except:
            logging.exception('Exception captured in OSRMService.estimate_route_properties. Check Docker.')

        return route_distance, route_time
