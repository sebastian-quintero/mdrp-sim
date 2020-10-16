import unittest
from unittest.mock import patch

from objects.location import Location
from objects.order import Order
from objects.route import Route
from objects.stop import Stop, StopType
from tests.test_utils import mocked_get_route


class TestsRoute(unittest.TestCase):
    """Class for the Route object class"""

    @patch('services.osrm_service.OSRMService.get_route', side_effect=mocked_get_route)
    def test_update_route(self, osrm):
        """Test to verify a route is updated based on canceled orders"""

        # Constants
        order_1 = Order(
            order_id=1,
            pick_up_at=Location(lat=4.567, lng=1.234),
            drop_off_at=Location(lat=1.234, lng=4.567)
        )
        order_2 = Order(
            order_id=2,
            pick_up_at=Location(lat=4.567, lng=1.234),
            drop_off_at=Location(lat=1.234, lng=4.567)
        )

        # Test 1: define a route and some orders being canceled
        orders_dict = {
            order_1.order_id: order_1,
            order_2.order_id: order_2
        }
        route = Route(
            orders=orders_dict,
            stops=[
                Stop(
                    orders={order_1.order_id: order_1},
                    type=StopType.PICK_UP,
                    position=0,
                    location=order_1.pick_up_at
                ),
                Stop(
                    orders={order_2.order_id: order_2},
                    type=StopType.PICK_UP,
                    position=1,
                    location=order_2.pick_up_at
                ),
                Stop(
                    orders={order_1.order_id: order_1},
                    type=StopType.DROP_OFF,
                    position=2,
                    location=order_1.drop_off_at
                ),
                Stop(
                    orders={order_2.order_id: order_2},
                    type=StopType.DROP_OFF,
                    position=3,
                    location=order_2.drop_off_at
                )
            ]
        )
        canceled_order_ids = [1]

        # Update the route and assert canceled orders were removed
        route.update(canceled_order_ids)
        self.assertEqual(len(route.orders), 1)
        self.assertEqual(len(route.stops), 2)
        for stop in route.stops:
            self.assertNotIn(order_1.order_id, stop.orders)
            self.assertEqual(len(stop.orders), 1)

        # Test 2: define a route and all orders being canceled
        orders_dict = {
            order_1.order_id: order_1,
            order_2.order_id: order_2
        }
        route = Route(
            orders=orders_dict,
            stops=[
                Stop(
                    orders=orders_dict,
                    type=StopType.PICK_UP,
                    position=0,
                    location=order_1.pick_up_at
                ),
                Stop(
                    orders=orders_dict,
                    type=StopType.DROP_OFF,
                    position=2,
                    location=order_1.drop_off_at
                )
            ]
        )
        canceled_order_ids = [1, 2]

        # Update the route and assert canceled orders were removed
        route.update(canceled_order_ids)
        self.assertEqual(len(route.orders), 0)
        self.assertEqual(len(route.stops), 0)

    @patch('services.osrm_service.OSRMService.get_route', side_effect=mocked_get_route)
    def test_add_order(self, osrm):
        """Test to verify how a new order is added to an existing route"""

        # Constants
        old_order = Order(
            order_id=5,
            pick_up_at=Location(lat=4.567, lng=1.234),
            drop_off_at=Location(lat=1.234, lng=4.567)
        )
        new_order = Order(
            order_id=1,
            pick_up_at=Location(lat=1.234, lng=4.567),
            drop_off_at=Location(lat=4.567, lng=1.234)
        )

        # Case 1: the route is empty
        route = Route(num_stops=2)
        route.add_order(new_order)
        self.assertTrue(route.stops)
        self.assertEqual(len(route.stops), 2)
        self.assertEqual(len(route.stops), route.num_stops)
        self.assertIn(new_order.order_id, route.orders.keys())
        self.assertIn(new_order.order_id, route.stops[0].orders.keys())
        self.assertIn(new_order.order_id, route.stops[1].orders.keys())
        self.assertEqual(route.stops[0].type, StopType.PICK_UP)
        self.assertEqual(route.stops[1].type, StopType.DROP_OFF)
        self.assertTrue(route.time)

        # Case 2. the route has an order and is inserted at correct position
        route = Route(
            orders={old_order.order_id: old_order},
            stops=[
                Stop(
                    location=old_order.pick_up_at,
                    orders={old_order.order_id: old_order},
                    position=0,
                    type=StopType.PICK_UP
                ),
                Stop(
                    location=old_order.drop_off_at,
                    orders={old_order.order_id: old_order},
                    position=1,
                    type=StopType.DROP_OFF
                )
            ]
        )
        route.add_order(new_order, route_position=2)
        self.assertTrue(route)
        self.assertEqual(len(route.stops), 3)
        self.assertEqual(len(route.stops), route.num_stops)
        self.assertIn(new_order.order_id, route.orders.keys())
        self.assertIn(old_order.order_id, route.orders.keys())
        self.assertIn(new_order.order_id, route.stops[0].orders.keys())
        self.assertIn(old_order.order_id, route.stops[0].orders.keys())
        self.assertIn(old_order.order_id, route.stops[1].orders.keys())
        self.assertIn(new_order.order_id, route.stops[2].orders.keys())
        self.assertEqual(route.stops[0].type, StopType.PICK_UP)
        self.assertEqual(route.stops[1].type, StopType.DROP_OFF)
        self.assertEqual(route.stops[2].type, StopType.DROP_OFF)
        self.assertTrue(route.time)

        # Case 3. the route has an order and is inserted at wrong position (greater position)
        route = Route(
            orders={old_order.order_id: old_order},
            stops=[
                Stop(
                    location=old_order.pick_up_at,
                    orders={old_order.order_id: old_order},
                    position=0,
                    type=StopType.PICK_UP
                ),
                Stop(
                    location=old_order.drop_off_at,
                    orders={old_order.order_id: old_order},
                    position=1,
                    type=StopType.DROP_OFF
                )
            ]
        )
        route.add_order(new_order, route_position=6)
        self.assertTrue(route)
        self.assertEqual(len(route.stops), 3)
        self.assertEqual(len(route.stops), route.num_stops)
        self.assertIn(new_order.order_id, route.orders.keys())
        self.assertIn(old_order.order_id, route.orders.keys())
        self.assertIn(new_order.order_id, route.stops[0].orders.keys())
        self.assertIn(old_order.order_id, route.stops[0].orders.keys())
        self.assertIn(old_order.order_id, route.stops[1].orders.keys())
        self.assertIn(new_order.order_id, route.stops[2].orders.keys())
        self.assertEqual(route.stops[0].type, StopType.PICK_UP)
        self.assertEqual(route.stops[1].type, StopType.DROP_OFF)
        self.assertEqual(route.stops[2].type, StopType.DROP_OFF)
        self.assertTrue(route.time)

        # Case 4. the route has an order and is inserted at wrong position (equal position)
        route = Route(
            orders={old_order.order_id: old_order},
            stops=[
                Stop(
                    location=old_order.pick_up_at,
                    orders={old_order.order_id: old_order},
                    position=0,
                    type=StopType.PICK_UP
                ),
                Stop(
                    location=old_order.drop_off_at,
                    orders={old_order.order_id: old_order},
                    position=1,
                    type=StopType.DROP_OFF
                )
            ]
        )
        route.add_order(new_order, route_position=1)
        self.assertTrue(route)
        self.assertEqual(len(route.stops), 3)
        self.assertEqual(len(route.stops), route.num_stops)
        self.assertIn(new_order.order_id, route.orders.keys())
        self.assertIn(old_order.order_id, route.orders.keys())
        self.assertIn(new_order.order_id, route.stops[0].orders.keys())
        self.assertIn(old_order.order_id, route.stops[0].orders.keys())
        self.assertIn(old_order.order_id, route.stops[1].orders.keys())
        self.assertIn(new_order.order_id, route.stops[2].orders.keys())
        self.assertEqual(route.stops[0].type, StopType.PICK_UP)
        self.assertEqual(route.stops[1].type, StopType.DROP_OFF)
        self.assertEqual(route.stops[2].type, StopType.DROP_OFF)
        self.assertTrue(route.time)

        # Case 5. the route has an order and is inserted at wrong position (smaller position)
        route = Route(
            orders={old_order.order_id: old_order},
            stops=[
                Stop(
                    location=old_order.pick_up_at,
                    orders={old_order.order_id: old_order},
                    position=0,
                    type=StopType.PICK_UP
                ),
                Stop(
                    location=old_order.drop_off_at,
                    orders={old_order.order_id: old_order},
                    position=1,
                    type=StopType.DROP_OFF
                )
            ]
        )
        route.add_order(new_order, route_position=1)
        self.assertTrue(route)
        self.assertEqual(len(route.stops), 3)
        self.assertEqual(len(route.stops), route.num_stops)
        self.assertIn(new_order.order_id, route.orders.keys())
        self.assertIn(old_order.order_id, route.orders.keys())
        self.assertIn(new_order.order_id, route.stops[0].orders.keys())
        self.assertIn(old_order.order_id, route.stops[0].orders.keys())
        self.assertIn(old_order.order_id, route.stops[1].orders.keys())
        self.assertIn(new_order.order_id, route.stops[2].orders.keys())
        self.assertEqual(route.stops[0].type, StopType.PICK_UP)
        self.assertEqual(route.stops[1].type, StopType.DROP_OFF)
        self.assertEqual(route.stops[2].type, StopType.DROP_OFF)
        self.assertTrue(route.time)
