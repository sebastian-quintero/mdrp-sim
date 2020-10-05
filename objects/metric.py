from dataclasses import dataclass
from typing import Optional, Union, Dict

import numpy as np


@dataclass
class Metric:
    """Class that defines the structure of a metric, this is, a set of data"""

    name: str
    value: Optional[Union[int, float]] = None
    dataset: Optional[np.ndarray] = None
    mean: Optional[float] = None
    standard_deviation: Optional[float] = None
    minimum: Optional[float] = None
    tenth_percentile: Optional[float] = None
    median: Optional[float] = None
    ninetieth_percentile: Optional[float] = None
    maximum: Optional[float] = None

    def to_dict(self) -> Dict[str, Union[str, int, float]]:
        """Method to convert a metric to a dictionary"""

        return {
            k: round(v, 2) if isinstance(v, float) else v
            for k, v in self.__dict__.items()
            if k != 'dataset'
        }
