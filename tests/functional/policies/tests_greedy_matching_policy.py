import unittest
from datetime import time
from unittest.mock import patch

import numpy as np
from haversine import haversine

from actors.courier import Courier
from objects.location import Location
from objects.order import Order
from objects.route import Route
from objects.vehicle import Vehicle
from policies.dispatcher.matching.greedy import GreedyMatchingPolicy
from tests.test_utils import mocked_get_route


class TestsGreedyMatchingPolicy(unittest.TestCase):
    """Tests for the greedy matching policy class"""

    @patch('settings.DISPATCHER_PROSPECTS_MAX_DISTANCE', 5)
    def test_get_prospects(self):
        """Test to verify how prospects are obtained"""

        # Constants
        on_time = time(14, 0, 0)
        off_time = time(16, 0, 0)

        # Services
        policy = GreedyMatchingPolicy()

        # Case 1: verify an order is prospect to a courier
        order = Order(pick_up_at=Location(4.678622, -74.055694), drop_off_at=Location(4.690207, -74.044235))
        courier = Courier(location=Location(4.709022, -74.035102), on_time=on_time, off_time=off_time)
        prospects = policy._get_prospects(orders=[order], couriers=[courier])
        self.assertEqual(prospects.tolist(), [[0, 0]])

        # Case 2: verify an order is not prospect to a courier
        order = Order(pick_up_at=Location(4.678622, -74.055694), drop_off_at=Location(4.690207, -74.044235))
        courier = Courier(
            location=Location(4.8090, -74.9351),
            on_time=on_time,
            off_time=off_time,
            active_route=Route(
                stops=[],
                orders={2: Order(), 3: Order(), 4: Order()}
            )
        )
        prospects = policy._get_prospects(orders=[order], couriers=[courier])
        self.assertEqual(prospects.tolist(), [])

        # Case 3: assert some orders being prospect and some not to some couriers
        order_1 = Order(
            pick_up_at=Location(4.678622, -74.055694),
            drop_off_at=Location(4.690207, -74.044235),
            order_id=1
        )
        order_2 = Order(
            pick_up_at=Location(1.178, -72.25),
            drop_off_at=Location(1.690207, -75.044235),
            order_id=2
        )
        courier_1 = Courier(location=Location(4.709022, -74.035102), on_time=on_time, off_time=off_time, courier_id=1)
        courier_2 = Courier(
            location=Location(4.709022, -74.035102),
            on_time=on_time,
            off_time=off_time,
            courier_id=2
        )
        prospects = policy._get_prospects(orders=[order_1, order_2], couriers=[courier_1, courier_2])
        self.assertEqual(len(prospects), 2)

    @patch('services.osrm_service.OSRMService.get_route', side_effect=mocked_get_route)
    def test_get_estimations(self, osrm):
        """Test to verify that estimations are correctly calculated"""

        # Constants
        on_time = time(15, 0, 0)
        off_time = time(16, 0, 0)

        # Services
        policy = GreedyMatchingPolicy()

        # Create an order and a courier and have them be prospects
        order = Order(pick_up_at=Location(4.678622, -74.055694), drop_off_at=Location(4.690207, -74.044235))
        courier = Courier(
            location=Location(4.709022, -74.035102),
            on_time=on_time,
            off_time=off_time,
            vehicle=Vehicle.CAR
        )
        prospects = np.array([[0, 0]])

        # Obtain estimations and assert they are correctly calculated
        estimations = policy._get_estimations(orders=[order], couriers=[courier], prospects=prospects)
        self.assertEqual(
            round(estimations['distance'].tolist()[0], 2),
            round(
                haversine(courier.location.coordinates, order.pick_up_at.coordinates) +
                haversine(order.pick_up_at.coordinates, order.drop_off_at.coordinates),
                2
            )
        )
        average_velocity = courier.vehicle.average_velocity
        self.assertEqual(
            int(estimations['time'][0]),
            int(
                haversine(courier.location.coordinates, order.pick_up_at.coordinates) / average_velocity +
                haversine(order.pick_up_at.coordinates, order.drop_off_at.coordinates) / average_velocity +
                order.pick_up_service_time +
                order.drop_off_service_time
            )
        )

    @patch('settings.DISPATCHER_PROSPECTS_MAX_DISTANCE', 8)
    @patch('services.osrm_service.OSRMService.get_route', side_effect=mocked_get_route)
    def test_execute(self, osrm):
        """Test the full functionality of the greedy matching policy"""

        # Constants
        on_time = time(7, 0, 0)
        off_time = time(9, 0, 0)

        # Services
        policy = GreedyMatchingPolicy()

        # Test 1: creates an order and two couriers.
        # Since the courier_2 is at the same location as the pick up, asserts it should get chosen for notification
        order = Order(pick_up_at=Location(4.678622, -74.055694), drop_off_at=Location(4.690207, -74.044235))
        courier_1 = Courier(
            location=Location(4.709022, -74.035102),
            on_time=on_time,
            off_time=off_time,
            vehicle=Vehicle.CAR,
            state='idle'
        )
        courier_2 = Courier(
            location=Location(4.678622, -74.055694),
            on_time=on_time,
            off_time=off_time,
            vehicle=Vehicle.CAR,
            state='idle'
        )
        notifications = policy.execute(orders=[order], couriers=[courier_1, courier_2], env_time=3)
        self.assertEqual(len(notifications), 1)
        self.assertEqual(notifications[0].courier, courier_2)
        self.assertIn(order, notifications[0].instruction.orders.values())

        # Test 2: creates two orders and two couriers.
        # The courier_1 is at the same location as the pick up of order_1.
        # The courier_2 is at the same location as the pick up of order_2.
        # In this fashion, courier_1 should be selected for order_1 and courier_2 for order_2
        order_1 = Order(
            pick_up_at=Location(4.678622, -74.055694),
            drop_off_at=Location(4.690207, -74.044235),
            order_id=1
        )
        order_2 = Order(
            pick_up_at=Location(4.690207, -74.044235),
            drop_off_at=Location(4.678622, -74.055694),
            order_id=2
        )
        courier_1 = Courier(
            location=Location(4.678622, -74.055694),
            on_time=on_time,
            off_time=off_time,
            vehicle=Vehicle.CAR,
            state='idle',
            courier_id=1
        )
        courier_2 = Courier(
            location=Location(4.690207, -74.044235),
            on_time=on_time,
            off_time=off_time,
            vehicle=Vehicle.CAR,
            state='idle',
            courier_id=2
        )
        notifications = policy.execute(orders=[order_1, order_2], couriers=[courier_1, courier_2], env_time=4)
        self.assertEqual(len(notifications), 2)
        self.assertEqual(notifications[0].courier, courier_1)
        self.assertIn(order_1, notifications[0].instruction.orders.values())
        self.assertEqual(notifications[1].courier, courier_2)
        self.assertIn(order_2, notifications[1].instruction.orders.values())

        # Test 3: creates more orders than couriers to check nothing breaks
        order_1 = Order(
            pick_up_at=Location(4.678622, -74.055694),
            drop_off_at=Location(4.690207, -74.044235),
            order_id=1
        )
        order_2 = Order(
            pick_up_at=Location(4.690207, -74.044235),
            drop_off_at=Location(4.678622, -74.055694),
            order_id=2
        )
        courier = Courier(
            location=Location(4.678622, -74.055694),
            on_time=on_time,
            off_time=off_time,
            vehicle=Vehicle.CAR,
            state='idle',
            courier_id=1
        )
        notifications = policy.execute(orders=[order_1, order_2], couriers=[courier], env_time=5)
        self.assertEqual(len(notifications), 1)
        self.assertEqual(notifications[0].courier, courier)
        self.assertIn(order_1, notifications[0].instruction.orders.values())
