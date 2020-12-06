from settings import settings
from policies.dispatcher.prepositioning_evaluation.dispatcher_prepositioning_evaluation_policy import \
    DispatcherPrepositioningEvaluationPolicy


class FixedPrepositioningEvaluationPolicy(DispatcherPrepositioningEvaluationPolicy):
    """Class containing the policy for the dispatcher evaluating prepositioning instructions on a fixed interval"""

    def execute(self, env_time: int) -> bool:
        """Execution of the Fixed Prepositioning Timing Policy"""

        return env_time % settings.DISPATCHER_PREPOSITIONING_TIME == 0
