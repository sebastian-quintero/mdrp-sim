import math
from datetime import time, datetime, date, timedelta
from typing import Union


def min_to_sec(minutes: float) -> Union[float, int]:
    """Convert minutes to seconds"""

    return minutes * 60


def hour_to_sec(hours: float) -> Union[float, int]:
    """Convert hours to seconds"""

    return hours * 3600


def sec_to_hour(seconds: float) -> float:
    """Convert seconds to hours"""

    return seconds / 3600


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


def time_to_sec(raw_time: time) -> Union[float, int]:
    """Convert time object to seconds"""

    return hour_to_sec(raw_time.hour) + min_to_sec(raw_time.minute) + raw_time.second


def time_to_query_format(query_time: time) -> str:
    """Parse a time object to a str available to use in a query"""

    return f'\'{query_time.hour}:{query_time.minute}:{query_time.second}\''


def time_diff(time_1: time, time_2: time) -> float:
    """Returns the difference in seconds of time_1 - time_2"""

    diff = datetime.combine(date.today(), time_1) - datetime.combine(date.today(), time_2)

    return diff.total_seconds()


def time_add(time_to_add: time, seconds: float) -> time:
    """Adds the desired seconds to the time provided"""

    return (datetime.combine(date.today(), time_to_add) + timedelta(seconds=seconds)).time()
