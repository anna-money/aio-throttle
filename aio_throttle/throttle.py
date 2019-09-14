from collections import defaultdict
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import AsyncIterator, Optional, DefaultDict, Mapping

from .internals import LifoSemaphore
from .quotas import ThrottleConsumerQuota, StaticConsumerQuota


@dataclass(frozen=True)
class ThrottleRequest:
    __slots__ = ["consumer"]

    consumer: str


@dataclass(frozen=True)
class ThrottleResponse:
    __slots__ = ["accepted"]

    accepted: bool


@dataclass(frozen=True)
class ThrottleStats:
    __slots__ = ["available", "queued", "consumers_used_capacity"]

    available: int
    queued: int
    consumers_used_capacity: Mapping[str, int]


class Throttler:
    __slots__ = ["_semaphore", "_queue_limit", "_capacity_limit", "_consumers_used_capacity", "_consumer_quota"]

    def __init__(
        self, capacity_limit: int, queue_limit: int = 0, consumer_quota: Optional[ThrottleConsumerQuota] = None
    ):
        if capacity_limit < 1:
            raise ValueError("Throttler capacity_limit value must be >= 1")
        if queue_limit < 0:
            raise ValueError("Throttler queue limit must be >= 0")

        self._capacity_limit: int = capacity_limit
        self._queue_limit: int = queue_limit
        self._semaphore: LifoSemaphore = LifoSemaphore(capacity_limit)
        self._consumers_used_capacity: DefaultDict[str, int] = defaultdict(int)
        self._consumer_quota = consumer_quota or StaticConsumerQuota(True)

    def _try_accept_quotas(self, request: Optional[ThrottleRequest] = None) -> bool:
        if request is None:
            return True

        consumer_used = self._consumers_used_capacity[request.consumer]
        return self._consumer_quota.accept(request.consumer, consumer_used, self._capacity_limit)

    def _increment_counters(self, request: Optional[ThrottleRequest]) -> None:
        if request is None:
            return

        self._consumers_used_capacity[request.consumer] += 1

    def _decrement_counters(self, request: Optional[ThrottleRequest]) -> None:
        if request is None:
            return

        self._consumers_used_capacity[request.consumer] -= 1

    @property
    def stats(self) -> ThrottleStats:
        return ThrottleStats(self._semaphore.available, self._semaphore.waiting, self._consumers_used_capacity)

    @asynccontextmanager
    async def throttle(self, request: Optional[ThrottleRequest] = None) -> AsyncIterator[ThrottleResponse]:
        acquired_no_wait = self._semaphore.acquire_no_wait()
        if acquired_no_wait:
            try:
                self._increment_counters(request)
                yield ThrottleResponse(True)
            finally:
                self._decrement_counters(request)
                self._semaphore.release()
        elif self._semaphore.waiting >= self._queue_limit or not self._try_accept_quotas(request):
            yield ThrottleResponse(False)
        else:
            await self._semaphore.acquire()
            accepted = self._try_accept_quotas(request)
            try:
                if accepted:
                    self._increment_counters(request)
                yield ThrottleResponse(accepted)
            finally:
                if accepted:
                    self._decrement_counters(request)
                self._semaphore.release()
