import math
from collections import defaultdict
from typing import List, Iterable, Optional, Dict

import numpy as np
from geohash import encode
from haversine import haversine

import settings
from actors.courier import Courier
from objects.notification import Notification, NotificationType
from objects.order import Order
from objects.route import Route
from objects.vehicle import Vehicle
from policies.dispatcher.matching.dispatcher_matching_policy import DispatcherMatchingPolicy
from services.optimization_service.graph.graph_builder import GraphBuilder
from services.optimization_service.model.constraints.balance_constraint import BalanceConstraint
from services.optimization_service.model.model_builder import OptimizationModelBuilder
from services.optimization_service.model.optimization_model import SOLUTION_VALUE
from services.optimization_service.problem.matching_problem import MatchingProblem
from services.optimization_service.problem.matching_problem_builder import MatchingProblemBuilder
from services.osrm_service import OSRMService
from utils.datetime_utils import time_to_sec, sec_to_time, time_diff

MODEL_BUILDER = OptimizationModelBuilder(sense='max', model_constraints=[BalanceConstraint()])


class MyopicMatchingPolicy(DispatcherMatchingPolicy):
    """Class containing the policy for the dispatcher to execute routing and matching of orders and couriers"""

    @classmethod
    def execute(cls, orders: Iterable[Order], couriers: List[Courier], env_time: int) -> List[Notification]:
        """Implementation of the policy where routes are first calculated and later assigned"""

        routes = cls._generate_routes(orders, couriers, env_time)
        prospects = cls._generate_matching_prospects(routes, couriers, env_time)

        if bool(prospects.tolist()):
            costs = cls._generate_matching_costs(routes, couriers, prospects, env_time)
            problem = MatchingProblemBuilder.build(routes, couriers, prospects, costs)
            graph = GraphBuilder.build(problem)
            model = MODEL_BUILDER.build(graph)
            solution = model.solve()
            notifications = cls._process_solution(solution, problem)

            return notifications

        else:
            return []

    @classmethod
    def _generate_routes(cls, orders: Iterable[Order], couriers: Iterable[Courier], env_time: int) -> List[Route]:
        """Method to generate routes, also known as bundles"""

        target_size = cls._calculate_target_bundle_size(orders, couriers, env_time)
        groups = cls._group_by_geohash(orders)
        routes, processes, single_ods = [], [], []

        for ods in groups.values():
            if len(ods) > 1:
                routes += cls._execute_group_routing(ods, couriers, target_size)

            else:
                single_ods += ods

        single_routes = [Route.from_order(od) for od in single_ods]

        return routes + single_routes

    @classmethod
    def _execute_group_routing(cls, orders: List[Order], couriers: Iterable[Courier], target_size: int):
        """Method to orchestrate routing orders for a group"""

        courier_routes, courier_ids, num_idle_couriers = [], [], 0
        for courier in couriers:
            if (
                    (
                            haversine(courier.location.coordinates, orders[0].pick_up_at.coordinates) <=
                            settings.DISPATCHER_PROSPECTS_MAX_DISTANCE
                    ) and
                    (
                            encode(
                                courier.location.lat,
                                courier.location.lng,
                                settings.DISPATCHER_GEOHASH_PRECISION_GROUPING
                            ) == orders[0].geohash
                    )
            ):
                if courier.state == 'idle':
                    num_idle_couriers += 1

                elif courier.state == 'picking_up':
                    courier_routes.append(courier.active_route)
                    courier_ids.append(courier.courier_id)

        routes = cls._generate_group_routes(
            orders=orders,
            target_size=target_size,
            courier_routes=courier_routes,
            num_idle_couriers=num_idle_couriers,
            max_orders=settings.DISPATCHER_PROSPECTS_MAX_ORDERS,
            courier_ids=courier_ids
        )

        return routes

    @staticmethod
    def _generate_group_routes(
            orders: Iterable[Order],
            target_size: int,
            courier_routes: List[Route],
            num_idle_couriers: int,
            max_orders: Optional[int] = settings.DISPATCHER_PROSPECTS_MAX_ORDERS,
            courier_ids: List[int] = None,
    ) -> List[Route]:
        """Method to generate routes for a specific group using a heuristic"""

        sorted_orders = sorted(orders, key=lambda o: o.ready_time)
        number_of_routes = max(num_idle_couriers, math.ceil(len(sorted_orders) / target_size))
        route_size = min(target_size, max_orders)

        initial_routes = [route for route in courier_routes]
        initial_orders = []
        for route in initial_routes:
            route.add_stops(route_size)
            initial_orders.append([order_id for order_id in route.orders.keys()])

        routes = initial_routes + [Route(num_stops=route_size + 1) for _ in range(number_of_routes)]
        single_routes = []

        for order in sorted_orders:
            route_ix_position_time = []

            for route_ix, route in enumerate(routes):
                if len(route.orders) < route_size:
                    if not bool(route.orders):
                        cost = route.calculate_time_update(
                            destination=order.drop_off_at,
                            origin=order.pick_up_at,
                            service_time=order.drop_off_service_time
                        )[Vehicle.MOTORCYCLE]
                        route_ix_position_time.append((route_ix, 1, cost))

                    else:
                        for position in range(1, route.num_stops):
                            origin = route.stops[position - 1]
                            destination = route.stops[position]

                            if bool(origin.orders) and not bool(destination.orders):
                                cost = route.calculate_time_update(
                                    destination=order.drop_off_at,
                                    origin=origin.location,
                                    service_time=order.drop_off_service_time
                                )[Vehicle.MOTORCYCLE]
                                route_ix_position_time.append((route_ix, position, cost))

            if bool(route_ix_position_time):
                sorted_time = sorted(route_ix_position_time, key=lambda t: t[2])
                selected_route, selected_position, _ = sorted_time[0]
                routes[selected_route].add_order(order=order, route_position=selected_position)

            else:
                single_routes.append(Route.from_order(order))

        group_routes = []
        for ix, route in enumerate(routes):
            route.update_stops()

            if bool(initial_routes) and ix < len(initial_routes):
                route.update(processed_order_ids=initial_orders[ix])

                if bool(route.orders):
                    route.initial_prospect = courier_ids[ix]

            if bool(route.orders):
                group_routes.append(route)

        return group_routes + single_routes

    @classmethod
    def _generate_matching_prospects(cls, routes: List[Route], couriers: List[Courier], env_time: int) -> np.ndarray:
        """Method to generate the possible matching prospects"""

        return np.array(
            [
                (courier_ix, route_ix)
                for route_ix, route in enumerate(routes)
                for courier_ix, courier in enumerate(couriers)
                if cls._is_prospect(route, courier, env_time)
            ],
            dtype=np.int64
        )

    @staticmethod
    def _calculate_target_bundle_size(orders: Iterable[Order], couriers: Iterable[Courier], env_time: int) -> int:
        """Method to calculate the target bundle size based on system intensity"""

        num_orders = len([
            order
            for order in orders
            if time_to_sec(order.ready_time) <= env_time + settings.DISPATCHER_MYOPIC_READY_TIME_SLACK
        ])
        num_couriers = len([courier for courier in couriers if courier.state == 'idle'])

        return max(math.ceil(num_orders / num_couriers), 1) if num_couriers > 0 else 1

    @staticmethod
    def _group_by_geohash(orders: Iterable[Order]) -> Dict[str, List[Order]]:
        """Method to group orders by geohashes, an alternate way to group into stores"""

        groups = defaultdict(list)
        for order in orders:
            groups[order.geohash] += [order]

        return groups

    @staticmethod
    def _is_prospect(route: Route, courier: Courier, env_time: int) -> bool:
        """Method to establish if a courier and route are matching prospects"""

        _, time_to_first_stop = OSRMService.estimate_travelling_properties(
            origin=courier.location,
            destination=route.stops[0].location,
            vehicle=courier.vehicle
        )
        stops_time_offset = sum(
            abs(time_diff(
                time_1=sec_to_time(int(env_time + time_to_first_stop + stop.arrive_at[courier.vehicle])),
                time_2=stop.calculate_latest_expected_time()
            ))
            for stop in route.stops
        )
        distance_condition = (
                haversine(courier.location.coordinates, route.stops[0].location.coordinates) <=
                settings.DISPATCHER_PROSPECTS_MAX_DISTANCE
        )
        stop_offset_condition = (
            stops_time_offset <= settings.DISPATCHER_PROSPECTS_MAX_STOP_OFFSET * route.num_stops
            if route.time_since_ready(env_time) <= settings.DISPATCHER_PROSPECTS_MAX_READY_TIME
            else True
        )
        courier_state_condition = (
                courier.state == 'idle' or
                (courier.state == 'picking_up' and route.initial_prospect == courier.courier_id)
        )

        return distance_condition and stop_offset_condition and courier_state_condition

    @staticmethod
    def _generate_matching_costs(
            routes: List[Route],
            couriers: List[Courier],
            prospects: np.ndarray,
            env_time: int
    ) -> np.ndarray:
        """Method to estimate the cost of a possible match, based on the prospects"""

        costs = np.zeros(len(prospects))

        for ix, (courier_ix, route_ix) in enumerate(prospects):
            route, courier = routes[route_ix], couriers[courier_ix]
            distance_to_first_stop, time_to_first_stop = OSRMService.estimate_travelling_properties(
                origin=courier.location,
                destination=route.stops[0].location,
                vehicle=courier.vehicle
            )
            costs[ix] = (
                    len(route.orders) / (time_to_first_stop + route.time[courier.vehicle]) -
                    time_diff(
                        time_1=sec_to_time(
                            int(env_time + time_to_first_stop + route.stops[0].arrive_at[courier.vehicle])
                        ),
                        time_2=max(order.ready_time for order in route.stops[0].orders.values())
                    ) * settings.DISPATCHER_DELAY_PENALTY
            )

        return costs

    @staticmethod
    def _process_solution(solution: np.ndarray, matching_problem: MatchingProblem) -> List[Notification]:
        """Method to parse the optimizer's solution into the notifications"""

        matching_solution = solution[0:len(matching_problem.prospects)]
        matched_prospects_ix = np.where(matching_solution >= SOLUTION_VALUE)
        matched_prospects = matching_problem.prospects[matched_prospects_ix]

        notifications = [None] * len(matched_prospects)
        for ix, (courier_ix, route_ix) in enumerate(matched_prospects):
            courier, route = matching_problem.couriers[courier_ix], matching_problem.routes[route_ix]
            instruction = route.stops[1:] if courier.state == 'picking_up' else route

            notifications[ix] = Notification(
                courier=courier,
                instruction=instruction,
                type=NotificationType.PICK_UP_DROP_OFF
            )

        return notifications
