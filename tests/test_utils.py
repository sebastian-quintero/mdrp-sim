from typing import Iterable, List

from actors.courier import Courier
from objects.location import Location
from objects.notification import Notification
from objects.order import Order
from objects.route import Route
from objects.stop import Stop
from policies.dispatcher.matching.dispatcher_matching_policy import DispatcherMatchingPolicy


class DummyMatchingPolicy(DispatcherMatchingPolicy):
    """Class to produce dummy notifications for testing purposes"""

    def execute(self, orders: Iterable[Order], couriers: Iterable[Courier]) -> List[Notification]:
        """Implementation of the dummy policy"""

        return []


def mocked_get_route(origin: Location, destination: Location) -> Route:
    """Method that mocks how a route is obtained going from an origin to a destination"""

    return Route(stops=[Stop(location=origin, position=0), Stop(location=destination, position=1)])
