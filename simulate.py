import logging
import random

from simpy import Environment

import settings
from actors.world import World
from services.metrics_service import MetricsService
from utils.datetime_utils import time_to_sec, sec_to_time
from utils.logging_utils import configure_logs

if __name__ == '__main__':
    """Main method for running the mdrp-sim"""

    configure_logs()
    random.seed(settings.SEED)

    env = Environment(initial_time=time_to_sec(settings.SIMULATE_FROM))
    world = World(env=env)
    env.run(until=time_to_sec(settings.SIMULATE_UNTIL))
    logging.info(f'Instance {settings.INSTANCE} | Simulation finished at sim time = {sec_to_time(env.now)}.')

    metrics_service = MetricsService()
    metrics = metrics_service.calculate_and_save_metrics(world.dispatcher)
