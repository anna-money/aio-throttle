from abc import ABC, abstractmethod
from typing import List, Optional


class ThrottleConsumerQuota(ABC):
    __slots__: List[str] = []

    @abstractmethod
    def accept(self, consumer: str, consumer_capacity: int, capacity_limit: int) -> bool:
        ...


class StaticThrottleConsumerQuota(ThrottleConsumerQuota):
    __slots__ = ["_accept"]

    def __init__(self, accept: bool):
        self._accept = accept

    def accept(self, consumer: str, consumer_capacity: int, capacity_limit: int) -> bool:
        return self._accept


class MaxFractionConsumerQuota(ThrottleConsumerQuota):
    __slots__ = ["_max_fraction", "_consumer"]

    def __init__(self, max_fraction: float, consumer: Optional[str] = None):
        if max_fraction < 0 or max_fraction > 1:
            raise ValueError("MaxFractionConsumerQuota max_faction value must be in [0, 1]")

        self._max_fraction = max_fraction
        self._consumer = consumer

    def accept(self, consumer: str, consumer_used_capacity: int, capacity_limit: int) -> bool:
        if self._consumer is not None and self._consumer != consumer:
            return True

        return (consumer_used_capacity * 1.0 / capacity_limit) <= self._max_fraction
