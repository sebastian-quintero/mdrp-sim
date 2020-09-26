from policies.dispatcher.cancellation.dispatcher_cancellation_policy import DispatcherCancellationPolicy


class StaticCancellationPolicy(DispatcherCancellationPolicy):
    """Class containing the policy for the dispatcher evaluating canceling an order using a static condition"""

    def execute(self, courier_id: int) -> bool:
        """Execution of the Cancellation Policy"""

        return courier_id is None
