from typing import Awaitable, Callable, Set, Optional, List

from aiohttp.web_app import Application
from aiohttp.web_middlewares import middleware
from aiohttp.web_request import Request
from aiohttp.web_response import Response, StreamResponse

from .abc import ThrottlerBase, ThrottlePriority
from .quotas import MaxFractionCapacityQuota, ThrottleCapacityQuota, ThrottleQuota
from .throttle import Throttler

HANDLER = Callable[[Request], Awaitable[Response]]
MIDDLEWARE = Callable[[Request, HANDLER], Awaitable[StreamResponse]]

__all__ = (
    "setup_throttling",
    "throttling_middleware",
)


def setup_throttling(
    app: Application,
    capacity_limit: int = 128,
    queue_limit: int = 512,
    consumer_quotas: Optional[List[ThrottleCapacityQuota[str]]] = None,
    priority_quotas: Optional[List[ThrottleCapacityQuota[ThrottlePriority]]] = None,
    quotas: Optional[List[ThrottleQuota]] = None,
    extensions: Optional[List[Callable[[ThrottlerBase], ThrottlerBase]]] = None,
) -> None:
    throttler: ThrottlerBase = Throttler(
        capacity_limit=capacity_limit,
        queue_limit=queue_limit,
        consumer_quotas=consumer_quotas or [MaxFractionCapacityQuota[str](0.7)],
        priority_quotas=priority_quotas or [MaxFractionCapacityQuota[ThrottlePriority](0.9, ThrottlePriority.NORMAL)],
        quotas=quotas,
    )
    if extensions:
        for extension in extensions:
            throttler = extension(throttler)
    app["AIOTHROTTLER"] = throttler


def throttling_middleware(
    consumer_header_name: str = "X-Service-Name",
    priority_header_name: str = "X-Request-Priority",
    throttled_response_status_code: int = 503,
    throttled_response_reason_header_name: str = "X-Throttled-Reason",
    ignored_paths: Optional[Set[str]] = None,
) -> MIDDLEWARE:
    @middleware
    async def _throttling_middleware(request: Request, handler: HANDLER) -> Response:
        path = request.match_info.route.resource.canonical if request.match_info.route.resource else request.path
        if ignored_paths is not None and path in ignored_paths:
            return await handler(request)

        throttler: ThrottlerBase = request.app["AIOTHROTTLER"]
        consumer = request.headers.get(consumer_header_name, "unknown").lower()
        priority = ThrottlePriority.parse(request.headers.get(priority_header_name))
        async with throttler.throttle(consumer=consumer, priority=priority) as throttle_result:
            if throttle_result:
                return await handler(request)

            return Response(
                status=throttled_response_status_code,
                headers={throttled_response_reason_header_name: str(throttle_result)},
            )

    return _throttling_middleware
