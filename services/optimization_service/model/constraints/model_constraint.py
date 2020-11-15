from typing import List

from pulp import LpConstraint


class ModelConstraint:
    """Class that defines how a constraint is expressed for the model"""

    def express(self, *args, **kwargs) -> List[LpConstraint]:
        """Method to express a model constraint into a standard format"""

        pass
