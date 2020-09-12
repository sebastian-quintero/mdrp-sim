import settings
from policies.dispatcher.prepositioning_timing.dispatcher_prepositioning_timing_policy import \
    DispatcherPrepositioningTimingPolicy


class FixedPrepositioningTimingPolicy(DispatcherPrepositioningTimingPolicy):
    """Class containing the policy for the dispatcher evaluating prepositioning instructions on a fixed interval"""

    def execute(self) -> bool:
        """Execution of the Fixed Prepositioning Timing Policy"""

        return settings.DISPATCHER_PREPOSITIONING_TIME
