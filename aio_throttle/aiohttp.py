from typing import Awaitable, Callable, Set, Optional, List

import aiohttp.web_exceptions
import aiohttp.web_middlewares
import aiohttp.web_request
import aiohttp.web_response

from .metrics import MetricsProvider, NOOP_METRICS_PROVIDER
from .base import ThrottlePriority
from .quotas import MaxFractionCapacityQuota, ThrottleCapacityQuota, ThrottleQuota
from .throttle import Throttler

_HANDLER = Callable[[aiohttp.web_request.Request], Awaitable[aiohttp.web_response.StreamResponse]]
_MIDDLEWARE = Callable[[aiohttp.web_request.Request, _HANDLER], Awaitable[aiohttp.web_response.StreamResponse]]


def aiohttp_middleware_factory(
    *,
    capacity_limit: int = 128,
    queue_limit: int = 512,
    consumer_quotas: Optional[List[ThrottleCapacityQuota[str]]] = None,
    priority_quotas: Optional[List[ThrottleCapacityQuota[ThrottlePriority]]] = None,
    quotas: Optional[List[ThrottleQuota]] = None,
    consumer_header_name: str = "X-Service-Name",
    priority_header_name: str = "X-Request-Priority",
    throttled_response_status_code: int = 503,
    throttled_response_reason_header_name: str = "X-Throttled-Reason",
    ignored_paths: Optional[Set[str]] = None,
    metrics_provider: MetricsProvider = NOOP_METRICS_PROVIDER,
) -> _MIDDLEWARE:
    throttler = Throttler(
        capacity_limit=capacity_limit,
        queue_limit=queue_limit,
        consumer_quotas=consumer_quotas or [MaxFractionCapacityQuota[str](0.7)],
        priority_quotas=priority_quotas or [MaxFractionCapacityQuota[ThrottlePriority](0.9, ThrottlePriority.NORMAL)],
        quotas=quotas,
        metrics_provider=metrics_provider,
    )

    @aiohttp.web_middlewares.middleware
    async def _throttling_middleware(
        request: aiohttp.web_request.Request, handler: _HANDLER
    ) -> aiohttp.web_response.StreamResponse:
        path = request.match_info.route.resource.canonical if request.match_info.route.resource else request.path
        if ignored_paths is not None and path in ignored_paths:
            return await handler(request)

        consumer = request.headers.get(consumer_header_name, "unknown").lower()
        priority = ThrottlePriority.parse(request.headers.get(priority_header_name))
        async with throttler.throttle(consumer=consumer, priority=priority) as throttle_result:
            if throttle_result:
                return await handler(request)

            return aiohttp.web_response.Response(
                status=throttled_response_status_code,
                headers={throttled_response_reason_header_name: str(throttle_result)},
            )

    return _throttling_middleware
