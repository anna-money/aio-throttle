import logging
from asyncio import FIRST_COMPLETED, wait, ALL_COMPLETED

import pytest

from aio_throttle import Throttler, StaticThrottleConsumerQuota, ThrottleRequest, ThrottleStats, defaultdict

logger = logging.getLogger(__name__)

request = ThrottleRequest("consumer")


def stats(available, queued, by_consumers=None):
    return ThrottleStats(available, queued, defaultdict(int, by_consumers or {}))


@pytest.mark.asyncio
@pytest.mark.timeout(1)
async def test_throttle_without_queue():
    throttler = Throttler(1)
    assert throttler.stats == stats(1, 0)
    async with throttler.throttle() as t1:
        assert t1.accepted
        assert throttler.stats == stats(0, 0)
        async with throttler.throttle() as t2:
            assert not t2.accepted
            assert throttler.stats == stats(0, 0)
    assert throttler.stats == stats(1, 0)


@pytest.mark.asyncio
@pytest.mark.timeout(1)
async def test_throttle_with_rejecting_consumer_quota():
    throttler = Throttler(1, 1, StaticThrottleConsumerQuota(False))
    assert throttler.stats == stats(1, 0, {})
    async with throttler.throttle(request) as t1:
        assert t1.accepted
        assert throttler.stats == stats(0, 0, {request.consumer: 1})
        async with throttler.throttle(request) as t2:
            assert throttler.stats == stats(0, 0, {request.consumer: 1})
            assert not t2.accepted
    assert throttler.stats == stats(1, 0, {request.consumer: 0})


@pytest.mark.asyncio
@pytest.mark.timeout(1)
async def test_throttle_with_queue():
    throttler = Throttler(1, 1)
    t1_ctx = throttler.throttle()
    assert throttler.stats == stats(1, 0, {})
    t1 = await t1_ctx.__aenter__()
    assert t1.accepted
    assert throttler.stats == stats(0, 0, {})

    t2_ctx = throttler.throttle()
    t3_ctx = throttler.throttle()

    done, pending = await wait({t2_ctx.__aenter__(), t3_ctx.__aenter__()}, return_when=FIRST_COMPLETED)
    assert len(done) == 1 and len(pending) == 1
    assert not (await list(done)[0]).accepted
    assert throttler.stats == stats(0, 1, {})

    done, pending = await wait(pending, timeout=0.5, return_when=FIRST_COMPLETED)
    assert len(done) == 0 and len(pending) == 1

    await t1_ctx.__aexit__(None, None, None)

    done, pending = await wait(pending, return_when=FIRST_COMPLETED)
    assert len(done) == 1 and len(pending) == 0
    assert (await list(done)[0]).accepted
    assert throttler.stats == stats(0, 0, {})

    await wait([t2_ctx.__aexit__(None, None, None), t3_ctx.__aexit__(None, None, None)], return_when=ALL_COMPLETED)
    assert throttler.stats == stats(1, 0, {})
