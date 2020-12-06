import random
import unittest
from datetime import time
from unittest.mock import patch

from actors.courier import Courier
from objects.location import Location
from objects.order import Order
from objects.route import Route
from objects.stop import Stop, StopType
from policies.dispatcher.matching.myopic import MyopicMatchingPolicy
from services.optimization_service.graph.graph_builder import GraphBuilder
from services.optimization_service.model.constraints.balance_constraint import BalanceConstraint
from services.optimization_service.model.constraints.courier_assignment_constraint import CourierAssignmentConstraint
from services.optimization_service.model.constraints.route_assignment_constraint import RouteAssignmentConstraint
from services.optimization_service.model.graph_model_builder import GraphOptimizationModelBuilder
from services.optimization_service.model.mip_model_builder import MIPOptimizationModelBuilder
from services.optimization_service.problem.matching_problem_builder import MatchingProblemBuilder
from tests.test_utils import mocked_get_route
from utils.datetime_utils import time_to_sec, hour_to_sec, min_to_sec


class TestsMyopicMatchingPolicy(unittest.TestCase):
    """Tests for the greedy matching policy class"""

    @patch('settings.settings.DISPATCHER_GEOHASH_PRECISION_GROUPING', 7)
    def test_group_by_geohash(self):
        """Test to verify how the target bundle size is calculated"""

        # Create 3 orders to be grouped into 2 geohashes
        order_1 = Order(order_id=1, pick_up_at=Location(lat=4.678417, lng=-74.054725))
        order_2 = Order(order_id=2, pick_up_at=Location(lat=4.678417, lng=-74.054725))
        order_3 = Order(order_id=3, pick_up_at=Location(lat=4.717045, lng=-74.036359))

        groups = MyopicMatchingPolicy._group_by_geohash(orders=[order_1, order_2, order_3])

        # Asserts only 2 groups are created from 3 groups
        self.assertEqual(len(groups), 2)
        self.assertIn(order_1, groups.get('d2g6dgd'))
        self.assertIn(order_2, groups.get('d2g6dgd'))
        self.assertIn(order_3, groups.get('d2g6g68'))

    @patch('settings.settings.DISPATCHER_MYOPIC_READY_TIME_SLACK', 0)
    def test_calculate_target_bundle_size(self):
        """"Test to verify the target bundle size is correctly calculated"""

        # Constants
        on_time = time(15, 0, 0)
        off_time = time(16, 0, 0)
        ready_time = time(15, 0, 0)
        env_time = time_to_sec(time(15, 20, 0))

        # Test case 1: create more couriers than orders
        courier_1 = Courier(courier_id=1, on_time=on_time, off_time=off_time, condition='idle')
        courier_2 = Courier(courier_id=2, on_time=on_time, off_time=off_time, condition='idle')
        courier_3 = Courier(courier_id=3, on_time=on_time, off_time=off_time, condition='idle')

        order_1 = Order(order_id=1, ready_time=ready_time)

        target_size = MyopicMatchingPolicy._calculate_target_bundle_size(
            orders=[order_1],
            couriers=[courier_1, courier_2, courier_3],
            env_time=env_time
        )

        self.assertEqual(target_size, 1)

        # Test case 2: create more orders than couriers
        courier_1 = Courier(courier_id=1, on_time=on_time, off_time=off_time, condition='idle')

        order_1 = Order(order_id=1, ready_time=ready_time)
        order_2 = Order(order_id=2, ready_time=ready_time)
        order_3 = Order(order_id=3, ready_time=ready_time)

        target_size = MyopicMatchingPolicy._calculate_target_bundle_size(
            orders=[order_1, order_2, order_3],
            couriers=[courier_1],
            env_time=env_time
        )

        self.assertEqual(target_size, 3)

        # Test case 3: create more orders than couriers but couriers are idle
        courier_1 = Courier(courier_id=1, on_time=on_time, off_time=off_time, condition='moving')

        order_2 = Order(order_id=2, ready_time=ready_time)
        order_3 = Order(order_id=3, ready_time=ready_time)

        target_size = MyopicMatchingPolicy._calculate_target_bundle_size(
            orders=[order_1, order_2, order_3],
            couriers=[courier_1],
            env_time=env_time
        )

        self.assertEqual(target_size, 1)

    @patch('services.osrm_service.OSRMService.get_route', side_effect=mocked_get_route)
    @patch('settings.settings.DISPATCHER_PROSPECTS_MAX_ORDERS', 1)
    def test_generate_group_routes(self, osrm):
        """Test to verify how the heuristic to generate routes work"""

        # Constants
        order_1 = Order(
            order_id=1,
            pick_up_at=Location(lat=4.678417, lng=-74.054725),
            drop_off_at=Location(lat=4.717045, lng=-74.036359),
            ready_time=time(12, 13, 0)
        )
        order_2 = Order(
            order_id=2,
            pick_up_at=Location(lat=4.678417, lng=-74.054725),
            drop_off_at=Location(lat=4.723418, lng=-74.037067),
            ready_time=time(12, 10, 0)
        )
        order_3 = Order(
            order_id=3,
            pick_up_at=Location(lat=4.678417, lng=-74.054725),
            drop_off_at=Location(lat=4.723418, lng=-74.037067),
            ready_time=time(12, 30, 0)
        )
        old_order = Order(
            order_id=9898,
            pick_up_at=Location(lat=4.678417, lng=-74.054725),
            drop_off_at=Location(lat=4.727278, lng=-74.039299),
            ready_time=time(11, 50, 0)
        )
        target_size = 2

        # Case 1: orders routed without initial routes and courier slack
        num_idle_couriers = 4
        routes = MyopicMatchingPolicy._generate_group_routes(
            orders=[order_1, order_2],
            target_size=target_size,
            courier_routes=[],
            num_idle_couriers=num_idle_couriers
        )
        self.assertTrue(routes)
        self.assertEqual(len(routes), 2)

        routed_orders = [o for route in routes for o in route.orders.keys()]
        for order in [order_1, order_2]:
            self.assertIn(order.order_id, routed_orders)

        # Case 2: orders routed without initial routes and no courier slack
        num_idle_couriers = 0
        routes = MyopicMatchingPolicy._generate_group_routes(
            orders=[order_1, order_2],
            target_size=target_size,
            courier_routes=[],
            num_idle_couriers=num_idle_couriers
        )
        self.assertTrue(routes)
        self.assertEqual(len(routes), 1)

        routed_orders = [o for route in routes for o in route.orders.keys()]
        for order in [order_1, order_2]:
            self.assertIn(order.order_id, routed_orders)

        # Case 3: orders routed with initial routes and courier slack
        num_idle_couriers = 1
        initial_route = Route(
            orders={old_order.order_id: old_order},
            stops=[
                Stop(
                    orders={old_order.order_id: old_order},
                    location=old_order.pick_up_at,
                    position=0,
                    type=StopType.PICK_UP
                ),
                Stop(
                    orders={old_order.order_id: old_order},
                    location=old_order.drop_off_at,
                    position=1,
                    type=StopType.DROP_OFF
                )
            ]
        )
        routes = MyopicMatchingPolicy._generate_group_routes(
            orders=[order_1, order_2],
            target_size=2,
            courier_routes=[initial_route],
            num_idle_couriers=num_idle_couriers,
            max_orders=3,
            courier_ids=[3]
        )
        self.assertTrue(routes)
        self.assertEqual(len(routes), 1)

        routed_orders = [o for route in routes for o in route.orders.keys()]
        for order in [order_1, order_2]:
            self.assertIn(order.order_id, routed_orders)

        self.assertIsNone(routes[0].initial_prospect)

        # Case 4: orders routed without initial routes and insufficient couriers
        num_idle_couriers = 0
        target_size = 5
        routes = MyopicMatchingPolicy._generate_group_routes(
            orders=[order_1, order_2, order_3],
            target_size=target_size,
            courier_routes=[],
            num_idle_couriers=num_idle_couriers
        )
        self.assertTrue(routes)
        self.assertEqual(len(routes), 1)

        routed_orders = [o for route in routes for o in route.orders.keys()]
        for order in [order_1, order_2, order_3]:
            self.assertIn(order.order_id, routed_orders)

    @patch('services.osrm_service.OSRMService.get_route', side_effect=mocked_get_route)
    @patch('settings.settings.DISPATCHER_MYOPIC_READY_TIME_SLACK', min_to_sec(20))
    def test_generate_routes_idle_couriers(self, osrm):
        """Test to verify how routes are created from test orders and couriers"""

        # Constants
        env_time = hour_to_sec(12) + min_to_sec(20)
        on_time = time(8, 0, 0)
        off_time = time(16, 0, 0)

        # Orders
        order_1 = Order(
            order_id=1,
            pick_up_at=Location(lat=4.678759, lng=-74.055729),
            drop_off_at=Location(lat=4.681694, lng=-74.044811),
            ready_time=time(12, 30, 0),
            expected_drop_off_time=time(12, 40, 0),
            pick_up_service_time=0,
            drop_off_service_time=0
        )
        order_2 = Order(
            order_id=2,
            pick_up_at=Location(lat=4.678759, lng=-74.055729),
            drop_off_at=Location(lat=4.695001, lng=-74.040737),
            ready_time=time(12, 32, 0),
            expected_drop_off_time=time(12, 42, 0),
            pick_up_service_time=0,
            drop_off_service_time=0
        )
        order_3 = Order(
            order_id=3,
            pick_up_at=Location(lat=4.678759, lng=-74.055729),
            drop_off_at=Location(lat=4.668742, lng=-74.056684),
            ready_time=time(12, 33, 0),
            expected_drop_off_time=time(12, 43, 0),
            pick_up_service_time=0,
            drop_off_service_time=0
        )
        order_4 = Order(
            order_id=4,
            pick_up_at=Location(lat=4.678759, lng=-74.055729),
            drop_off_at=Location(lat=4.661441, lng=-74.056955),
            ready_time=time(12, 34, 0),
            expected_drop_off_time=time(12, 44, 0),
            pick_up_service_time=0,
            drop_off_service_time=0
        )

        # Couriers
        courier_1 = Courier(
            courier_id=1,
            on_time=on_time,
            off_time=off_time,
            condition='idle',
            location=Location(lat=4.676854, lng=-74.057498)
        )
        courier_2 = Courier(
            courier_id=2,
            on_time=on_time,
            off_time=off_time,
            condition='idle',
            location=Location(lat=4.679408, lng=-74.052524)
        )

        # Get routes and assert expected behavior
        policy = MyopicMatchingPolicy(
            assignment_updates=True,
            prospects=True,
            notification_filtering=False,
            mip_matcher=False
        )
        routes = policy._generate_routes(
            orders=[order_1, order_2, order_3, order_4],
            couriers=[courier_1, courier_2],
            env_time=env_time
        )
        self.assertTrue(routes)
        self.assertEqual(len(routes), 2)
        self.assertIn(order_1.order_id, routes[0].orders.keys())
        self.assertIn(order_3.order_id, routes[0].orders.keys())
        self.assertIn(order_2.order_id, routes[1].orders.keys())
        self.assertIn(order_4.order_id, routes[1].orders.keys())

    @patch('services.osrm_service.OSRMService.get_route', side_effect=mocked_get_route)
    @patch('settings.settings.DISPATCHER_MYOPIC_READY_TIME_SLACK', min_to_sec(20))
    def test_generate_routes_picking_up_couriers(self, osrm):
        """Test to verify how routes are created from test orders and couriers"""

        # Constants
        env_time = hour_to_sec(12) + min_to_sec(20)
        on_time = time(8, 0, 0)
        off_time = time(16, 0, 0)
        random.seed(56)

        # Orders
        order_1 = Order(
            order_id=1,
            pick_up_at=Location(lat=4.678759, lng=-74.055729),
            drop_off_at=Location(lat=4.681694, lng=-74.044811),
            ready_time=time(12, 30, 0),
            expected_drop_off_time=time(12, 40, 0),
            pick_up_service_time=0,
            drop_off_service_time=0
        )
        order_2 = Order(
            order_id=2,
            pick_up_at=Location(lat=4.678759, lng=-74.055729),
            drop_off_at=Location(lat=4.695001, lng=-74.040737),
            ready_time=time(12, 32, 0),
            expected_drop_off_time=time(12, 42, 0),
            pick_up_service_time=0,
            drop_off_service_time=0
        )
        order_3 = Order(
            order_id=3,
            pick_up_at=Location(lat=4.678759, lng=-74.055729),
            drop_off_at=Location(lat=4.668742, lng=-74.056684),
            ready_time=time(12, 33, 0),
            expected_drop_off_time=time(12, 43, 0),
            pick_up_service_time=0,
            drop_off_service_time=0
        )

        # Couriers
        courier_3 = Courier(
            courier_id=3,
            on_time=on_time,
            off_time=off_time,
            condition='picking_up',
            location=order_3.pick_up_at,
            active_route=Route(
                orders={order_3.order_id: order_3},
                stops=[
                    Stop(
                        location=order_3.pick_up_at,
                        orders={order_3.order_id: order_3},
                        position=0,
                        type=StopType.PICK_UP
                    ),
                    Stop(
                        location=order_3.drop_off_at,
                        orders={order_3.order_id: order_3},
                        position=1,
                        type=StopType.DROP_OFF
                    )
                ]
            ),
            active_stop=Stop(
                location=order_3.pick_up_at,
                orders={order_3.order_id: order_3},
                position=0,
                type=StopType.PICK_UP
            )
        )

        # Get routes and assert expected behavior
        policy = MyopicMatchingPolicy(
            assignment_updates=True,
            prospects=True,
            notification_filtering=False,
            mip_matcher=False
        )
        routes = policy._generate_routes(
            orders=[order_1, order_2],
            couriers=[courier_3],
            env_time=env_time
        )
        self.assertTrue(routes)
        self.assertEqual(len(routes), 2)
        self.assertIsNone(routes[0].initial_prospect)
        self.assertIsNone(routes[1].initial_prospect)

    @patch('services.osrm_service.OSRMService.get_route', side_effect=mocked_get_route)
    @patch('settings.settings.DISPATCHER_PROSPECTS_MAX_STOP_OFFSET', min_to_sec(15))
    def test_generate_matching_prospects_all(self, osrm):
        """Test to verify how prospects are created"""

        # Constants
        env_time = hour_to_sec(12) + min_to_sec(20)
        on_time = time(8, 0, 0)
        off_time = time(16, 0, 0)

        # Orders
        order_1 = Order(
            order_id=1,
            pick_up_at=Location(lat=4.678759, lng=-74.055729),
            drop_off_at=Location(lat=4.681694, lng=-74.044811),
            ready_time=time(12, 30, 0),
            expected_drop_off_time=time(12, 40, 0),
            pick_up_service_time=0,
            drop_off_service_time=0
        )
        order_2 = Order(
            order_id=2,
            pick_up_at=Location(lat=4.678759, lng=-74.055729),
            drop_off_at=Location(lat=4.695001, lng=-74.040737),
            ready_time=time(12, 32, 0),
            expected_drop_off_time=time(12, 42, 0),
            pick_up_service_time=0,
            drop_off_service_time=0
        )
        order_3 = Order(
            order_id=3,
            pick_up_at=Location(lat=4.678759, lng=-74.055729),
            drop_off_at=Location(lat=4.668742, lng=-74.056684),
            ready_time=time(12, 33, 0),
            expected_drop_off_time=time(12, 43, 0),
            pick_up_service_time=0,
            drop_off_service_time=0
        )
        order_4 = Order(
            order_id=4,
            pick_up_at=Location(lat=4.678759, lng=-74.055729),
            drop_off_at=Location(lat=4.661441, lng=-74.056955),
            ready_time=time(12, 34, 0),
            expected_drop_off_time=time(12, 44, 0),
            pick_up_service_time=0,
            drop_off_service_time=0
        )

        # Couriers
        courier_1 = Courier(
            courier_id=1,
            on_time=on_time,
            off_time=off_time,
            condition='idle',
            location=Location(lat=4.676854, lng=-74.057498)
        )
        courier_2 = Courier(
            courier_id=2,
            on_time=on_time,
            off_time=off_time,
            condition='idle',
            location=Location(lat=4.679408, lng=-74.052524)
        )

        # Routes
        policy = MyopicMatchingPolicy(
            assignment_updates=True,
            prospects=True,
            notification_filtering=False,
            mip_matcher=False
        )
        routes = policy._generate_routes(
            orders=[order_1, order_2, order_3, order_4],
            couriers=[courier_1, courier_2],
            env_time=env_time
        )

        # Generate prospects and assert expected behavior
        prospects = policy._generate_matching_prospects(
            routes=routes,
            couriers=[courier_1, courier_2],
            env_time=env_time
        )
        self.assertTrue(prospects.tolist())
        self.assertEqual(len(prospects), 8)

    @patch('services.osrm_service.OSRMService.get_route', side_effect=mocked_get_route)
    @patch('settings.settings.DISPATCHER_PROSPECTS_MAX_STOP_OFFSET', min_to_sec(15))
    def test_generate_matching_prospects_picking_up_couriers(self, osrm):
        """Test to verify how prospects are created"""

        # Constants
        env_time = hour_to_sec(12) + min_to_sec(20)
        on_time = time(8, 0, 0)
        off_time = time(16, 0, 0)

        # Orders
        order_1 = Order(
            order_id=1,
            pick_up_at=Location(lat=4.678759, lng=-74.055729),
            drop_off_at=Location(lat=4.681694, lng=-74.044811),
            ready_time=time(12, 30, 0),
            expected_drop_off_time=time(12, 40, 0),
            pick_up_service_time=0,
            drop_off_service_time=0
        )
        order_2 = Order(
            order_id=2,
            pick_up_at=Location(lat=4.678759, lng=-74.055729),
            drop_off_at=Location(lat=4.695001, lng=-74.040737),
            ready_time=time(12, 32, 0),
            expected_drop_off_time=time(12, 42, 0),
            pick_up_service_time=0,
            drop_off_service_time=0
        )
        order_3 = Order(
            order_id=3,
            pick_up_at=Location(lat=4.678759, lng=-74.055729),
            drop_off_at=Location(lat=4.668742, lng=-74.056684),
            ready_time=time(12, 33, 0),
            expected_drop_off_time=time(12, 43, 0),
            pick_up_service_time=0,
            drop_off_service_time=0
        )

        # Couriers
        courier_3 = Courier(
            courier_id=3,
            on_time=on_time,
            off_time=off_time,
            condition='picking_up',
            location=order_3.pick_up_at,
            active_route=Route(
                orders={order_3.order_id: order_3},
                stops=[
                    Stop(
                        location=order_3.pick_up_at,
                        orders={order_3.order_id: order_3},
                        position=0,
                        type=StopType.PICK_UP
                    ),
                    Stop(
                        location=order_3.drop_off_at,
                        orders={order_3.order_id: order_3},
                        position=1,
                        type=StopType.DROP_OFF
                    )
                ]
            ),
            active_stop=Stop(
                location=order_3.pick_up_at,
                orders={order_3.order_id: order_3},
                position=0,
                type=StopType.PICK_UP
            )
        )

        # Get routes and assert expected behavior
        policy = MyopicMatchingPolicy(
            assignment_updates=True,
            prospects=True,
            notification_filtering=False,
            mip_matcher=False
        )
        routes = policy._generate_routes(
            orders=[order_1, order_2],
            couriers=[courier_3],
            env_time=env_time
        )

        # Generate prospects and assert expected behavior
        prospects = policy._generate_matching_prospects(
            routes=routes,
            couriers=[courier_3],
            env_time=env_time
        )
        self.assertFalse(prospects.tolist())

    @patch('services.osrm_service.OSRMService.get_route', side_effect=mocked_get_route)
    @patch('settings.settings.DISPATCHER_PROSPECTS_MAX_STOP_OFFSET', min_to_sec(15))
    @patch('settings.settings.DISPATCHER_MYOPIC_READY_TIME_SLACK', min_to_sec(20))
    def test_myopic_matching_policy_execute(self, osrm):
        """Test to verify how the optimization model is solved"""

        # Constants
        env_time = hour_to_sec(12) + min_to_sec(20)
        on_time = time(8, 0, 0)
        off_time = time(16, 0, 0)
        random.seed(45)

        # Orders
        order_1 = Order(
            order_id=1,
            pick_up_at=Location(lat=4.678759, lng=-74.055729),
            drop_off_at=Location(lat=4.681694, lng=-74.044811),
            ready_time=time(12, 30, 0),
            expected_drop_off_time=time(12, 40, 0),
            pick_up_service_time=0,
            drop_off_service_time=0
        )
        order_2 = Order(
            order_id=2,
            pick_up_at=Location(lat=4.678759, lng=-74.055729),
            drop_off_at=Location(lat=4.695001, lng=-74.040737),
            ready_time=time(12, 32, 0),
            expected_drop_off_time=time(12, 42, 0),
            pick_up_service_time=0,
            drop_off_service_time=0
        )
        order_3 = Order(
            order_id=3,
            pick_up_at=Location(lat=4.678759, lng=-74.055729),
            drop_off_at=Location(lat=4.668742, lng=-74.056684),
            ready_time=time(12, 33, 0),
            expected_drop_off_time=time(12, 43, 0),
            pick_up_service_time=0,
            drop_off_service_time=0
        )
        order_4 = Order(
            order_id=4,
            pick_up_at=Location(lat=4.678759, lng=-74.055729),
            drop_off_at=Location(lat=4.661441, lng=-74.056955),
            ready_time=time(12, 34, 0),
            expected_drop_off_time=time(12, 44, 0),
            pick_up_service_time=0,
            drop_off_service_time=0
        )

        # Couriers
        courier_1 = Courier(
            courier_id=1,
            on_time=on_time,
            off_time=off_time,
            condition='idle',
            location=Location(lat=4.676854, lng=-74.057498)
        )
        courier_2 = Courier(
            courier_id=2,
            on_time=on_time,
            off_time=off_time,
            condition='idle',
            location=Location(lat=4.679408, lng=-74.052524)
        )
        courier_3 = Courier(
            courier_id=3,
            on_time=on_time,
            off_time=off_time,
            condition='picking_up',
            location=order_3.pick_up_at,
            active_route=Route(
                orders={order_3.order_id: order_3},
                stops=[
                    Stop(
                        location=order_3.pick_up_at,
                        orders={order_3.order_id: order_3},
                        position=0,
                        type=StopType.PICK_UP
                    ),
                    Stop(
                        location=order_3.drop_off_at,
                        orders={order_3.order_id: order_3},
                        position=1,
                        type=StopType.DROP_OFF
                    )
                ]
            ),
            active_stop=Stop(
                location=order_3.pick_up_at,
                orders={order_3.order_id: order_3},
                position=0,
                type=StopType.PICK_UP
            )
        )

        # Get all the elements from the policy and assert their expected behavior
        policy = MyopicMatchingPolicy(
            assignment_updates=True,
            prospects=True,
            notification_filtering=False,
            mip_matcher=False
        )
        routes = policy._generate_routes(
            orders=[order_1, order_2, order_4],
            couriers=[courier_1, courier_2, courier_3],
            env_time=env_time
        )
        self.assertTrue(routes)
        self.assertEqual(len(routes), 3)
        self.assertEqual(routes[0].initial_prospect, courier_3.courier_id),
        self.assertIn(order_4.order_id, routes[0].orders)
        self.assertEqual(len(routes[0].orders), 1)
        self.assertEqual(len(routes[1].orders), 1)
        self.assertEqual(len(routes[2].orders), 1)

        prospects = policy._generate_matching_prospects(
            routes=routes,
            couriers=[courier_1, courier_2, courier_3],
            env_time=env_time
        )
        self.assertTrue(prospects.tolist())
        self.assertEqual(len(prospects), 7)
        courier_3_prospects = [prospect for prospect in prospects if prospect[0] == 2]
        self.assertEqual(len(courier_3_prospects), 1)

        costs = policy._generate_matching_costs(
            routes=routes,
            couriers=[courier_1, courier_2, courier_3],
            prospects=prospects,
            env_time=env_time
        )
        self.assertTrue(costs.tolist())
        self.assertEqual(len(prospects), len(costs))
        self.assertEqual(len(costs), 7)
        self.assertNotIn(0., costs)

        problem = MatchingProblemBuilder.build(
            routes=routes,
            couriers=[courier_1, courier_2, courier_3],
            prospects=prospects,
            costs=costs
        )
        self.assertTrue(problem)
        self.assertEqual(len(prospects), len(problem.prospects))
        self.assertEqual(len(prospects), len(problem.matching_prospects))
        self.assertEqual(len(prospects), len(problem.costs))
        self.assertEqual(routes, problem.routes)
        self.assertEqual(problem.couriers, [courier_1, courier_2, courier_3])

        graph = GraphBuilder.build(problem)
        self.assertTrue(graph)
        self.assertEqual(len(graph.nodes), 7)
        self.assertEqual(len(graph.arcs), 13)

        model_builder = GraphOptimizationModelBuilder(sense='max', model_constraints=[BalanceConstraint()])
        model = model_builder.build(graph)
        self.assertTrue(model)
        self.assertEqual(len(model.constraints), len(graph.nodes))
        self.assertEqual(len(model.variable_set), len(graph.arcs))

        solution = model.solve()
        self.assertTrue(solution.tolist())
        self.assertEqual(len(solution), len(graph.arcs))
        self.assertEqual(solution[0:len(problem.prospects)].sum(), 3)
        self.assertEqual(solution.sum(), 6)

        notifications = policy._process_solution(solution, problem, env_time)
        self.assertEqual(len(notifications), len(routes))
        self.assertIsInstance(notifications[0].instruction[0], Stop)
        self.assertIsInstance(notifications[1].instruction, Route)
        self.assertIsInstance(notifications[2].instruction, Route)
        self.assertEqual(notifications[0].courier, courier_3)
        self.assertIn(order_4.order_id, notifications[0].instruction[0].orders.keys())

    @patch('services.osrm_service.OSRMService.get_route', side_effect=mocked_get_route)
    @patch('settings.settings.DISPATCHER_PROSPECTS_MAX_STOP_OFFSET', min_to_sec(15))
    @patch('settings.settings.DISPATCHER_MYOPIC_READY_TIME_SLACK', min_to_sec(20))
    def test_myopic_matching_policy_execute_mip_matcher(self, osrm):
        """Test to verify how the optimization model is solved with a MIP approach"""

        # Constants
        env_time = hour_to_sec(12) + min_to_sec(20)
        on_time = time(8, 0, 0)
        off_time = time(16, 0, 0)
        random.seed(45)

        # Orders
        order_1 = Order(
            order_id=1,
            pick_up_at=Location(lat=4.678759, lng=-74.055729),
            drop_off_at=Location(lat=4.681694, lng=-74.044811),
            ready_time=time(12, 30, 0),
            expected_drop_off_time=time(12, 40, 0),
            pick_up_service_time=0,
            drop_off_service_time=0
        )
        order_2 = Order(
            order_id=2,
            pick_up_at=Location(lat=4.678759, lng=-74.055729),
            drop_off_at=Location(lat=4.695001, lng=-74.040737),
            ready_time=time(12, 32, 0),
            expected_drop_off_time=time(12, 42, 0),
            pick_up_service_time=0,
            drop_off_service_time=0
        )
        order_3 = Order(
            order_id=3,
            pick_up_at=Location(lat=4.678759, lng=-74.055729),
            drop_off_at=Location(lat=4.668742, lng=-74.056684),
            ready_time=time(12, 33, 0),
            expected_drop_off_time=time(12, 43, 0),
            pick_up_service_time=0,
            drop_off_service_time=0
        )
        order_4 = Order(
            order_id=4,
            pick_up_at=Location(lat=4.678759, lng=-74.055729),
            drop_off_at=Location(lat=4.661441, lng=-74.056955),
            ready_time=time(12, 34, 0),
            expected_drop_off_time=time(12, 44, 0),
            pick_up_service_time=0,
            drop_off_service_time=0
        )

        # Couriers
        courier_1 = Courier(
            courier_id=1,
            on_time=on_time,
            off_time=off_time,
            condition='idle',
            location=Location(lat=4.676854, lng=-74.057498)
        )
        courier_2 = Courier(
            courier_id=2,
            on_time=on_time,
            off_time=off_time,
            condition='idle',
            location=Location(lat=4.679408, lng=-74.052524)
        )
        courier_3 = Courier(
            courier_id=3,
            on_time=on_time,
            off_time=off_time,
            condition='picking_up',
            location=order_3.pick_up_at,
            active_route=Route(
                orders={order_3.order_id: order_3},
                stops=[
                    Stop(
                        location=order_3.pick_up_at,
                        orders={order_3.order_id: order_3},
                        position=0,
                        type=StopType.PICK_UP
                    ),
                    Stop(
                        location=order_3.drop_off_at,
                        orders={order_3.order_id: order_3},
                        position=1,
                        type=StopType.DROP_OFF
                    )
                ]
            ),
            active_stop=Stop(
                location=order_3.pick_up_at,
                orders={order_3.order_id: order_3},
                position=0,
                type=StopType.PICK_UP
            )
        )

        # Get all the elements from the policy and assert their expected behavior
        policy = MyopicMatchingPolicy(
            assignment_updates=False,
            prospects=False,
            notification_filtering=False,
            mip_matcher=False
        )
        routes = policy._generate_routes(
            orders=[order_1, order_2, order_4],
            couriers=[courier_1, courier_2, courier_3],
            env_time=env_time
        )
        self.assertTrue(routes)
        self.assertEqual(len(routes), 2)
        self.assertEqual(len(routes[0].orders), 2)
        self.assertEqual(len(routes[1].orders), 1)

        prospects = policy._generate_matching_prospects(
            routes=routes,
            couriers=[courier_1, courier_2, courier_3],
            env_time=env_time
        )
        self.assertTrue(prospects.tolist())
        self.assertEqual(len(prospects), 4),
        self.assertEqual(len(prospects), len(routes) * len([courier_1, courier_2]))

        costs = policy._generate_matching_costs(
            routes=routes,
            couriers=[courier_1, courier_2, courier_3],
            prospects=prospects,
            env_time=env_time
        )
        self.assertTrue(costs.tolist())
        self.assertEqual(len(prospects), len(costs))
        self.assertEqual(len(costs), 4)
        self.assertNotIn(0., costs)

        problem = MatchingProblemBuilder.build(
            routes=routes,
            couriers=[courier_1, courier_2, courier_3],
            prospects=prospects,
            costs=costs
        )
        self.assertTrue(problem)
        self.assertEqual(len(prospects), len(problem.prospects))
        self.assertEqual(len(prospects), len(problem.matching_prospects))
        self.assertEqual(len(prospects), len(problem.costs))
        self.assertEqual(routes, problem.routes)
        self.assertEqual(problem.couriers, [courier_1, courier_2, courier_3])
        self.assertNotIn(str(courier_3.courier_id), problem.matching_prospects['i'])

        model_builder = MIPOptimizationModelBuilder(
            sense='max',
            model_constraints=[CourierAssignmentConstraint(), RouteAssignmentConstraint()]
        )
        model = model_builder.build(problem)
        self.assertTrue(model)
        self.assertEqual(len(model.constraints), len(problem.routes) + len([courier_1, courier_2]))
        self.assertEqual(len(model.variable_set), len(problem.matching_prospects) + len(problem.routes))

        solution = model.solve()
        self.assertTrue(solution.tolist())
        self.assertEqual(len(solution), len(problem.matching_prospects) + len(problem.routes))
        self.assertEqual(solution[0:len(problem.prospects)].sum(), 2)
        self.assertEqual(solution.sum(), 2)

        notifications = policy._process_solution(solution, problem, env_time)
        self.assertEqual(len(notifications), len(routes))
        self.assertIsInstance(notifications[0].instruction, Route)
        self.assertIsInstance(notifications[1].instruction, Route)
        self.assertEqual(notifications[0].courier, courier_1)
        self.assertEqual(notifications[1].courier, courier_2)
        self.assertIn(order_1.order_id, notifications[1].instruction.orders.keys())
        self.assertIn(order_4.order_id, notifications[1].instruction.orders.keys())
