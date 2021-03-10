import asyncio
import collections
import logging
import time


import pytest

from aio_throttle import Throttler

DELAY = 1
SUCCEED = "+"
FAILED = "-"

logger = logging.getLogger(__name__)


class Server:
    def __init__(self, delay, throttler):
        self.throttler = throttler
        self.delay = delay

    async def handle(self, consumer=None):
        async with self.throttler.throttle(consumer=consumer) as result:
            if not result:
                return FAILED
            await asyncio.sleep(self.delay)
            return SUCCEED


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "capacity_limit, queue_limit, succeed_count, failed_count, multiplier",
    [
        (1, 0, 1, 0, 1),
        (1, 0, 1, 1, 1),
        (2, 0, 2, 0, 1),
        (2, 0, 2, 1, 1),
        (1, 1, 2, 0, 2),
        (1, 1, 2, 1, 2),
        (2, 1, 3, 0, 2),
        (2, 1, 3, 1, 2),
        (1, 1, 2, 0, 2),
        (1, 1, 2, 1, 2),
        (1, 2, 3, 0, 3),
        (1, 2, 3, 1, 3),
    ],
)
async def test(capacity_limit, queue_limit, succeed_count, failed_count, multiplier):
    server = Server(DELAY, Throttler(capacity_limit, queue_limit))

    handle_tasks = list(map(lambda x: server.handle(), range(0, succeed_count + failed_count)))

    start = time.monotonic()
    statuses = await asyncio.gather(*handle_tasks)
    end = time.monotonic()

    counter = collections.Counter(statuses)
    assert counter[SUCCEED] == succeed_count
    assert counter[FAILED] == failed_count
    assert multiplier * DELAY <= end - start <= (1.1 * multiplier * DELAY)
