from abc import ABC, abstractmethod
from collections import defaultdict
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import AsyncIterator, Optional, DefaultDict, List, Mapping

from .internals import LifoSemaphore


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
    __slots__ = ["available", "queued", "by_consumers"]

    available: int
    queued: int
    by_consumers: Mapping[str, int]


class Throttler:
    __slots__ = ["_semaphore", "_queue_limit", "_capacity_limit", "_consumers_requests", "_consumer_quota"]

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
        self._consumers_requests: DefaultDict[str, int] = defaultdict(int)
        self._consumer_quota = consumer_quota or StaticThrottleConsumerQuota(True)

    def _try_accept_quotas(self, request: Optional[ThrottleRequest] = None) -> bool:
        if request is None:
            return True

        consumer_used = self._consumers_requests[request.consumer]
        return self._consumer_quota.accept(consumer_used, self._capacity_limit)

    def _increment_counters(self, request: Optional[ThrottleRequest]) -> None:
        if request is None:
            return

        self._consumers_requests[request.consumer] += 1

    def _decrement_counters(self, request: Optional[ThrottleRequest]) -> None:
        if request is None:
            return

        self._consumers_requests[request.consumer] -= 1

    @property
    def stats(self) -> ThrottleStats:
        return ThrottleStats(self._semaphore.available, self._semaphore.waiting, self._consumers_requests)

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
        elif self._semaphore.waiting >= self._queue_limit:
            yield ThrottleResponse(False)
        elif not self._try_accept_quotas(request):
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
