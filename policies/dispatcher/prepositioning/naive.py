from typing import Iterable, List

from actors.courier import Courier
from objects.notification import Notification
from objects.order import Order
from policies.policy import Policy


class NaivePrepositioningPolicy(Policy):
    """Class that establishes how the dispatcher doesn't execute any preposition instructions"""

    def execute(self, orders: Iterable[Order], couriers: Iterable[Courier]) -> List[Notification]:
        """Implementation of the Naive Prepositioning policy"""

        return []
