import random
from dataclasses import dataclass, field
from datetime import time
from typing import Optional, List, Any

from geohash import encode

import settings
from objects.location import Location


@dataclass
class Order:
    """A class used to handle an order's state and events"""

    order_id: Optional[int] = None
    courier_id: Optional[int] = None
    drop_off_at: Optional[Location] = None
    rejected_by: Optional[List[int]] = field(default_factory=lambda: list())
    pick_up_at: Optional[Location] = None
    state: Optional[str] = ''
    user: Optional[Any] = None

    acceptance_time: Optional[time] = None
    cancellation_time: Optional[time] = None
    drop_off_service_time: Optional[float] = None
    drop_off_time: Optional[time] = None
    expected_drop_off_time: Optional[time] = None
    geohash: Optional[str] = None
    in_store_time: Optional[time] = None
    pick_up_time: Optional[time] = None
    pick_up_service_time: Optional[float] = None
    placement_time: Optional[time] = None
    preparation_time: Optional[time] = None
    ready_time: Optional[time] = None

    def __post_init__(self):
        """Randomly assigns missing properties immediately after the order is created and other initializations"""

        self.pick_up_service_time = random.randint(
            settings.ORDER_MIN_SERVICE_TIME,
            settings.ORDER_MAX_PICK_UP_SERVICE_TIME
        ) if self.pick_up_service_time is None else self.pick_up_service_time
        self.drop_off_service_time = random.randint(
            settings.ORDER_MIN_SERVICE_TIME,
            settings.ORDER_MAX_DROP_OFF_SERVICE_TIME
        ) if self.drop_off_service_time is None else self.drop_off_service_time
        self.state = 'unassigned'
        self.geohash = (
            encode(self.pick_up_at.lat, self.pick_up_at.lng, settings.DISPATCHER_GEOHASH_PRECISION_GROUPING)
            if self.pick_up_at is not None
            else ''
        )
