from typing import List

from actors.courier import Courier
from models.notification import Notification
from models.order import Order
from policies.policy import Policy


class MyopicMatchingPolicy(Policy):
    """Class containing the policy for the dispatcher to execute a myopic matching"""

    def execute(self, orders: List[Order], couriers: List[Courier]) -> List[Notification]:
        pass
