import logging
from datetime import time
from typing import Dict

import pandas as pd
from sqlalchemy import create_engine, DateTime, Integer, Float, JSON, Time, Boolean, BigInteger

from actors.dispatcher import Dispatcher
from ddbb.config import get_db_url
from settings import settings, SIMULATION_KEYS, POLICIES_KEYS
from utils.datetime_utils import time_to_str


class MetricsService:
    """Class that contains the Metrics Service to calculate the output of a simulation"""

    def __init__(self, instance: int):
        """Instantiates the class by creating the DDBB connection"""

        self._instance = instance
        self._connection = create_engine(get_db_url(), pool_size=20, max_overflow=0, pool_pre_ping=True)

    def calculate_and_save_metrics(self, dispatcher: Dispatcher):
        """Method for calculating and saving the simulation metrics"""

        metrics = self._calculate_metrics(dispatcher)
        logging.info(f'Instance {self._instance} | Successful metrics calculation.')

        self._save_metrics(metrics)
        self._connection.dispose()
        logging.info(f'Instance {self._instance} | Successfully saved metrics to DDBB.')

    def _calculate_metrics(self, dispatcher: Dispatcher) -> Dict[str, pd.DataFrame]:
        """Method for calculating metrics based on the Dispatcher, after the simulation is finished"""

        settings_dict = {
            'instance_id': self._instance,
            'simulation_settings': {
                k: time_to_str(v) if isinstance(v, time) else v
                for k, v in settings.attributes.items()
                if k in SIMULATION_KEYS
            },
            'simulation_policies': {k: v for k, v in settings.attributes.items() if k in POLICIES_KEYS},
            'extra_settings': {
                k: v
                for k, v in settings.attributes.items()
                if k not in SIMULATION_KEYS and k not in POLICIES_KEYS
            }
        }
        order_metrics = [
            {**settings_dict, **order.calculate_metrics()}
            for order in list(dispatcher.fulfilled_orders.values()) + list(dispatcher.canceled_orders.values())
        ]
        courier_metrics = [
            {**settings_dict, **courier.calculate_metrics()}
            for courier in dispatcher.logged_off_couriers.values()
        ]
        matching_optimization_metrics = [
            {**settings_dict, **{'id': ix}, **metric.calculate_metrics()}
            for ix, metric in enumerate(dispatcher.matching_metrics)
        ]

        return {
            'order_metrics': pd.DataFrame(order_metrics),
            'courier_metrics': pd.DataFrame(courier_metrics),
            'matching_optimization_metrics': pd.DataFrame(matching_optimization_metrics)
        }

    def _save_metrics(self, metrics: Dict[str, pd.DataFrame]):
        """Method for saving the metrics to de DDBB"""

        order_metrics = metrics['order_metrics']
        courier_metrics = metrics['courier_metrics']
        matching_optimization_metrics = metrics['matching_optimization_metrics']
        order_metrics.to_sql(
            name='order_metrics',
            con=self._connection,
            if_exists='append',
            index=False,
            dtype={
                'created_at': DateTime,
                'instance_id': Integer,
                'simulation_settings': JSON,
                'simulation_policies': JSON,
                'extra_settings': JSON,
                'order_id': Integer,
                'placement_time': Time,
                'preparation_time': Time,
                'acceptance_time': Time,
                'in_store_time': Time,
                'ready_time': Time,
                'pick_up_time': Time,
                'drop_off_time': Time,
                'expected_drop_off_time': Time,
                'cancellation_time': Time,
                'dropped_off': Boolean,
                'click_to_door_time': Float,
                'click_to_taken_time': Float,
                'ready_to_door_time': Float,
                'ready_to_pick_up_time': Float,
                'in_store_to_pick_up_time': Float,
                'drop_off_lateness_time': Float,
                'click_to_cancel_time': Float,
            }
        )
        courier_metrics.to_sql(
            name='courier_metrics',
            con=self._connection,
            if_exists='append',
            index=False,
            dtype={
                'created_at': DateTime,
                'instance_id': Integer,
                'simulation_settings': JSON,
                'simulation_policies': JSON,
                'extra_settings': JSON,
                'courier_id': Integer,
                'on_time': Time,
                'off_time': Time,
                'fulfilled_orders': Integer,
                'earnings': Float,
                'utilization_time': Float,
                'accepted_notifications': Integer,
                'guaranteed_compensation': Boolean,
                'courier_utilization': Float,
                'courier_delivery_earnings': Float,
                'courier_compensation': Float,
                'courier_orders_delivered_per_hour': Float,
                'courier_bundles_picked_per_hour': Float,
            }
        )
        matching_optimization_metrics.to_sql(
            name='matching_optimization_metrics',
            con=self._connection,
            if_exists='append',
            index=False,
            dtype={
                'created_at': DateTime,
                'instance_id': Integer,
                'simulation_settings': JSON,
                'simulation_policies': JSON,
                'extra_settings': JSON,
                'id': Integer,
                'orders': Integer,
                'routes': Integer,
                'couriers': Integer,
                'variables': BigInteger,
                'constraints': BigInteger,
                'routing_time': Float,
                'matching_time': Float,
                'matches': Integer,
            }
        )
