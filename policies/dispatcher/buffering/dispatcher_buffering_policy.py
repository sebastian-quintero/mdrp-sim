from policies.policy import Policy


class DispatcherBufferingPolicy(Policy):
    """Class that establishes how the dispatcher buffers orders before executing a dispatching event"""

    def execute(self, env_time: int) -> bool:
        """Implementation of the policy"""

        pass
