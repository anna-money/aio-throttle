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


consumer, priority = "yet another consumer", ThrottlePriority.HIGH
async with throttler.throttle(consumer=consumer, priority=priority) as result:
    ... # check if result is ThrottleResult.ACCEPTED or not
```

Example of an integration with aiohttp and prometheus_client
```python
from aiohttp import web
from aiohttp.web_app import Application
from aiohttp.web_request import Request
from aiohttp.web_response import Response

from aio_throttle.aiohttp import throttling_middleware, setup_throttling
from aio_throttle.prometheus import prometheus_aware_throttler, build_throttle_results_counter

throttle_results_counter = build_throttle_results_counter()


async def ok(_: Request) -> Response:
    return Response()


async def create_app() -> Application:
    app = web.Application(middlewares=[throttling_middleware()])
    setup_throttling(app, extensions=[prometheus_aware_throttler(throttle_results_counter=throttle_results_counter)])
    app.router.add_get("/", ok)
    return app


web.run_app(create_app(), port=8080, access_log=None)
```