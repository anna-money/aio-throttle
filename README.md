This library is inspired by [this book](https://landing.google.com/sre/sre-book/chapters/handling-overload/) and this implementation https://github.com/vostok/throttling.

Features:
1. Set capacity(max parallel requests) and queue(max queued requests) limits.
1. Per-consumer limits. For instance, to not allow any consumer to use more than 70% of service's capacity.
1. Per-request priorities. For instance, to not allow requests with lowest priority to be queued or to now allow requests with normal priority to use more than 90% of service's capacity. 

Example:
```python
from aio_throttle import Throttler, MaxFractionCapacityQuota, ThrottlePriority, ThrottleResult

capacity_limit = 100
queue_limit = 200
consumer_quotas = [MaxFractionCapacityQuota(0.7)]
priority_quotas = [MaxFractionCapacityQuota(0.9, ThrottlePriority.NORMAL)]
throttler = Throttler(capacity_limit, queue_limit, consumer_quotas, priority_quotas)

async with throttler.throttle(consumer, priority) as result:
    ... # check if result is ThrottleResult.ACCEPTED or not
```


Example of integration with `aiohttp`:
```python
from typing import Awaitable, Callable

from aiohttp import web
from aiohttp.web_middlewares import middleware
from aiohttp.web_request import Request
from aiohttp.web_response import StreamResponse

from aio_throttle import Throttler, ThrottlePriority

Handler = Callable[[Request], Awaitable[StreamResponse]]


@middleware
async def middleware(request: Request, handler: Handler) -> StreamResponse:
    throttler: Throttler = request.app['throttler']
    service = request.headers.get('X-Service', 'UNKNOWN')
    priority = ThrottlePriority(request.headers.get('X-Request-Priority', ThrottlePriority.NORMAL))
    async with throttler.throttle(service, priority) as result:
        if not result:
            return web.Response(status=503)
        return await handler(request)
```
