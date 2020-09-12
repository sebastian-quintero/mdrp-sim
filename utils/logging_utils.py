import logging

from simpy import Environment

import settings
from utils.datetime_utils import sec_to_time

LOG_PATTERN = '[%(asctime)s][%(levelname)s] | %(message)s '
LOG_DATE_PATTERN = '%Y-%m-%d %H:%M:%S'


def configure_logs():
    """Method to configure the structure of a log"""

    logging.basicConfig(
        format=LOG_PATTERN,
        level=logging.INFO,
        datefmt=LOG_DATE_PATTERN,
    )


def log(env: Environment, actor_name: str, state: str, msg: str):
    """Method to handle how an info log is shown"""

    if settings.VERBOSE_LOGS:
        logging.info(f'sim time = {sec_to_time(env.now)} | actor = {actor_name} (state = {state}) | {msg}')
