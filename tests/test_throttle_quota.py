import asyncio
import collections
import logging
import time
import pytest

from aio_throttle import Throttler, RandomRejectThrottleQuota

DELAY = 1
SUCCEED = "+"
FAILED = "-"

logger = logging.getLogger(__name__)


class Server:
    def __init__(self, delay, throttler):
        self.throttler = throttler
        self.delay = delay

    async def handle(self):
        async with self.throttler.throttle() as result:
            if not result:
                return FAILED
            await asyncio.sleep(self.delay)
            return SUCCEED


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "capacity_limit, reject_probability, succeed_count, failed_count, multiplier",
    [(2, 0.5, 2, 2, 1), (1, 0.5, 1, 3, 1)],
)
async def test(capacity_limit, reject_probability, succeed_count, failed_count, multiplier):
    throttler = Throttler(capacity_limit, 0, [], [], [RandomRejectThrottleQuota(reject_probability, 0)])
    server = Server(DELAY, throttler)

    handle_tasks = list(map(lambda x: server.handle(), range(0, succeed_count + failed_count)))

    start = time.monotonic()
    statuses = await asyncio.gather(*handle_tasks)
    end = time.monotonic()

    counter = collections.Counter(statuses)
    assert counter[SUCCEED] == succeed_count
    assert counter[FAILED] == failed_count
    assert multiplier * DELAY <= end - start <= (1.1 * multiplier * DELAY)
