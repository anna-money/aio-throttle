from contextlib import asynccontextmanager
from typing import Optional, AsyncIterator, Callable
from prometheus_client import Counter, CollectorRegistry, REGISTRY

from .abc import ThrottlerBase, ThrottlePriority, ThrottleResult, ThrottleStats

__all__ = ("build_throttle_results_counter", "prometheus_aware_throttler", "PrometheusAwareThrottler")


def prometheus_aware_throttler(*, throttle_results_counter: Counter) -> Callable[[ThrottlerBase], ThrottlerBase]:
    def wrap(throttler: ThrottlerBase) -> ThrottlerBase:
        return PrometheusAwareThrottler(throttler, throttle_results_counter=throttle_results_counter)

    return wrap


def build_throttle_results_counter(
    *, registry: CollectorRegistry = REGISTRY, namespace: str = "", subsystem: str = ""
) -> Counter:
    return Counter(
        name="throttle_results",
        documentation="Throttle result",
        labelnames=("throttle_consumer", "throttle_priority", "throttle_result"),
        namespace=namespace,
        subsystem=subsystem,
        registry=registry,
    )


class PrometheusAwareThrottler(ThrottlerBase):
    __slots__ = ("_throttler", "_throttle_results_counter")

    def __init__(
        self, throttler: ThrottlerBase, *, throttle_results_counter: Counter,
    ):
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
            self._throttle_results_counter.labels(
                throttle_consumer=consumer, throttle_priority=priority, throttle_result=result
            ).inc()
            yield result
