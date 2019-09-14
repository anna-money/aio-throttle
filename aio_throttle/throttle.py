from contextlib import asynccontextmanager
from typing import AsyncIterator

from .internals import LifoSemaphore


class ThrottleResult:
    __slots__ = ["_accepted"]

    def __init__(self, accepted: bool):
        self._accepted = accepted

    @property
    def accepted(self) -> bool:
        return self._accepted


class Throttler:
    __slots__ = ["_semaphore", "_queue_limit", "_capacity_limit"]

    def __init__(self, capacity_limit: int, queue_limit: int = 0):
        if capacity_limit < 1:
            raise ValueError("Throttler capacity_limit value must be >= 1")
        if queue_limit < 0:
            raise ValueError("Throttler queue limit must be >= 0")

        self._capacity_limit: int = capacity_limit
        self._queue_limit: int = queue_limit
        self._semaphore: LifoSemaphore = LifoSemaphore(capacity_limit)

    @asynccontextmanager
    async def throttle(self) -> AsyncIterator[ThrottleResult]:
        acquired_no_wait = self._semaphore.acquire_no_wait()
        if acquired_no_wait:
            try:
                yield ThrottleResult(True)
            finally:
                self._semaphore.release()
        elif self._semaphore.waiting >= self._queue_limit:
            yield ThrottleResult(False)
        else:
            await self._semaphore.acquire()
            try:
                yield ThrottleResult(True)
            finally:
                self._semaphore.release()
