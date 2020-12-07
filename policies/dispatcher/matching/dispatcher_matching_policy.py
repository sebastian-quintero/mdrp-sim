from typing import List, Iterable, Tuple

from actors.courier import Courier
from objects.matching_metric import MatchingMetric
from objects.notification import Notification
from objects.order import Order
from policies.policy import Policy


class DispatcherMatchingPolicy(Policy):
    """Class that establishes how the dispatcher executes the routing and matching of orders and couriers"""

    def execute(
            self,
            orders: Iterable[Order],
            couriers: Iterable[Courier],
            env_time: int
    ) -> Tuple[List[Notification], MatchingMetric]:
        """Implementation of the policy"""

        pass
