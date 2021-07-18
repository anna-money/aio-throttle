import asyncio

import aiohttp
import aiohttp.web
import aiohttp.web_request
import aiohttp.web_response
import pytest
import yarl

import aio_throttle


@pytest.fixture
async def server(aiohttp_client):
    async def handler(_: aiohttp.web_request.Request) -> aiohttp.web_response.Response:
        await asyncio.sleep(0.1)
        return aiohttp.web_response.Response()

    @aio_throttle.aiohttp_ignore()
    async def handler_with_suppress(_: aiohttp.web_request.Request) -> aiohttp.web_response.Response:
        await asyncio.sleep(0.1)
        return aiohttp.web_response.Response()

    class ViewWithSuppress(aiohttp.web.View):
        @aio_throttle.aiohttp_ignore
        async def get(self) -> aiohttp.web.StreamResponse:
            await asyncio.sleep(0.1)
            return aiohttp.web_response.Response()

    app = aiohttp.web.Application(
        middlewares=[
            aio_throttle.aiohttp_middleware_factory(
                capacity_limit=1,
                queue_limit=0,
                consumer_quotas=[],
                priority_quotas=[],
                ignored_paths={"/ignore"},
                metrics_provider=aio_throttle.PROMETHEUS_METRICS_PROVIDER,
            )
        ],
    )
    app.router.add_get("/", handler)
    app.router.add_get("/ignore-handler", handler_with_suppress)
    app.router.add_get("/ignore-view", ViewWithSuppress)
    app.router.add_get("/ignore", handler)
    return await aiohttp_client(app)


async def test_throttle(server):
    async with aiohttp.ClientSession() as client_session:
        url = yarl.URL(f"http://{server.server.host}:{server.server.port}/")
        first, second = await asyncio.gather(client_session.get(url), client_session.get(url))
        async with first, second:
            assert first.status == 200
            assert second.status == 503


async def test_ignore_throttle_for_handler(server):
    async with aiohttp.ClientSession() as client_session:
        url = yarl.URL(f"http://{server.server.host}:{server.server.port}/ignore-handler")
        first, second = await asyncio.gather(client_session.get(url), client_session.get(url))
        async with first, second:
            assert first.status == 200
            assert second.status == 200


async def test_ignore_throttle_for_handler_by_set(server):
    async with aiohttp.ClientSession() as client_session:
        url = yarl.URL(f"http://{server.server.host}:{server.server.port}/ignore")
        first, second = await asyncio.gather(client_session.get(url), client_session.get(url))
        async with first, second:
            assert first.status == 200
            assert second.status == 200


async def test_ignore_throttle_for_view(server):
    async with aiohttp.ClientSession() as client_session:
        url = yarl.URL(f"http://{server.server.host}:{server.server.port}/ignore-view")
        first, second = await asyncio.gather(client_session.get(url), client_session.get(url))
        async with first, second:
            assert first.status == 200
            assert second.status == 200
