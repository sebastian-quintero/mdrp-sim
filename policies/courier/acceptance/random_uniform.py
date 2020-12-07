import random
from typing import Generator, Any

from simpy import Environment

from settings import settings
from policies.courier.acceptance.courier_acceptance_policy import CourierAcceptancePolicy


class UniformAcceptancePolicy(CourierAcceptancePolicy):
    """
    Class containing the policy that decides how a courier evaluates accepting or rejecting a notification.
    It uses a Uniform Distribution to obtain the acceptance rate and a weighted probability to decide.
    """

    def execute(self, acceptance_rate: float, env: Environment) -> Generator[Any, Any, bool]:
        """Execution of the Acceptance Policy"""

        yield env.timeout(delay=settings.COURIER_WAIT_TO_ACCEPT)

        return random.choices(self.ACCEPTANCE_CHOICES, weights=(acceptance_rate, 1 - acceptance_rate))[0]
