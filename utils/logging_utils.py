import logging
import sys

from simpy import Environment

from settings import settings
from utils.datetime_utils import sec_to_time

LOG_PATTERN = '[%(asctime)s][%(levelname)s] | %(message)s '
LOG_DATE_PATTERN = '%Y-%m-%d %H:%M:%S'


def configure_logs():
    """Method to configure the structure of a log"""

    logging.basicConfig(
        format=LOG_PATTERN,
        level=logging.INFO,
        datefmt=LOG_DATE_PATTERN,
        stream=sys.stdout
    )


def log(env: Environment, actor_name: str, condition: str, msg: str):
    """Method to handle how an info log is shown"""

    if settings.VERBOSE_LOGS:
        logging.info(f'sim time = {sec_to_time(env.now)} | actor = {actor_name} (condition = {condition}) | {msg}')


def world_log(dispatcher) -> str:
    """Method to log the state of the world"""

    return f'| Couriers => ' \
           f'{len(dispatcher.idle_couriers)} idle, ' \
           f'{len(dispatcher.moving_couriers)} moving, ' \
           f'{len(dispatcher.picking_up_couriers)} picking_up, ' \
           f'{len(dispatcher.dropping_off_couriers)} dropping_off, ' \
           f'{len(dispatcher.logged_off_couriers)} logged_off. ' \
           f'| Orders => ' \
           f'{len(dispatcher.placed_orders)} placed, ' \
           f'{len(dispatcher.unassigned_orders)} unassigned, ' \
           f'{len(dispatcher.assigned_orders)} assigned, ' \
           f'{len(dispatcher.fulfilled_orders)} fulfilled, ' \
           f'{len(dispatcher.canceled_orders)} canceled. '
