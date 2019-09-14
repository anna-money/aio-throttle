from abc import ABC, abstractmethod
from typing import List


class ThrottleConsumerQuota(ABC):
    __slots__: List[str] = []

    @abstractmethod
    def accept(self, consumer_capacity: int, capacity_limit: int) -> bool:
        ...


class StaticThrottleConsumerQuota(ThrottleConsumerQuota):
    __slots__ = ["_accept"]

    def __init__(self, accept: bool):
        self._accept = accept

    def accept(self, consumer_capacity: int, capacity_limit: int) -> bool:
        return self._accept
