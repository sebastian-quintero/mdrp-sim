from typing import Tuple

import numpy as np
import numpy.lib.recfunctions as rfn

from services.optimization_service.graph.graph import Graph
from services.optimization_service.problem.matching_problem import MatchingProblem


class GraphBuilder:
    """Class that enables the construction of a directed graph"""

    @classmethod
    def build(cls, matching_problem: MatchingProblem) -> Graph:
        """Main method to build the graph"""

        nodes = cls._build_nodes(matching_problem)
        arcs = cls._build_arcs(matching_problem)
        incidence_matrix = cls._build_incidence_matrix(nodes, arcs)

        return Graph(arcs=arcs, nodes=nodes, incidence_matrix=incidence_matrix)

    @classmethod
    def _build_nodes(cls, matching_problem: MatchingProblem) -> np.ndarray:
        """Method to build the nodes based on a matching problem"""

        courier_ids, route_ids = cls._get_entities_ids(matching_problem)

        route_demands = np.array(-1 * np.ones(route_ids.shape), dtype=[('demand', '<i8')])
        courier_demands = np.zeros(courier_ids.shape, dtype=[('demand', '<i8')])

        courier_nodes = rfn.merge_arrays([courier_ids, courier_demands], flatten=True, usemask=False)
        route_nodes = rfn.merge_arrays([route_ids, route_demands], flatten=True, usemask=False)
        supply_node = np.array([('supply', len(route_ids))], dtype=[('id', '<U100'), ('demand', '<i8')])

        return np.concatenate((courier_nodes, route_nodes, supply_node), axis=0)

    @classmethod
    def _build_arcs(cls, matching_problem: MatchingProblem) -> np.ndarray:
        """Method to build the arcs based on a matching problem"""

        courier_ids, route_ids = cls._get_entities_ids(matching_problem)
        matching_costs = np.array(matching_problem.costs, dtype=[('c', '<f8')])

        matching_arcs = rfn.merge_arrays(
            [matching_problem.matching_prospects[['i', 'j']], matching_costs],
            flatten=True,
            usemask=False
        )
        supply_couriers_arcs = cls._build_supply_entities_arcs(
            entities_ids=courier_ids,
            costs=np.zeros(len(courier_ids), dtype=[('c', '<f8')])
        )
        supply_routes_arcs = cls._build_supply_entities_arcs(
            entities_ids=route_ids,
            costs=np.zeros(len(route_ids), dtype=[('c', '<f8')])
        )

        return np.concatenate((matching_arcs, supply_couriers_arcs, supply_routes_arcs), axis=0)

    @staticmethod
    def _build_incidence_matrix(nodes: np.ndarray, arcs: np.ndarray) -> np.ndarray:
        """Method to build an incidence matrix based on nodes and arcs"""

        incidence_matrix = np.zeros((len(nodes), len(arcs)), dtype=np.intc)
        cols = np.arange(0, len(arcs))
        node_ids = nodes['id']
        i, j, c = arcs['i'], arcs['j'], arcs['c']

        nodes_sorted = np.argsort(node_ids)
        i_ix = np.searchsorted(node_ids[nodes_sorted], i)
        j_ix = np.searchsorted(node_ids[nodes_sorted], j)
        sources = nodes_sorted[i_ix]
        destinations = nodes_sorted[j_ix]

        incidence_matrix[sources, cols] = 1
        incidence_matrix[destinations, cols] = -1

        return incidence_matrix

    @staticmethod
    def _get_entities_ids(matching_problem: MatchingProblem) -> Tuple[np.ndarray, np.ndarray]:
        """Method to extract the unique entities ids from the matching problem"""

        i_dup, j_dup = matching_problem.matching_prospects['i'], matching_problem.matching_prospects['j']

        courier_ids = np.array(np.unique(i_dup), dtype=[('id', '<U100')])
        route_ids = np.array(np.unique(j_dup), dtype=[('id', '<U100')])

        return courier_ids, route_ids

    @staticmethod
    def _build_supply_entities_arcs(entities_ids: np.ndarray, costs: np.ndarray) -> np.ndarray:
        """Method to build the arcs that depart from the supply node and are directed into courier or route nodes"""

        supply_entities_combinations = np.array(
            np.meshgrid(np.array(['supply']), entities_ids['id'])
        ).T.reshape(-1, 2)
        i = np.array(supply_entities_combinations[:, 0], dtype=[('i', '<U100')])
        j = np.array(supply_entities_combinations[:, 1], dtype=[('j', '<U100')])

        return rfn.merge_arrays([i, j, costs], flatten=True, usemask=False)
