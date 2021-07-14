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

Example of an integration with aiohttp and prometheus_client()
```python
import aiohttp
import aiohttp.web
import aiohttp.web_request
import aiohttp.web_response

import aio_throttle


@aio_throttle.aiohttp_ignore() # do not throttle this handler 
async def healthcheck(_: aiohttp.web_request.Request) -> aiohttp.web_response.Response:
    return aiohttp.web_response.Response()


async def authorize(_: aiohttp.web_request.Request) -> aiohttp.web_response.Response:
    return aiohttp.web_response.Response()


async def create_app() -> aiohttp.web.Application:
    app = aiohttp.web.Application(middlewares=[
        aio_throttle.aiohttp_middleware_factory(
                capacity_limit=20,
                queue_limit=100,
                consumer_quotas=[aio_throttle.MaxFractionCapacityQuota[str](0.7)],
                priority_quotas=[
                    aio_throttle.MaxFractionCapacityQuota[aio_throttle.ThrottlePriority](
                        0.9, aio_throttle.ThrottlePriority.NORMAL
                    )
                ],
                metrics_provider=aio_throttle.PROMETHEUS_METRICS_PROVIDER,
            ),
    ])
    app.router.add_get("/healthcheck", healthcheck)
    app.router.add_post("/authorize", authorize)
    return app


aiohttp.web.run_app(create_app(), port=8080, access_log=None)
```
