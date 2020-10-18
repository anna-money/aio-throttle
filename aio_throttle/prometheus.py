from contextlib import asynccontextmanager
from typing import Optional, AsyncIterator, Callable

from prometheus_client import Counter

from .abc import ThrottlerBase, ThrottlePriority, ThrottleResult, ThrottleStats

__all__ = ["prometheus_aware_throttler", "PrometheusAwareThrottler"]


def prometheus_aware_throttler(*, throttle_result_counter: Counter,) -> Callable[[ThrottlerBase], ThrottlerBase]:
    def wrap(throttler: ThrottlerBase) -> ThrottlerBase:
        return PrometheusAwareThrottler(throttler, throttle_result_counter=throttle_result_counter)

    return wrap


class PrometheusAwareThrottler(ThrottlerBase):
    __slots__ = ("_throttler", "_throttle_result_counter")

    def __init__(
        self, throttler: ThrottlerBase, *, throttle_result_counter: Counter,
    ):
        self._throttler = throttler
        self._throttle_result_counter = throttle_result_counter

    @property
    def stats(self) -> ThrottleStats:
        return self._throttler.stats

    @asynccontextmanager
    async def throttle(
        self, consumer: Optional[str] = None, priority: Optional[ThrottlePriority] = None
    ) -> AsyncIterator[ThrottleResult]:
        async with self._throttler.throttle() as result:
            self._throttle_result_counter.labels(
                throttle_consumer=consumer, throttle_priority=priority, throttle_result=result
            ).inc()
            yield result
