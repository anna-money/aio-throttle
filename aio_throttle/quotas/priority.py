from abc import ABC, abstractmethod
from enum import Enum
from typing import List


class ThrottlePriority(str, Enum):
    CRITICAL = "critical"
    NORMAL = "normal"
    SHEDDABLE = "sheddable"  # Never put in queue


class ThrottlePriorityQuota(ABC):
    __slots__: List[str] = []

    @abstractmethod
    def can_be_accepted(self, priority: ThrottlePriority, priority_capacity_used: int, capacity_limit: int) -> bool:
        ...


class CompositePriorityQuota(ThrottlePriorityQuota):
    __slots__ = ["_quotas"]

    def __init__(self, quotas: List[ThrottlePriorityQuota]):
        self._quotas = quotas

    def can_be_accepted(self, priority: ThrottlePriority, priority_capacity_used: int, capacity_limit: int) -> bool:
        for quota in self._quotas:
            if not quota.can_be_accepted(priority, priority_capacity_used, capacity_limit):
                return False
        return True


class MaxFractionPriorityQuota(ThrottlePriorityQuota):
    __slots__ = ["_max_fraction", "_priority"]

    def __init__(self, max_fraction: float, priority: ThrottlePriority = ThrottlePriority.SHEDDABLE):
        self._max_fraction = max_fraction
        self._priority = priority

    def can_be_accepted(self, priority: ThrottlePriority, priority_used_capacity: int, capacity_limit: int) -> bool:
        if priority != self._priority:
            return True
        return (priority_used_capacity * 1.0 / capacity_limit) <= self._max_fraction
