import settings
from policies.dispatcher.buffering.dispatcher_buffering_policy import DispatcherBufferingPolicy


class RollingBufferingPolicy(DispatcherBufferingPolicy):
    """Class containing the policy for the dispatcher to buffer orders"""

    def execute(self) -> float:
        """Execution of the order buffering policy"""

        return settings.DISPATCHER_ROLLING_HORIZON_TIME
