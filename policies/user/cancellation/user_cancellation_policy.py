from policies.policy import Policy


class UserCancellationPolicy(Policy):
    """Class that establishes how the user decides to cancel an order"""

    def execute(self, courier_id: int) -> bool:
        """Implementation of the policy"""

        pass
