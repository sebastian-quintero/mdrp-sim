import random
from dataclasses import dataclass, field
from datetime import time
from typing import Optional, List

from simpy import Environment

import settings
from models.location import Location
from utils.datetime_utils import min_to_sec

MIN_SERVICE_TIME = min_to_sec(2)


@dataclass
class Order:
    """A class used to handle an order's state and events"""

    env: Environment

    order_id: Optional[int] = None
    courier_id: Optional[int] = None
    drop_off_at: Location = None
    rejected_by: List[int] = field(default_factory=lambda: list())
    pick_up_at: Location = None
    state: str = ''

    acceptance_time: Optional[time] = None
    cancellation_time: Optional[time] = None
    drop_off_service_time: Optional[float] = None
    drop_off_time: Optional[time] = None
    expected_drop_off_time: Optional[time] = None
    pick_up_time: Optional[time] = None
    pick_up_service_time: Optional[float] = None
    placement_time: time = None
    preparation_time: Optional[time] = None
    ready_time: Optional[time] = None

    def __post_init__(self):
        """Randomly assigns missing properties immediately after the order is created"""

        self.pick_up_service_time = random.randint(MIN_SERVICE_TIME, settings.ORDER_MAX_PICK_UP_SERVICE_TIME)
        self.drop_off_service_time = random.randint(MIN_SERVICE_TIME, settings.ORDER_MAX_DROP_OFF_SERVICE_TIME)
        self.state = 'unassigned'