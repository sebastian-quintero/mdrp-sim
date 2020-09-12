import math
from datetime import time
from typing import Union


def min_to_sec(minutes: float) -> float:
    """Convert minutes to seconds"""

    return minutes * 60


def hour_to_sec(hours: float) -> Union[float, int]:
    """Convert hours to seconds"""

    return hours * 3600


def sec_to_time(seconds: int) -> time:
    """Convert seconds since the day started to a time object"""

    def next_precision_frac(interval: float) -> float:
        """Convert time interval to fractional next precision"""

        return round(math.modf(interval)[0] * 60, 4)

    def next_precision(interval: float) -> int:
        """Convert fractional time interval to next precision"""

        return min(round(next_precision_frac(interval)), 59)

    raw_hours = seconds / 3600

    return time(
        hour=math.floor(raw_hours),
        minute=next_precision(raw_hours),
        second=next_precision(next_precision_frac(raw_hours))
    )
