from typing import Optional

from objects.location import Location
from policies.policy import Policy


class CourierMovementEvaluationPolicy(Policy):
    """Class that establishes how a courier decides to change his / her location and the corresponding destination"""

    def execute(self, current_location: Location) -> Optional[Location]:
        """Implementation of the policy"""

        pass
