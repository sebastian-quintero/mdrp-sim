from typing import List, Union

from gurobipy import Constr
from pulp import LpConstraint


class ModelConstraint:
    """Class that defines how a constraint is expressed for the model"""

    def express(self, *args, **kwargs) -> List[Union[LpConstraint, Constr]]:
        """Method to express a model constraint into a standard format"""

        pass
