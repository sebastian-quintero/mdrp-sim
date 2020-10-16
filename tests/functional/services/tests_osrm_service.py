import unittest
from unittest.mock import patch

from objects.location import Location
from objects.route import Route
from objects.stop import Stop
from objects.vehicle import Vehicle
from services.osrm_service import OSRMService
from tests.test_utils import mocked_get_route


class TestsOSRMService(unittest.TestCase):
    """Tests for the OSRM service class"""

    @patch('services.osrm_service.OSRMService.get_route', side_effect=mocked_get_route)
    def test_get_route(self, osrm):
        """Test to verify the route construction works correctly"""

        # Defines an origin and a destination
        origin = Location(4.678622, -74.055694)
        destination = Location(4.690207, -74.044235)

        # Obtains the route and asserts it is equal to the mocked value
        route = OSRMService.get_route(origin, destination)
        self.assertEqual(
            route.stops,
            Route(
                stops=[
                    Stop(position=0, location=origin),
                    Stop(position=1, location=destination)
                ]
            ).stops
        )

    @patch('services.osrm_service.OSRMService.get_route', side_effect=mocked_get_route)
    def test_estimate_route_properties(self, osrm):
        """Test to verify the route estimation works correctly"""

        # Defines an origin and a route that must be fulfilled
        origin = Location(4.678622, -74.055694)
        route = Route(
            stops=[
                Stop(position=0, location=Location(4.690207, -74.044235)),
                Stop(position=1, location=Location(4.709022, -74.035102))
            ]
        )

        # Obtains the route's distance and time and asserts expected values
        distance, time = OSRMService.estimate_route_properties(origin=origin, route=route, vehicle=Vehicle.CAR)
        self.assertEqual(int(distance), 4)
        self.assertEqual(time, 594)
