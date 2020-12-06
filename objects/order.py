import random
from dataclasses import dataclass, field
from datetime import time
from typing import Optional, List, Any, Dict

from geohash import encode

from objects.location import Location
from settings import settings
from utils.datetime_utils import time_diff


@dataclass
class Order:
    """A class used to handle an order's state and events"""

    order_id: Optional[int] = None
    courier_id: Optional[int] = None
    drop_off_at: Optional[Location] = None
    pick_up_at: Optional[Location] = None
    rejected_by: Optional[List[int]] = field(default_factory=lambda: list())
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

    def calculate_metrics(self) -> Dict[str, Any]:
        """Method to calculate the metrics of an order"""

        dropped_off = bool(self.drop_off_time)

        if dropped_off:
            click_to_door_time = time_diff(self.drop_off_time, self.placement_time)
            click_to_taken_time = time_diff(self.acceptance_time, self.placement_time)
            ready_to_door_time = time_diff(self.drop_off_time, self.ready_time)
            ready_to_pickup_time = time_diff(self.pick_up_time, self.ready_time)
            in_store_to_pickup_time = time_diff(self.pick_up_time, self.in_store_time)
            drop_off_lateness_time = time_diff(self.drop_off_time, self.expected_drop_off_time)
            click_to_cancel_time = None

        else:
            click_to_door_time = None
            click_to_taken_time = None
            ready_to_door_time = None
            ready_to_pickup_time = None
            in_store_to_pickup_time = None
            drop_off_lateness_time = None
            click_to_cancel_time = time_diff(self.cancellation_time, self.preparation_time)

        return {
            'order_id': self.order_id,
            'placement_time': self.placement_time,
            'preparation_time': self.preparation_time,
            'acceptance_time': self.acceptance_time,
            'in_store_time': self.in_store_time,
            'ready_time': self.ready_time,
            'pick_up_time': self.pick_up_time,
            'drop_off_time': self.drop_off_time,
            'expected_drop_off_time': self.expected_drop_off_time,
            'cancellation_time': self.cancellation_time,
            'dropped_off': dropped_off,
            'click_to_door_time': click_to_door_time,
            'click_to_taken_time': click_to_taken_time,
            'ready_to_door_time': ready_to_door_time,
            'ready_to_pick_up_time': ready_to_pickup_time,
            'in_store_to_pick_up_time': in_store_to_pickup_time,
            'drop_off_lateness_time': drop_off_lateness_time,
            'click_to_cancel_time': click_to_cancel_time
        }
