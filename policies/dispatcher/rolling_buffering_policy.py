import settings
from policies.policy import Policy


class RollingBufferingPolicy(Policy):
    """Class containing the policy for the dispatcher to buffer orders"""

    def execute(self) -> float:
        """Execution of the order buffering policy"""

        return settings.DISPATCHER_ROLLING_HORIZON_TIME
