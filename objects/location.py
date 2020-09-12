from dataclasses import dataclass
from typing import Tuple


@dataclass
class Location:
    lat: float
    lng: float

    @property
    def coordinates(self) -> Tuple[float, float]:
        return self.lat, self.lng
