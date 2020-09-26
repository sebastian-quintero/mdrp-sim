from typing import List

import numpy as np
from haversine import haversine

import settings
from actors.courier import Courier
from objects.notification import Notification, NotificationType
from objects.order import Order
from objects.route import Route
from objects.stop import Stop, StopType
from policies.dispatcher.matching.dispatcher_matching_policy import DispatcherMatchingPolicy
from services.osrm_service import OSRMService


class GreedyMatchingPolicy(DispatcherMatchingPolicy):
    """Class containing the policy for the dispatcher to execute a greedy matching"""

    def execute(self, orders: List[Order], couriers: List[Courier]) -> List[Notification]:
        """Implementation of the policy"""

        idle_couriers = [courier for courier in couriers if courier.state == 'idle' and courier.active_route is None]
        prospects = self._get_prospects(orders, idle_couriers)
        estimations = self._get_estimations(orders, idle_couriers, prospects)

        notifications, notified_couriers = [], np.array([])
        if bool(prospects.tolist()) and bool(estimations.tolist()) and bool(orders) and bool(idle_couriers):
            for order_ix, order in enumerate(orders):
                mask = np.where(np.logical_and(
                    prospects[:, 0] == order_ix,
                    np.logical_not(np.isin(prospects[:, 1], notified_couriers))
                ))

                if bool(mask[0].tolist()):
                    order_prospects = prospects[mask]
                    order_estimations = estimations[mask]
                    min_time = order_estimations['time'].min()
                    selection_mask = np.where(order_estimations['time'] == min_time)
                    selected_prospect = order_prospects[selection_mask][0]

                    notifications.append(
                        Notification(
                            courier=couriers[selected_prospect[1]],
                            type=NotificationType.PICK_UP_DROP_OFF,
                            instruction=Route(
                                orders={order.order_id: order},
                                stops=[
                                    Stop(
                                        location=order.pick_up_at,
                                        orders={order.order_id: order},
                                        position=0,
                                        type=StopType.PICK_UP,
                                        visited=False
                                    ),
                                    Stop(
                                        location=order.drop_off_at,
                                        orders={order.order_id: order},
                                        position=1,
                                        type=StopType.DROP_OFF,
                                        visited=False
                                    )
                                ]
                            )
                        )
                    )
                    notified_couriers = np.append(notified_couriers, selected_prospect[1])

        return notifications

    @staticmethod
    def _get_prospects(orders: List[Order], couriers: List[Courier]) -> np.ndarray:
        """Method to obtain the matching prospects between orders and couriers"""

        prospects = []
        for order_ix, order in enumerate(orders):
            for courier_ix, courier in enumerate(couriers):
                distance_to_pick_up = haversine(courier.location.coordinates, order.pick_up_at.coordinates)
                courier_orders = len(courier.active_route.orders) if courier.active_route is not None else 0
                if (
                        distance_to_pick_up <= settings.DISPATCHER_PROSPECTS_MAX_DISTANCE and
                        courier_orders + 1 <= settings.DISPATCHER_PROSPECTS_MAX_ORDERS
                ):
                    prospects.append((order_ix, courier_ix))

        return np.array(prospects)

    @staticmethod
    def _get_estimations(orders: List[Order], couriers: List[Courier], prospects: np.ndarray) -> np.ndarray:
        """Method to obtain the time estimations from the matching prospects"""

        estimations = [None] * len(prospects)
        for ix, (order_ix, courier_ix) in enumerate(prospects):
            order, courier = orders[order_ix], couriers[courier_ix]
            route = Route(
                orders={order.order_id: order},
                stops=[
                    Stop(
                        location=order.pick_up_at,
                        orders={order.order_id: order},
                        position=0,
                        type=StopType.PICK_UP,
                        visited=False
                    ),
                    Stop(
                        location=order.drop_off_at,
                        orders={order.order_id: order},
                        position=1,
                        type=StopType.DROP_OFF,
                        visited=False
                    )
                ]
            )
            distance, time = OSRMService.estimate_route_properties(
                origin=courier.location,
                route=route,
                vehicle=courier.vehicle
            )
            time += (order.pick_up_service_time + order.drop_off_service_time)
            estimations[ix] = (distance, time)

        return np.array(estimations, dtype=[('distance', np.float64), ('time', np.float64)])
