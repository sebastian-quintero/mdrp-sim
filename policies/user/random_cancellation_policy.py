import random

import settings
from policies.policy import Policy


class RandomCancellationPolicy(Policy):
    """Class containing the policy that decides how a user evaluates cancelling an order using a random probability"""

    def execute(self, courier_id: int) -> bool:
        """Execution of the Cancellation Policy"""

        if courier_id is None:
            return random.random() <= settings.USER_CANCELLATION_PROBABILITY

        return False
