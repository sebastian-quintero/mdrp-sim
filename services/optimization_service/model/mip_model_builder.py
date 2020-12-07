from typing import Union

import numpy as np
from pulp import LpVariable, LpBinary, LpProblem
from gurobipy import Model, Var, GRB

from services.optimization_service.model.model_builder import OptimizationModelBuilder
from services.optimization_service.problem.matching_problem import MatchingProblem


class MIPOptimizationModelBuilder(OptimizationModelBuilder):
    """Class that enables the construction of an optimization model for matching"""

    def _build_variables(self, problem: MatchingProblem, engine_model: Union[LpProblem, Model]) -> np.ndarray:
        """Method to build the model decision variables, which are integer variables"""

        i, j = problem.matching_prospects['i'], problem.matching_prospects['j']
        couriers_routes_vars = np.vectorize(self._build_int_bool_var, otypes=[np.object])(i, j, engine_model)

        unique_routes = np.unique(j)
        supply_courier = np.array(['supply'])
        supply_routes_combinations = np.array(
            np.array(np.meshgrid(supply_courier, unique_routes)).T.reshape(len(supply_courier) * len(unique_routes), 2),
            dtype='<U100'
        )
        supply_routes_vars = np.vectorize(self._build_int_bool_var, otypes=[np.object])(
            supply_routes_combinations[:, 0],
            supply_routes_combinations[:, 1],
            engine_model
        )

        return np.concatenate((couriers_routes_vars, supply_routes_vars), axis=0)

    @staticmethod
    def _build_objective(problem: MatchingProblem, variable_set: np.ndarray) -> np.ndarray:
        """Method to build the model's linear objective"""

        couriers_routes_costs = problem.costs
        unique_routes = np.unique(problem.matching_prospects['j'])
        supply_routes_costs = np.zeros(len(unique_routes))
        costs = np.concatenate((couriers_routes_costs, supply_routes_costs), axis=0)

        return np.dot(variable_set, costs)

    def _build_int_bool_var(
            self,
            i: np.ndarray,
            j: np.ndarray,
            engine_model: Union[LpProblem, Model]
    ) -> Union[LpVariable, Var]:
        """Method to build an integer boolean variable"""

        if self._optimizer == 'pulp':
            var = LpVariable(f'x({i}, {j})', 0, 1, LpBinary)
        else:
            var = engine_model.addVar(lb=0, ub=1, vtype=GRB.BINARY, name=f'x({i}, {j})')

        return var
