import logging
import os

import pandas as pd
from sqlalchemy import create_engine, Integer, Float, Time, String

from ddbb.config import get_db_url, run_db_migrations
from utils.logging_utils import configure_logs

PROJECT_PATH = os.getcwd()
INSTANCES_DIR_PATH = f'{PROJECT_PATH}/instances'
INSTANCES_SUB_DIR_PATH = INSTANCES_DIR_PATH + '/{instance_id}'
ORDERS_CSV_FILE = 'orders.csv'
COURIERS_CSV_FILE = 'couriers.csv'

if __name__ == '__main__':
    """Method to load .csv instances to local DDBB for fast processing"""

    configure_logs()
    run_db_migrations()

    connection = create_engine(get_db_url(), pool_size=20, max_overflow=0, pool_pre_ping=True)
    logging.info('Successfully created DDBB connection.')

    instances = os.listdir(INSTANCES_DIR_PATH)
    instances = [instance for instance in instances if instance != '.DS_Store']
    logging.info(f'Start loading data to local DDBB for {len(instances)} instances.')

    for instance in instances:
        sub_dir = INSTANCES_SUB_DIR_PATH.format(instance_id=instance)
        orders_file = f'{sub_dir}/{ORDERS_CSV_FILE}'
        couriers_file = f'{sub_dir}/{COURIERS_CSV_FILE}'
        logging.info(f'Instance {instance} | Successfully read orders and couriers files.')

        orders_df = pd.read_csv(orders_file)
        orders_df['instance_id'] = instance
        logging.info(
            f'Instance {instance} | Successfully obtained orders DF with these columns: '
            f'{orders_df.columns.tolist()}.'
        )

        couriers_df = pd.read_csv(couriers_file)
        couriers_df['instance_id'] = instance
        logging.info(
            f'Instance {instance} | Successfully obtained couriers DF with these columns: '
            f'{couriers_df.columns.tolist()}.'
        )

        orders_df.to_sql(
            name='orders_instance_data',
            con=connection,
            if_exists='append',
            index=False,
            dtype={
                'instance_id': Integer,
                'order_id': Integer,
                'pick_up_lat': Float,
                'pick_up_lng': Float,
                'drop_off_lat': Float,
                'drop_off_lng': Float,
                'placement_time': Time,
                'preparation_time': Time,
                'ready_time': Time,
                'expected_drop_off_time': Time
            }
        )
        logging.info(f'Instance {instance} | Successfully transferred orders DF to SQL table.')

        couriers_df.to_sql(
            name='couriers_instance_data',
            con=connection,
            if_exists='append',
            index=False,
            dtype={
                'instance_id': Integer,
                'courier_id': Integer,
                'vehicle': String,
                'on_lat': Float,
                'on_lng': Float,
                'on_time': Time,
                'off_time': Time
            }
        )
        logging.info(f'Instance {instance} | Successfully transferred couriers DF to SQL table.')

    connection.dispose()
    logging.info('Successfully finished loading instances and disposed of DDBB connection.')
