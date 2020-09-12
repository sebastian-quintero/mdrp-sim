from typing import Generator, Any

from simpy import Environment

from policies.policy import Policy


class CourierAcceptancePolicy(Policy):
    """Class that establishes how a courier accepts a notification"""

    ACCEPTANCE_CHOICES = [True, False]

    def execute(self, acceptance_rate: float, env: Environment) -> Generator[Any, Any, bool]:
        """Implementation of the policy"""

        pass
