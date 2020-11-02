import logging
from typing import Dict, List, Union

import numpy as np
import pandas as pd
from sqlalchemy import create_engine, DateTime, Integer, String, Float, JSON

import settings
from actors.dispatcher import Dispatcher
from ddbb.config import get_db_url
from objects.metric import Metric
from objects.notification import NotificationType
from objects.route import Route
from utils.datetime_utils import time_diff, sec_to_hour, time_to_str


class MetricsService:
    """Class that contains the Metrics Service to calculate the output of a simulation"""

    def __init__(self):
        """Instantiates the class by creating the DDBB connection"""
        self._connection = create_engine(get_db_url(), pool_size=20, max_overflow=0, pool_pre_ping=True)

    def calculate_and_save_metrics(self, dispatcher: Dispatcher):
        """Method for calculating and saving the simulation metrics"""

        metrics = self._calculate_metrics(dispatcher)
        logging.info(f'Instance {settings.INSTANCE} | Successful metrics calculation.')

        self._save_metrics(metrics)
        self._connection.dispose()
        logging.info(f'Instance {settings.INSTANCE} | Successfully saved metrics to DDBB.')

    def _calculate_metrics(self, dispatcher: Dispatcher) -> List[Metric]:
        """Method for calculating metrics based on the Dispatcher, after the simulation is finished"""

        order_metrics = self._calculate_order_metrics(dispatcher)
        courier_metrics = self._calculate_courier_metrics(dispatcher)
        orders_per_bundle = np.array([
            len(notification.instruction.orders)
            for notification in dispatcher.notifications
            if notification.type == NotificationType.PICK_UP_DROP_OFF and isinstance(notification.instruction, Route)
        ])

        summary_statistics_metrics = self._calculate_summary_statistics_metrics(metrics={
            'click_to_door_time': order_metrics['click_to_door_time'],
            'click_to_door_time_overage': order_metrics['click_to_door_time_overage'],
            'click_to_taken_time': order_metrics['click_to_taken_time'],
            'ready_to_door_time': order_metrics['ready_to_door_time'],
            'ready_to_pickup_time': order_metrics['ready_to_pickup_time'],
            'in_store_to_pickup_time': order_metrics['in_store_to_pickup_time'],
            'drop_off_lateness_time': order_metrics['drop_off_lateness_time'],
            'courier_utilization': courier_metrics['courier_utilization'],
            'courier_delivery_earnings': courier_metrics['courier_delivery_earnings'],
            'courier_compensation': courier_metrics['courier_compensation'],
            'courier_orders_delivered_per_hour': courier_metrics['courier_orders_delivered_per_hour'],
            'courier_bundles_picked_per_hour': courier_metrics['courier_bundles_picked_per_hour'],
            'orders_per_bundle': orders_per_bundle
        })

        cost_per_order = (
            courier_metrics['total_courier_compensation'] / order_metrics['orders_delivered']
            if order_metrics['orders_delivered'] > 0
            else 0.
        )

        value_metrics = [
            Metric(name='orders_delivered', value=order_metrics['orders_delivered']),
            Metric(name='orders_canceled', value=order_metrics['orders_canceled']),
            Metric(name='total_courier_compensation', value=courier_metrics['total_courier_compensation']),
            Metric(name='cost_per_order', value=cost_per_order),
            Metric(
                name='courier_fraction_minimum_compensation',
                value=courier_metrics['courier_fraction_minimum_compensation']
            )
        ]

        return summary_statistics_metrics + value_metrics

    def _save_metrics(self, metrics: List[Metric]):
        """Method for saving the metrics to de DDBB"""

        settings_dict = {
            'DISPATCHER_CANCELLATION_POLICY': settings.DISPATCHER_CANCELLATION_POLICY,
            'DISPATCHER_BUFFERING_POLICY': settings.DISPATCHER_BUFFERING_POLICY,
            'DISPATCHER_MATCHING_POLICY': settings.DISPATCHER_MATCHING_POLICY,
            'DISPATCHER_PREPOSITIONING_POLICY': settings.DISPATCHER_PREPOSITIONING_POLICY,
            'DISPATCHER_PREPOSITIONING_TIMING_POLICY': settings.DISPATCHER_PREPOSITIONING_EVALUATION_POLICY,
            'COURIER_ACCEPTANCE_POLICY': settings.COURIER_ACCEPTANCE_POLICY,
            'COURIER_MOVEMENT_EVALUATION_POLICY': settings.COURIER_MOVEMENT_EVALUATION_POLICY,
            'COURIER_MOVEMENT_POLICY': settings.COURIER_MOVEMENT_POLICY,
            'USER_CANCELLATION_POLICY': settings.USER_CANCELLATION_POLICY,
            'SIMULATE_FROM': time_to_str(settings.SIMULATE_FROM),
            'SIMULATE_UNTIL': time_to_str(settings.SIMULATE_UNTIL),
            'CREATE_USERS_UNTIL': time_to_str(settings.CREATE_USERS_UNTIL),
            'CREATE_COURIERS_UNTIL': time_to_str(settings.CREATE_COURIERS_UNTIL),
            'WARM_UP_TIME': settings.WARM_UP_TIME
        }
        metrics_dict = [
            {
                **metric.to_dict(),
                **{'instance_id': settings.INSTANCE, 'settings': settings_dict}
            }
            for metric in metrics
        ]
        metrics_df = pd.DataFrame(metrics_dict)
        metrics_df.to_sql(
            name='metrics',
            con=self._connection,
            if_exists='append',
            index=False,
            dtype={
                'created_at': DateTime,
                'instance_id': Integer,
                'name': String,
                'value': Float,
                'mean': Float,
                'standard_deviation': Float,
                'minimum': Float,
                'tenth_percentile': Float,
                'median': Float,
                'ninetieth_percentile': Float,
                'maximum': Float,
                'settings': JSON
            }
        )

    @staticmethod
    def _calculate_order_metrics(dispatcher: Dispatcher) -> Dict[str, Union[int, np.ndarray]]:
        """Method to calculate order-based metrics"""

        orders_delivered = len(dispatcher.fulfilled_orders)
        orders_canceled = len(dispatcher.canceled_orders)
        click_to_door_time = np.zeros(orders_delivered)
        click_to_door_time_overage = np.zeros(orders_delivered)
        click_to_taken_time = np.zeros(orders_delivered)
        ready_to_door_time = np.zeros(orders_delivered)
        ready_to_pickup_time = np.zeros(orders_delivered)
        in_store_to_pickup_time = np.zeros(orders_delivered)
        drop_off_lateness_time = np.zeros(orders_delivered)

        for order_ix, order in enumerate(dispatcher.fulfilled_orders.values()):
            click_to_door_time[order_ix] = time_diff(order.drop_off_time, order.placement_time)
            click_to_door_time_overage[order_ix] = (
                    time_diff(order.drop_off_time, order.placement_time) +
                    settings.ORDER_TARGET_DROP_OFF_TIME
            )
            click_to_taken_time[order_ix] = time_diff(order.acceptance_time, order.placement_time)
            ready_to_door_time[order_ix] = time_diff(order.drop_off_time, order.ready_time)
            ready_to_pickup_time[order_ix] = time_diff(order.pick_up_time, order.ready_time)
            in_store_to_pickup_time[order_ix] = time_diff(order.pick_up_time, order.in_store_time)
            drop_off_lateness_time[order_ix] = time_diff(order.drop_off_time, order.expected_drop_off_time)

        return {
            'orders_delivered': orders_delivered,
            'orders_canceled': orders_canceled,
            'click_to_door_time': click_to_door_time,
            'click_to_door_time_overage': click_to_door_time_overage,
            'click_to_taken_time': click_to_taken_time,
            'ready_to_door_time': ready_to_door_time,
            'ready_to_pickup_time': ready_to_pickup_time,
            'in_store_to_pickup_time': in_store_to_pickup_time,
            'drop_off_lateness_time': drop_off_lateness_time
        }

    @staticmethod
    def _calculate_courier_metrics(dispatcher: Dispatcher) -> Dict[str, Union[int, np.ndarray, float]]:
        """Method to calculate courier-based metrics"""

        num_couriers = len(dispatcher.logged_off_couriers)
        courier_utilization = np.zeros(num_couriers)
        courier_delivery_earnings = np.zeros(num_couriers)
        courier_compensation = np.zeros(num_couriers)
        courier_orders_delivered_per_hour = np.zeros(num_couriers)
        courier_bundles_picked_per_hour = np.zeros(num_couriers)

        for courier_ix, courier in enumerate(dispatcher.logged_off_couriers.values()):
            courier_delivery_earnings[courier_ix] = len(courier.fulfilled_orders) * settings.COURIER_EARNINGS_PER_ORDER
            courier_compensation[courier_ix] = courier.earnings

            if time_diff(courier.off_time, courier.on_time) > 0:
                courier_utilization[courier_ix] = (
                        courier.utilization_time /
                        time_diff(courier.off_time, courier.on_time)
                )
                courier_orders_delivered_per_hour[courier_ix] = (
                        len(courier.fulfilled_orders) /
                        sec_to_hour(time_diff(courier.off_time, courier.on_time))
                )
                courier_bundles_picked_per_hour[courier_ix] = (
                        len(courier.accepted_notifications) /
                        sec_to_hour(time_diff(courier.off_time, courier.on_time))
                )

        total_courier_compensation = courier_compensation.sum()
        courier_fraction_minimum_compensation = (
                sum(1 for courier in dispatcher.logged_off_couriers.values() if courier.guaranteed_compensation) /
                num_couriers
        ) if num_couriers > 0 else 0.

        return {
            'num_couriers': num_couriers,
            'courier_utilization': courier_utilization,
            'courier_delivery_earnings': courier_delivery_earnings,
            'courier_compensation': courier_compensation,
            'courier_orders_delivered_per_hour': courier_orders_delivered_per_hour,
            'courier_bundles_picked_per_hour': courier_bundles_picked_per_hour,
            'total_courier_compensation': total_courier_compensation,
            'courier_fraction_minimum_compensation': courier_fraction_minimum_compensation
        }

    @staticmethod
    def _calculate_summary_statistics_metrics(metrics: Dict[str, np.ndarray]) -> List[Metric]:
        """Method to process metrics datasets and obtain the relevant summary statistics"""

        metrics_list = []
        for metric_name, metric_dataset in metrics.items():

            if bool(list(metric_dataset)):
                metrics_list.append(
                    Metric(
                        name=metric_name,
                        dataset=metric_dataset,
                        mean=metric_dataset.mean(),
                        standard_deviation=metric_dataset.std(),
                        minimum=metric_dataset.min(),
                        tenth_percentile=np.percentile(metric_dataset, 10),
                        median=np.median(metric_dataset),
                        ninetieth_percentile=np.percentile(metric_dataset, 90),
                        maximum=metric_dataset.max()
                    )
                )

            else:
                metrics_list.append(
                    Metric(name=metric_name)
                )

        return metrics_list
