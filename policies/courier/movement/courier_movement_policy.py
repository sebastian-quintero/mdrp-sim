from simpy import Environment

from objects.location import Location
from policies.policy import Policy


class CourierMovementPolicy(Policy):
    """Class that establishes how a courier moves from an origin to a destination"""

    def execute(self, origin: Location, destination: Location, env: Environment, courier):
        """Implementation of the policy"""

        pass
