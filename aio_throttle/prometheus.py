from contextlib import asynccontextmanager
from typing import Optional, AsyncIterator, Callable

from prometheus_client import Counter

from .abc import ThrottlerBase, ThrottlePriority, ThrottleResult, ThrottleStats

__all__ = ("prometheus_aware_throttler", "PrometheusAwareThrottler")


def prometheus_aware_throttler(*, throttle_results_counter: Counter) -> Callable[[ThrottlerBase], ThrottlerBase]:
    """
    :param throttle_results_counter: A prometheus counter which is supposed to have three labels:
        consumer, priority, result
    """

    def wrap(throttler: ThrottlerBase) -> ThrottlerBase:
        return PrometheusAwareThrottler(throttler, throttle_results_counter=throttle_results_counter)

    return wrap


class PrometheusAwareThrottler(ThrottlerBase):
    __slots__ = ("_throttler", "_throttle_results_counter")

    def __init__(
        self, throttler: ThrottlerBase, *, throttle_results_counter: Counter,
    ):
        """
        :param throttler: main throttler
        :param throttle_results_counter: A prometheus counter which is supposed to have three labels:
            consumer, priority, result
        """
        self._throttler = throttler
        self._throttle_results_counter = throttle_results_counter

    @property
    def stats(self) -> ThrottleStats:
        return self._throttler.stats

    @asynccontextmanager
    async def throttle(
        self, *, consumer: Optional[str] = None, priority: Optional[ThrottlePriority] = None
    ) -> AsyncIterator[ThrottleResult]:
        async with self._throttler.throttle(consumer=consumer, priority=priority) as result:
            self._throttle_results_counter.labels(consumer, priority, result).inc()
            yield result
