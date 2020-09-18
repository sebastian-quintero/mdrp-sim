from dataclasses import dataclass
from datetime import time
from typing import List, Dict, Any, Iterable

from simpy import Environment

from actors.courier import Courier
from actors.dispatcher import Dispatcher
from actors.user import User
from objects.order import Order
from utils.datetime_utils import hour_to_sec, sec_to_time


@dataclass
class World:
    """A class to handle the simulated world"""

    def simulate(self) -> Any:
        """Process that simulates the ongoing world of the simulated environment"""

        env = Environment()
        dispatcher = Dispatcher(env=env)

        for second in range(hour_to_sec(24)):
            yield env.timeout(delay=1)

            orders_info = self._new_orders_info(sec_to_time(env.now))
            for order_info in orders_info:
                user = User(
                    env=env,
                    dispatcher=dispatcher
                )
                yield env.process(user.submit_order_event(**order_info))

            couriers_info = self._new_couriers_info(sec_to_time(env.now))
            for courier_info in couriers_info:
                courier = Courier(
                    env=env,
                    dispatcher=dispatcher,
                    **courier_info
                )
                yield env.process(courier.log_off_event)

        env.run(until=hour_to_sec(24))

        metrics = self._calculate_metrics(
            orders={**dispatcher.fulfilled_orders, **dispatcher.canceled_orders}.values(),
            couriers={**dispatcher.idle_couriers}
        )

        return metrics

    def _new_orders_info(self, current_time: time) -> List[Dict[str, Any]]:
        """Method that returns the list of new users that log on at a given time"""

        # TODO: finish method to obtain new orders
        pass

    def _new_couriers_info(self, current_time: time) -> List[Dict[str, Any]]:
        """Method that returns the list of new couriers that log on at a given time"""

        # TODO: finish method to obtain new couriers
        pass

    def _calculate_metrics(self, orders: Iterable[Order], couriers: Iterable[Courier]) -> Any:
        """Method to calculate metrics of the simulated world"""

        # TODO: finish method to calculate metrics
        pass
