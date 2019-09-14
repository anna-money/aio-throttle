import time
from asyncio import sleep, gather
from collections import Counter

import pytest

from aio_throttle import Throttler

DELAY = 1
SUCCEED = "+"
FAILED = "-"


class Server:
    def __init__(self, delay, throttler):
        self.throttler = throttler
        self.delay = delay

    async def handle(self):
        async with self.throttler.throttle() as result:
            if not result.accepted:
                return FAILED
            await sleep(self.delay)
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
    ]
)
async def test_simple_workload(capacity_limit, queue_limit, succeed_count, failed_count, multiplier):
    server = Server(DELAY, Throttler(capacity_limit, queue_limit))
    start = time.monotonic()

    handle_tasks = list(map(lambda x: server.handle(), range(0, succeed_count + failed_count)))
    statuses = await gather(*handle_tasks)

    end = time.monotonic()

    counter = Counter(statuses)
    assert counter[SUCCEED] == succeed_count and counter[FAILED] == failed_count
    assert multiplier * DELAY <= end - start <= (1.1 * multiplier * DELAY)
