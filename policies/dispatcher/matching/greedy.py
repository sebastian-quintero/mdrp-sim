from typing import List, Iterable

from actors.courier import Courier
from objects.notification import Notification
from objects.order import Order
from policies.dispatcher.matching.dispatcher_matching_policy import DispatcherMatchingPolicy


class GreedyMatchingPolicy(DispatcherMatchingPolicy):
    """Class containing the policy for the dispatcher to execute a greedy matching"""

    def execute(self, orders: Iterable[Order], couriers: Iterable[Courier]) -> List[Notification]:
        """Implementation of the policy"""

        pass
