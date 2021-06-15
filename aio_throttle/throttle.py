import contextlib
from typing import AsyncIterator, Optional, List, Dict

from .base import ThrottlePriority, ThrottleResult, ThrottleStats
from .internals import LifoSemaphore
from .metrics import MetricsProvider, NOOP_METRICS_PROVIDER
from .quotas import ThrottleCapacityQuota, CompositeThrottleCapacityQuota, ThrottleQuota, CompositeThrottleQuota
from .utils import increment_counter, decrement_counter


class Throttler:
    __slots__ = (
        "_semaphore",
        "_queue_limit",
        "_capacity_limit",
        "_consumers_used_capacity",
        "_consumer_quota",
        "_priority_quota",
        "_priorities_used_capacity",
        "_quota",
        "_metrics_provider",
    )

    def __init__(
        self,
        capacity_limit: int,
        queue_limit: int = 0,
        consumer_quotas: Optional[List[ThrottleCapacityQuota[str]]] = None,
        priority_quotas: Optional[List[ThrottleCapacityQuota[ThrottlePriority]]] = None,
        quotas: Optional[List[ThrottleQuota]] = None,
        metrics_provider: MetricsProvider = NOOP_METRICS_PROVIDER,
    ):
        if capacity_limit < 1:
            raise ValueError("Throttler capacity_limit value must be >= 1")
        if queue_limit < 0:
            raise ValueError("Throttler queue limit must be >= 0")

        self._capacity_limit: int = capacity_limit
        self._queue_limit: int = queue_limit
        self._semaphore: LifoSemaphore = LifoSemaphore(capacity_limit)
        self._consumers_used_capacity: Dict[str, int] = {}
        self._consumer_quota = CompositeThrottleCapacityQuota(consumer_quotas or [])
        self._priorities_used_capacity: Dict[ThrottlePriority, int] = {}
        self._priority_quota = CompositeThrottleCapacityQuota(priority_quotas or [])
        self._quota = CompositeThrottleQuota(quotas or [])
        self._metrics_provider = metrics_provider

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

    @contextlib.asynccontextmanager
    async def throttle(
        self, *, consumer: Optional[str] = None, priority: Optional[ThrottlePriority] = None
    ) -> AsyncIterator[ThrottleResult]:
        check_queue_and_quotas_result = self._check_queue(priority) and self._check_quotas(consumer, priority)
        if not check_queue_and_quotas_result:
            self._capture_throttled_request_metric(consumer, priority, check_queue_and_quotas_result)
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
                    self._capture_throttled_request_metric(consumer, priority, check_queue_and_quotas_result)
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

    def _capture_throttled_request_metric(
        self,
        consumer: Optional[str],
        priority: Optional[ThrottlePriority],
        result: ThrottleResult,
    ) -> None:
        tags: Dict[str, str] = {}
        if consumer is not None:
            tags["consumer"] = consumer
        if priority is not None:
            tags["priority"] = str(priority)
        tags["result"] = str(result)

        self._metrics_provider.increment_counter("aio_throttle_requests", tags)

    def _check_quotas(
        self, consumer: Optional[str] = None, priority: Optional[ThrottlePriority] = None
    ) -> ThrottleResult:
        if not self._quota.can_be_accepted():
            return ThrottleResult.REJECTED_DUE_TO_QUOTA

        if priority is not None:
            priority_used_capacity = self._priorities_used_capacity.get(priority, 0)
            if not self._priority_quota.can_be_accepted(priority, priority_used_capacity + 1, self._capacity_limit):
                return ThrottleResult.REJECTED_DUE_TO_PRIORITY_QUOTA
        if consumer is not None:
            consumer_used_capacity = self._consumers_used_capacity.get(consumer, 0)
            if not self._consumer_quota.can_be_accepted(consumer, consumer_used_capacity + 1, self._capacity_limit):
                return ThrottleResult.REJECTED_DUE_TO_CONSUMER_QUOTA
        return ThrottleResult.ACCEPTED

    def _check_queue(self, priority: Optional[ThrottlePriority] = None) -> ThrottleResult:
        queue_size = self._semaphore.waiting
        if queue_size > 0 and priority == ThrottlePriority.LOW:
            return ThrottleResult.REJECTED_DUE_TO_FULL_QUEUE
        if queue_size >= self._queue_limit and self._semaphore.available == 0:
            return ThrottleResult.REJECTED_DUE_TO_FULL_QUEUE
        return ThrottleResult.ACCEPTED

    def _increment_counters(self, consumer: Optional[str] = None, priority: Optional[ThrottlePriority] = None) -> None:
        if priority is not None:
            increment_counter(self._priorities_used_capacity, priority)
        if consumer is not None:
            increment_counter(self._consumers_used_capacity, consumer)

    def _decrement_counters(self, consumer: Optional[str] = None, priority: Optional[ThrottlePriority] = None) -> None:
        if consumer is not None:
            decrement_counter(self._consumers_used_capacity, consumer)
        if priority is not None:
            decrement_counter(self._priorities_used_capacity, priority)

    def _acquire_capacity_slot_no_wait(self) -> bool:
        return self._semaphore.acquire_no_wait()

    async def _acquire_capacity_slot(self) -> None:
        await self._semaphore.acquire()

    def _release_capacity_slot(self) -> None:
        self._semaphore.release()
