from typing import Iterable, List, Tuple

from actors.courier import Courier
from objects.location import Location
from objects.matching_metric import MatchingMetric
from objects.notification import Notification
from objects.order import Order
from objects.route import Route
from objects.stop import Stop
from policies.dispatcher.matching.dispatcher_matching_policy import DispatcherMatchingPolicy


class DummyMatchingPolicy(DispatcherMatchingPolicy):
    """Class to produce dummy notifications for testing purposes"""

    def execute(
            self,
            orders: Iterable[Order],
            couriers: Iterable[Courier],
            env_time: int
    ) -> Tuple[List[Notification], MatchingMetric]:
        """Implementation of the dummy policy"""

        return [], None


def mocked_get_route(origin: Location, destination: Location) -> Route:
    """Method that mocks how a route is obtained going from an origin to a destination"""

    return Route(stops=[Stop(location=origin, position=0), Stop(location=destination, position=1)])
