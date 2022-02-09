from typing import Awaitable, Callable, Set, Optional, List, Any

import aiohttp.web
import aiohttp.web_exceptions
import aiohttp.web_middlewares
import aiohttp.web_request
import aiohttp.web_response

from .base import ThrottlePriority
from .metrics import MetricsProvider, NOOP_METRICS_PROVIDER
from .quotas import MaxFractionCapacityQuota, ThrottleCapacityQuota, ThrottleQuota
from .throttle import Throttler

_HANDLER = Callable[[aiohttp.web_request.Request], Awaitable[aiohttp.web_response.StreamResponse]]
_MIDDLEWARE = Callable[[aiohttp.web_request.Request, _HANDLER], Awaitable[aiohttp.web_response.StreamResponse]]
_IGNORE_KEY = "__aio_throttle_ignore__"


def aiohttp_ignore(func: Optional[Callable[..., Any]] = None) -> Callable[..., Any]:
    def wrapper(f: Callable[..., Any]) -> Callable[..., Any]:
        setattr(f, _IGNORE_KEY, True)
        return f

    return wrapper if func is None else wrapper(func)  # type: ignore


def aiohttp_middleware_factory(
    *,
    capacity_limit: int = 128,
    queue_limit: int = 512,
    consumer_quotas: Optional[List[ThrottleCapacityQuota[str]]] = None,
    priority_quotas: Optional[List[ThrottleCapacityQuota[ThrottlePriority]]] = None,
    quotas: Optional[List[ThrottleQuota]] = None,
    consumer_header_name: str = "X-Service-Name",
    priority_header_name: str = "X-Request-Priority",
    throttled_response_status_code: int = 429,
    throttled_response_reason_header_name: str = "X-Throttled-Reason",
    ignored_paths: Optional[Set[str]] = None,
    metrics_provider: MetricsProvider = NOOP_METRICS_PROVIDER,
) -> _MIDDLEWARE:
    throttler = Throttler(
        capacity_limit=capacity_limit,
        queue_limit=queue_limit,
        consumer_quotas=(consumer_quotas if consumer_quotas is not None else [MaxFractionCapacityQuota[str](0.7)]),
        priority_quotas=(
            priority_quotas
            if priority_quotas is not None
            else [MaxFractionCapacityQuota[ThrottlePriority](0.9, ThrottlePriority.NORMAL)]
        ),
        quotas=quotas,
        metrics_provider=metrics_provider,
    )

    @aiohttp.web_middlewares.middleware
    async def _throttling_middleware(
        request: aiohttp.web_request.Request, handler: _HANDLER
    ) -> aiohttp.web_response.StreamResponse:
        if _is_ignored_by_decorator(request) or _is_ignored_by_path(request, ignored_paths):
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


def _is_ignored_by_decorator(request: aiohttp.web_request.Request) -> bool:
    handler = request.match_info.handler
    ignored = getattr(handler, _IGNORE_KEY, False)
    if not ignored and _is_subclass(handler, aiohttp.web.View):
        method_handler = getattr(handler, request.method.lower(), None)
        if method_handler is not None:
            ignored = getattr(method_handler, _IGNORE_KEY, False)
    return bool(ignored)


def _is_ignored_by_path(request: aiohttp.web_request.Request, ignored_paths: Optional[Set[str]]) -> bool:
    if ignored_paths is None:
        return False

    path = request.match_info.route.resource.canonical if request.match_info.route.resource else request.path
    return path in ignored_paths


def _is_subclass(cls: Any, cls_info: type) -> bool:
    try:
        return issubclass(cls, cls_info)
    except TypeError:
        return False
