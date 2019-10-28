from collections import defaultdict
from contextlib import asynccontextmanager
from dataclasses import dataclass
from enum import Enum
from typing import AsyncIterator, Optional, DefaultDict, Mapping, List

from .quotas import ThrottleCapacityQuota, CompositeThrottleCapacityQuota, ThrottleQuota, CompositeThrottleQuota
from .internals import LifoSemaphore


class ThrottlePriority(str, Enum):
    CRITICAL = "critical"
    NORMAL = "normal"
    SHEDDABLE = "sheddable"


class ThrottleResult(str, Enum):
    ACCEPTED = "Accepted"
    REJECTED_FULL_QUEUE = "Rejected due because the queue is full"
    REJECTED_PRIORITY_QUOTA = "Rejected by a priority quota"
    REJECTED_CONSUMER_QUOTA = "Rejected by a consumer quota"
    REJECTED_QUOTA = "Rejected by a quota"

    def __bool__(self) -> bool:
        return self == self.ACCEPTED


@dataclass(frozen=True)
class ThrottleStats:
    __slots__ = [
        "available_capacity",
        "capacity_limit",
        "queue_size",
        "queue_limit",
        "consumers_used_capacity",
        "priorities_used_capacity",
    ]

    available_capacity: int
    capacity_limit: int
    queue_size: int
    queue_limit: int
    consumers_used_capacity: Mapping[str, int]
    priorities_used_capacity: Mapping[ThrottlePriority, int]


class Throttler:
    __slots__ = [
        "_semaphore",
        "_queue_limit",
        "_capacity_limit",
        "_consumers_used_capacity",
        "_consumer_quota",
        "_priority_quota",
        "_priorities_used_capacity",
        "_quota",
    ]

    def __init__(
        self,
        capacity_limit: int,
        queue_limit: int = 0,
        consumer_quotas: Optional[List[ThrottleCapacityQuota[str]]] = None,
        priority_quotas: Optional[List[ThrottleCapacityQuota[ThrottlePriority]]] = None,
        quotas: Optional[List[ThrottleQuota]] = None,
    ):
        if capacity_limit < 1:
            raise ValueError("Throttler capacity_limit value must be >= 1")
        if queue_limit < 0:
            raise ValueError("Throttler queue limit must be >= 0")

        self._capacity_limit: int = capacity_limit
        self._queue_limit: int = queue_limit
        self._semaphore: LifoSemaphore = LifoSemaphore(capacity_limit)
        self._consumers_used_capacity: DefaultDict[str, int] = defaultdict(int)
        self._consumer_quota = CompositeThrottleCapacityQuota(consumer_quotas or [])
        self._priorities_used_capacity: DefaultDict[ThrottlePriority, int] = defaultdict(int)
        self._priority_quota = CompositeThrottleCapacityQuota(priority_quotas or [])
        self._quota = CompositeThrottleQuota(quotas or [])

    def _check_quotas(
        self, consumer: Optional[str] = None, priority: Optional[ThrottlePriority] = None
    ) -> ThrottleResult:
        if not self._quota.can_be_accepted():
            return ThrottleResult.REJECTED_QUOTA

        if priority is not None:
            priority_used_capacity = self._priorities_used_capacity[priority]
            if not self._priority_quota.can_be_accepted(priority, priority_used_capacity + 1, self._capacity_limit):
                return ThrottleResult.REJECTED_PRIORITY_QUOTA
        if consumer is not None:
            consumer_used_capacity = self._consumers_used_capacity[consumer]
            if not self._consumer_quota.can_be_accepted(consumer, consumer_used_capacity + 1, self._capacity_limit):
                return ThrottleResult.REJECTED_CONSUMER_QUOTA
        return ThrottleResult.ACCEPTED

    def _check_queue(self, priority: Optional[ThrottlePriority] = None) -> ThrottleResult:
        queue_size = self._semaphore.waiting
        if queue_size > 0 and priority == ThrottlePriority.SHEDDABLE:
            return ThrottleResult.REJECTED_FULL_QUEUE
        if queue_size >= self._queue_limit and self._semaphore.available == 0:
            return ThrottleResult.REJECTED_FULL_QUEUE
        return ThrottleResult.ACCEPTED

    def _increment_counters(self, consumer: Optional[str] = None, priority: Optional[ThrottlePriority] = None) -> None:
        if priority is not None:
            self._priorities_used_capacity[priority] += 1
        if consumer is not None:
            self._consumers_used_capacity[consumer] += 1

    def _decrement_counters(self, consumer: Optional[str] = None, priority: Optional[ThrottlePriority] = None) -> None:
        if consumer is not None:
            self._consumers_used_capacity[consumer] -= 1
        if priority is not None:
            self._priorities_used_capacity[priority] -= 1

    def _acquire_capacity_slot_no_wait(self) -> bool:
        return self._semaphore.acquire_no_wait()

    async def _acquire_capacity_slot(self) -> None:
        await self._semaphore.acquire()

    def _release_capacity_slot(self) -> None:
        self._semaphore.release()

    @property
    def stats(self) -> ThrottleStats:
        return ThrottleStats(
            self._semaphore.available,
            self._capacity_limit,
            self._semaphore.waiting,
            self._queue_limit,
            self._consumers_used_capacity,
            self._priorities_used_capacity,
        )

    @asynccontextmanager
    async def throttle(
        self, consumer: Optional[str] = None, priority: Optional[ThrottlePriority] = None
    ) -> AsyncIterator[ThrottleResult]:
        check_queue_and_quotas_result = self._check_queue(priority) and self._check_quotas(consumer, priority)
        if not check_queue_and_quotas_result:
            yield check_queue_and_quotas_result
        elif self._acquire_capacity_slot_no_wait():
            try:
                self._increment_counters(consumer, priority)
                yield ThrottleResult.ACCEPTED
            finally:
                self._decrement_counters(consumer, priority)
                self._release_capacity_slot()
        else:
            await self._acquire_capacity_slot()
            check_quota_result = self._check_quotas(consumer, priority)
            if not check_quota_result:
                try:
                    yield check_quota_result
                finally:
                    self._release_capacity_slot()
            else:
                try:
                    self._increment_counters(consumer, priority)
                    yield ThrottleResult.ACCEPTED
                finally:
                    self._decrement_counters(consumer, priority)
                    self._release_capacity_slot()
