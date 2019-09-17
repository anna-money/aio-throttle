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
    consumer = request.headers.get('X-Service-Name', 'UNKNOWN')
    priority = ThrottlePriority(request.headers.get('X-Request-Priority', ThrottlePriority.NORMAL))
    async with throttler.throttle(consumer, priority) as result:
        if not result:
            return web.Response(status=503)
        return await handler(request)
