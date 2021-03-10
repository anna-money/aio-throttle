import abc
from typing import Dict


class MetricsProvider(abc.ABC):
    __slots__ = ()

    @abc.abstractmethod
    def increment_counter(self, name: str, tags: Dict[str, str], value: float = 1) -> None:
        pass


class NoopMetricsProvider(MetricsProvider):
    __slots__ = ()

    def increment_counter(self, name: str, tags: Dict[str, str], value: float = 1) -> None:
        pass


NOOP_METRICS_PROVIDER = NoopMetricsProvider()
