from typing import Any, Dict

import prometheus_client

from .metrics import MetricsProvider


class PrometheusMetricsProvider(MetricsProvider):
    __slots__ = ("_metrics", "_registry")

    def __init__(self, registry: prometheus_client.CollectorRegistry) -> None:
        self._metrics: Dict[str, Any] = {}
        self._registry = registry

    def increment_counter(self, name: str, tags: Dict[str, str], value: float = 1) -> None:
        if name not in self._metrics:
            self._metrics[name] = prometheus_client.Counter(name, "", labelnames=tags.keys())
        self._metrics[name].labels(*tags.values()).inc(value)


PROMETHEUS_METRICS_PROVIDER = PrometheusMetricsProvider(prometheus_client.REGISTRY)
