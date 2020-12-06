import random

from settings import settings
from policies.user.cancellation.user_cancellation_policy import UserCancellationPolicy


class RandomCancellationPolicy(UserCancellationPolicy):
    """Class containing the policy that decides how a user evaluates canceling an order using a random probability"""

    def execute(self, courier_id: int) -> bool:
        """Execution of the Cancellation Policy"""

        if courier_id is None:
            return random.random() <= settings.USER_CANCELLATION_PROBABILITY

        return False
