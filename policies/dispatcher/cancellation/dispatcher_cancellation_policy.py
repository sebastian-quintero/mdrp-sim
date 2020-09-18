from policies.policy import Policy


class DispatcherCancellationPolicy(Policy):
    """Class that establishes how the dispatcher decides to cancel an order"""

    def execute(self, courier_id: int) -> bool:
        """Implementation of the policy"""

        pass
