import logging
from asyncio import FIRST_COMPLETED, wait, ALL_COMPLETED

import pytest

from aio_throttle import Throttler

logger = logging.getLogger(__name__)


@pytest.mark.asyncio
@pytest.mark.timeout(1)
async def test_throttle_without_queue():
    throttler = Throttler(1)
    async with throttler.throttle() as t1:
        assert t1.accepted
        async with throttler.throttle() as t2:
            assert not t2.accepted


@pytest.mark.asyncio
@pytest.mark.timeout(1)
async def test_throttle_with_queue():
    throttler = Throttler(1, 1)
    t1_ctx = throttler.throttle()
    t1 = await t1_ctx.__aenter__()
    assert t1.accepted

    t2_ctx = throttler.throttle()
    t3_ctx = throttler.throttle()

    pending = [t2_ctx.__aenter__(), t3_ctx.__aenter__()]
    done, pending = await wait(pending, return_when=FIRST_COMPLETED)
    assert len(done) == 1 and len(pending) == 1
    assert not (await list(done)[0]).accepted

    done, pending = await wait(pending, timeout=0.5, return_when=FIRST_COMPLETED)
    assert len(done) == 0 and len(pending) == 1

    await t1_ctx.__aexit__(None, None, None)

    done, pending = await wait(pending, return_when=FIRST_COMPLETED)
    assert len(done) == 1 and len(pending) == 0
    assert (await list(done)[0]).accepted
    assert (await list(done)[0]).accepted

    await wait([t2_ctx.__aexit__(None, None, None), t3_ctx.__aexit__(None, None, None)], return_when=ALL_COMPLETED)
