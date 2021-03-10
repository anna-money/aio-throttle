import asyncio

from typing import List


class LifoSemaphore:
    __slots__ = ("_limit", "_available", "_waiters", "_loop")

    def __init__(self, initial: int = 1) -> None:
        if initial < 1:
            raise ValueError("LifoSemaphore initial value must be >= 0")
        self._limit = initial
        self._available = initial
        self._waiters: List[asyncio.Future[None]] = []
        self._loop = asyncio.get_event_loop()

    def _wake_up_next(self) -> None:
        while self._waiters:
            waiter = self._waiters.pop()
            if not waiter.done():
                waiter.set_result(None)
                return

    @property
    def available(self) -> int:
        return self._available

    @property
    def waiting(self) -> int:
        return len(self._waiters)

    def acquire_no_wait(self) -> bool:
        if self._available <= 0:
            return False

        self._available -= 1
        return True

    async def acquire(self) -> None:
        while self._available <= 0:
            future = self._loop.create_future()
            self._waiters.append(future)
            try:
                await future
            except:  # noqa
                future.cancel()
                if self._available > 0 and not future.cancelled():
                    self._wake_up_next()
                raise
        self._available -= 1
        return

    def release(self) -> None:
        if self._available >= self._limit:
            raise ValueError("LifoSemaphore released too many times")
        self._available += 1
        self._wake_up_next()
