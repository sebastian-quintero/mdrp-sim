from typing import Generator, Any

from simpy import Environment

import settings
from policies.courier.acceptance.courier_acceptance_policy import CourierAcceptancePolicy


class AbsoluteAcceptancePolicy(CourierAcceptancePolicy):
    """
    Class containing the policy that decides how a courier evaluates accepting or rejecting a notification.
    The courier accepts every notification
    """

    def execute(self, acceptance_rate: float, env: Environment) -> Generator[Any, Any, bool]:
        """Execution of the Acceptance Policy"""

        yield env.timeout(delay=settings.COURIER_WAIT_TO_ACCEPT)

        return True
