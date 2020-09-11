import random

from simpy import Environment

import settings
from policies.policy import Policy
from utils.datetime_utils import min_to_sec


class UniformAcceptancePolicy(Policy):
    """
    Class containing the policy that decides how a courier evaluates accepting or rejecting a notification.
    It uses a Uniform Distribution to obtain the acceptance rate and a weighted probability to decide.
    """

    ACCEPTANCE_CHOICES = [True, False]

    def execute(self, acceptance_rate: float, env: Environment) -> bool:
        """Execution of the Acceptance Policy"""

        yield env.timeout(delay=settings.COURIER_WAIT_TO_ACCEPT)

        return random.choices(self.ACCEPTANCE_CHOICES, weights=(acceptance_rate, 1 - acceptance_rate))[0]
