from abc import ABC, abstractmethod
from typing import List, Optional


class ThrottleConsumerQuota(ABC):
    __slots__: List[str] = []

    @abstractmethod
    def can_be_accepted(self, consumer: str, consumer_capacity: int, capacity_limit: int) -> bool:
        ...


class StaticConsumerQuota(ThrottleConsumerQuota):
    __slots__ = ["_accept"]

    def __init__(self, accept: bool):
        self._accept = accept

    def can_be_accepted(self, consumer: str, consumer_capacity: int, capacity_limit: int) -> bool:
        return self._accept


class CompositeConsumerQuota(ThrottleConsumerQuota):
    __slots__ = ["_quotas"]

    def __init__(self, quotas: List[ThrottleConsumerQuota]):
        self._quotas = quotas

    def can_be_accepted(self, consumer: str, consumer_capacity: int, capacity_limit: int) -> bool:
        for quota in self._quotas:
            if not quota.can_be_accepted(consumer, consumer_capacity, capacity_limit):
                return False
        return True


class MaxFractionConsumerQuota(ThrottleConsumerQuota):
    __slots__ = ["_max_fraction", "_consumer"]

    def __init__(self, max_fraction: float, consumer: Optional[str] = None):
        if max_fraction < 0 or max_fraction > 1:
            raise ValueError("MaxFractionConsumerQuota max_fraction value must be in range [0, 1]")

        self._max_fraction = max_fraction
        self._consumer = consumer

    def can_be_accepted(self, consumer: str, consumer_used_capacity: int, capacity_limit: int) -> bool:
        if self._consumer is not None and self._consumer != consumer:
            return True

        return (consumer_used_capacity * 1.0 / capacity_limit) <= self._max_fraction
