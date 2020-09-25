from typing import Optional

from objects.location import Location
from policies.courier.movement_evaluation.courier_movement_evaluation_policy import CourierMovementEvaluationPolicy


class StillMoveEvalPolicy(CourierMovementEvaluationPolicy):
    """
    Class containing the policy that decides how a courier evaluates moving about the city.
    The courier never moves, remaining still.
    """

    def execute(self, current_location: Location) -> Optional[Location]:
        """Execution of the Movement Evaluation Policy"""

        return None
