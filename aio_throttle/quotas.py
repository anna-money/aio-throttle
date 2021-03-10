import abc
import random
from typing import TypeVar, Generic, List, Optional, Any

TResource = TypeVar("TResource")


class ThrottleCapacityQuota(Generic[TResource]):
    __slots__ = ()

    @abc.abstractmethod
    def can_be_accepted(self, resource: TResource, capacity_used: int, capacity_limit: int) -> bool:
        ...


class CompositeThrottleCapacityQuota(ThrottleCapacityQuota[TResource]):
    __slots__ = ("_quotas",)

    def __init__(self, quotas: List[ThrottleCapacityQuota[TResource]]):
        self._quotas = quotas

    def can_be_accepted(self, resource: TResource, capacity_used: int, capacity_limit: int) -> bool:
        for quota in self._quotas:
            if not quota.can_be_accepted(resource, capacity_used, capacity_limit):
                return False
        return True


class MaxFractionCapacityQuota(ThrottleCapacityQuota[TResource]):
    __slots__ = ("_max_fraction", "_matched_resource")

    def __init__(self, max_fraction: float, resource: Optional[TResource] = None):
        if max_fraction < 0 or max_fraction > 1:
            raise ValueError("MaxFractionCapacityQuota max_fraction value must be in range [0, 1]")

        self._matched_resource = resource
        self._max_fraction = max_fraction

    def can_be_accepted(self, resource: TResource, used_capacity: int, capacity_limit: int) -> bool:
        if self._matched_resource is not None and resource != self._matched_resource:
            return True
        return (used_capacity * 1.0 / capacity_limit) <= self._max_fraction


class ThrottleQuota(abc.ABC):
    __slots__ = ()

    @abc.abstractmethod
    def can_be_accepted(self) -> bool:
        ...


class CompositeThrottleQuota(ThrottleQuota):
    __slots__ = ("_quotas",)

    def __init__(self, quotas: List[ThrottleQuota]):
        self._quotas = quotas

    def can_be_accepted(self) -> bool:
        for quota in self._quotas:
            if not quota.can_be_accepted():
                return False
        return True


class RandomRejectThrottleQuota(ThrottleQuota):
    __slots__ = ("_reject_probability", "_random")

    def __init__(self, reject_probability: float, seed: Any = None):
        if reject_probability < 0 or reject_probability > 1:
            raise ValueError("MaxFractionCapacityQuota max_fraction value must be in range [0, 1]")

        self._reject_probability = reject_probability
        self._random = random.Random(seed)

    def can_be_accepted(self) -> bool:
        return self._reject_probability == 0 or self._random.random() < self._reject_probability
