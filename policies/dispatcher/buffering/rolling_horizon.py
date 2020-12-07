from settings import settings
from policies.dispatcher.buffering.dispatcher_buffering_policy import DispatcherBufferingPolicy


class RollingBufferingPolicy(DispatcherBufferingPolicy):
    """Class containing the policy for the dispatcher to buffer orders"""

    def execute(self, env_time: int) -> bool:
        """Execution of the order buffering policy"""

        return env_time % settings.DISPATCHER_ROLLING_HORIZON_TIME == 0
