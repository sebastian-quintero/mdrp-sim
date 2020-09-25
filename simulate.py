from dataclasses import dataclass, field
from datetime import time
from typing import List, Dict, Any, Iterable, Optional

import pandas as pd
from simpy import Environment
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

import settings
from actors.courier import Courier, COURIER_ACCEPTANCE_POLICIES_MAP, COURIER_MOVEMENT_EVALUATION_POLICIES_MAP, \
    COURIER_MOVEMENT_POLICIES_MAP
from actors.dispatcher import Dispatcher, DISPATCHER_CANCELLATION_POLICIES_MAP, DISPATCHER_BUFFERING_POLICIES_MAP, \
    DISPATCHER_MATCHING_POLICIES_MAP, DISPATCHER_PREPOSITIONING_POLICIES_MAP, \
    DISPATCHER_PREPOSITIONING_TIMING_POLICIES_MAP
from actors.user import User, USER_CANCELLATION_POLICIES_MAP
from ddbb.config import get_db_url
from objects.location import Location
from objects.order import Order
from objects.vehicle import Vehicle
from utils.datetime_utils import sec_to_time
from utils.logging_utils import configure_logs


@dataclass
class World:
    """A class to handle the simulated world"""

    orders_query = """
        SELECT
            order_id,
            pick_up_lat,
            pick_up_lng,
            drop_off_lat,
            drop_off_lng,
            placement_time,
            preparation_time,
            ready_time,
            expected_drop_off_time
        FROM orders_instance_data
        WHERE placement_time = {placement_time} AND instance_id = {instance_id}
    """
    couriers_query = """
        SELECT
            courier_id,
            vehicle,
            on_lat,
            on_lng,
            on_time,
            off_time
        FROM couriers_instance_data
        WHERE on_time = {on_time} AND instance_id = {instance_id}
    """

    env = Environment()
    couriers: List[Courier] = field(default_factory=lambda: list())
    dispatcher: Optional[Dispatcher] = None
    users: List[User] = field(default_factory=lambda: list())

    def __post_init__(self):
        """The world is instantiated along with the single dispatcher"""

        self.dispatcher = Dispatcher(
            env=self.env,
            cancellation_policy=DISPATCHER_CANCELLATION_POLICIES_MAP[settings.DISPATCHER_CANCELLATION_POLICY],
            buffering_policy=DISPATCHER_BUFFERING_POLICIES_MAP[settings.DISPATCHER_BUFFERING_POLICY],
            matching_policy=DISPATCHER_MATCHING_POLICIES_MAP[settings.DISPATCHER_MATCHING_POLICY],
            prepositioning_policy=DISPATCHER_PREPOSITIONING_POLICIES_MAP[settings.DISPATCHER_PREPOSITIONING_POLICY],
            prepositioning_timing_policy=DISPATCHER_PREPOSITIONING_TIMING_POLICIES_MAP[
                settings.DISPATCHER_PREPOSITIONING_TIMING_POLICY
            ]
        )

    def simulate(self) -> Any:
        """Process that simulates the ongoing world of the simulated environment"""

        connection = create_engine(get_db_url(), pool_size=20, max_overflow=0, pool_pre_ping=True)

        for second in range(settings.SIMULATE_UNTIL):

            orders_info = self._new_orders_info(
                current_time=sec_to_time(second),
                ddbb_con=connection
            )
            if orders_info is not None:
                self._new_users_procedure(orders_info)

            couriers_info = self._new_couriers_info(
                current_time=sec_to_time(second),
                ddbb_con=connection
            )
            if couriers_info is not None:
                self._new_couriers_procedure(couriers_info)

            self.env.timeout(delay=1)

        self.env.run(until=settings.SIMULATE_UNTIL)

        #  TODO: return metrics and output them to the DDBB
        # metrics = self._calculate_metrics(
        #    orders={**dispatcher.fulfilled_orders, **dispatcher.canceled_orders}.values(),
        #    couriers={**dispatcher.idle_couriers}
        # )

        # return metrics

    def _new_orders_info(self, current_time: time, ddbb_con: Engine) -> Optional[List[Dict[str, Any]]]:
        """Method that returns the list of new users that log on at a given time"""

        query = self.orders_query.format(
            placement_time=f'\'{current_time.hour}:{current_time.minute}:{current_time.second}\'',
            instance_id=settings.INSTANCE
        )
        orders_df = pd.read_sql(sql=query, con=ddbb_con)

        return orders_df.to_dict('records') if not orders_df.empty else None

    def _new_couriers_info(self, current_time: time, ddbb_con: Engine) -> Optional[List[Dict[str, Any]]]:
        """Method that returns the list of new couriers that log on at a given time"""

        query = self.couriers_query.format(
            on_time=f'\'{current_time.hour}:{current_time.minute}:{current_time.second}\'',
            instance_id=settings.INSTANCE
        )
        couriers_df = pd.read_sql(sql=query, con=ddbb_con)

        return couriers_df.to_dict('records') if not couriers_df.empty else None

    def _new_users_procedure(self, orders_info: List[Dict[str, Any]]):
        """Method to establish how a new user is created in the World"""

        for order_info in orders_info:
            user = User(
                env=self.env,
                dispatcher=self.dispatcher,
                cancellation_policy=USER_CANCELLATION_POLICIES_MAP[settings.USER_CANCELLATION_POLICY],
                user_id=order_info['order_id']
            )
            self.env.process(user.submit_order_event(
                order_id=order_info['order_id'],
                pick_up_at=Location(lat=order_info['pick_up_lat'], lng=order_info['pick_up_lng']),
                drop_off_at=Location(lat=order_info['drop_off_lat'], lng=order_info['drop_off_lng']),
                placement_time=order_info['placement_time'],
                expected_drop_off_time=order_info['expected_drop_off_time'],
                preparation_time=order_info['preparation_time'],
                ready_time=order_info['ready_time']
            ))
            self.users.append(user)

    def _new_couriers_procedure(self, couriers_info: List[Dict[str, Any]]):
        """Method to establish how a new courier is created in the World"""

        for courier_info in couriers_info:
            courier = Courier(
                env=self.env,
                dispatcher=self.dispatcher,
                acceptance_policy=COURIER_ACCEPTANCE_POLICIES_MAP[settings.COURIER_ACCEPTANCE_POLICY],
                movement_evaluation_policy=COURIER_MOVEMENT_EVALUATION_POLICIES_MAP[
                    settings.COURIER_MOVEMENT_EVALUATION_POLICY
                ],
                movement_policy=COURIER_MOVEMENT_POLICIES_MAP[settings.COURIER_MOVEMENT_POLICY],
                courier_id=courier_info['courier_id'],
                vehicle=Vehicle.from_label(label=courier_info['vehicle']),
                location=Location(lat=courier_info['on_lat'], lng=courier_info['on_lng']),
                on_time=courier_info['on_time'],
                off_time=courier_info['off_time']
            )
            self.couriers.append(courier)

    def _calculate_metrics(self, orders: Iterable[Order], couriers: Iterable[Courier]) -> Any:
        """Method to calculate metrics of the simulated world"""

        # TODO: finish method to calculate metrics
        pass


if __name__ == '__main__':
    """Main method for running the mdrp-sim"""

    configure_logs()

    world = World()
    world.simulate()
