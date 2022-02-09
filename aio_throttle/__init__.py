import collections
import re
import sys

from .throttle import Throttler  # noqa
from .quotas import ThrottleCapacityQuota, MaxFractionCapacityQuota, ThrottleQuota, RandomRejectThrottleQuota  # noqa
from .base import ThrottlePriority, ThrottleStats, ThrottleResult  # noqa
from .metrics import MetricsProvider, NoopMetricsProvider, NOOP_METRICS_PROVIDER  # noqa


try:
    import aiohttp  # noqa

    from .aiohttp import aiohttp_middleware_factory, aiohttp_ignore  # noqa
except ImportError:
    pass

try:
    import prometheus_client  # noqa

    from .prometheus import PROMETHEUS_METRICS_PROVIDER, PrometheusMetricsProvider  # noqa
except ImportError:
    pass


__version__ = "1.7.0"

version = f"{__version__}, Python {sys.version}"

VersionInfo = collections.namedtuple("VersionInfo", "major minor micro release_level serial")


def _parse_version(v: str) -> VersionInfo:
    version_re = r"^(?P<major>\d+)\.(?P<minor>\d+)\.(?P<micro>\d+)" r"((?P<release_level>[a-z]+)(?P<serial>\d+)?)?$"
    match = re.match(version_re, v)
    if not match:
        raise ImportError(f"Invalid package version {v}")
    try:
        major = int(match.group("major"))
        minor = int(match.group("minor"))
        micro = int(match.group("micro"))
        levels = {"rc": "candidate", "a": "alpha", "b": "beta", None: "final"}
        release_level = levels[match.group("release_level")]
        serial = int(match.group("serial")) if match.group("serial") else 0
        return VersionInfo(major, minor, micro, release_level, serial)
    except Exception as e:
        raise ImportError(f"Invalid package version {v}") from e


version_info = _parse_version(__version__)
