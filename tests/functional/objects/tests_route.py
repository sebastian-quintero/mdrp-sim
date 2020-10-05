import unittest

from objects.order import Order
from objects.route import Route
from objects.stop import Stop, StopType


class TestsRoute(unittest.TestCase):
    """Class for the Route object class"""

    def test_update_route(self):
        """Test to verify a route is updated based on canceled orders"""

        # Test 1: define a route and some orders being canceled
        order_1 = Order(order_id=1)
        order_2 = Order(order_id=2)
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
                    position=0
                ),
                Stop(
                    orders={order_2.order_id: order_2},
                    type=StopType.PICK_UP,
                    position=1
                ),
                Stop(
                    orders={order_1.order_id: order_1},
                    type=StopType.DROP_OFF,
                    position=2
                ),
                Stop(
                    orders={order_2.order_id: order_2},
                    type=StopType.DROP_OFF,
                    position=3
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
        order_1 = Order(order_id=1)
        order_2 = Order(order_id=2)
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
                    position=0
                ),
                Stop(
                    orders=orders_dict,
                    type=StopType.DROP_OFF,
                    position=2
                )
            ]
        )
        canceled_order_ids = [1, 2]

        # Update the route and assert canceled orders were removed
        route.update(canceled_order_ids)
        self.assertEqual(len(route.orders), 0)
        self.assertEqual(len(route.stops), 0)
