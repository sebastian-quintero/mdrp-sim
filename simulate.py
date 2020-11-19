import random

from simpy import Environment

import settings
from actors.world import World
from services.metrics_service import MetricsService
from utils.datetime_utils import time_to_sec
from utils.logging_utils import configure_logs

if __name__ == '__main__':
    """Main method for running the mdrp-sim"""

    configure_logs()

    for instance in settings.INSTANCES:
        random.seed(settings.SEED)

        env = Environment(initial_time=time_to_sec(settings.SIMULATE_FROM))
        world = World(env=env, instance=instance)
        env.run(until=time_to_sec(settings.SIMULATE_UNTIL))
        world.post_process()

        metrics_service = MetricsService(instance=instance)
        metrics_service.calculate_and_save_metrics(world.dispatcher)
