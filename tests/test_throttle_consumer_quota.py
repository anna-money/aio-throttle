import logging
import time
from asyncio import sleep, gather
from collections import Counter

import pytest

from aio_throttle import MaxFractionCapacityQuota
from aio_throttle import Throttler

DELAY = 1
SUCCEED = "+"
FAILED = "-"
FIRST_CONSUMER = "first"
SECOND_CONSUMER = "second"

logger = logging.getLogger(__name__)


class Server:
    def __init__(self, delay, throttler):
        self.throttler = throttler
        self.delay = delay

    async def handle(self, consumer=None):
        async with self.throttler.throttle(consumer=consumer) as result:
            if not result:
                return FAILED
            await sleep(self.delay)
            return SUCCEED


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "capacity_limit, max_any_consumer_fraction, succeed_count, failed_count, multiplier",
    [(4, 0.25, 1, 3, 1), (4, 0.5, 2, 2, 1), (4, 0.75, 3, 1, 1)],
)
async def test_any_consumer_quota_workload(
    capacity_limit, max_any_consumer_fraction, succeed_count, failed_count, multiplier
):
    consumer_quotas = [MaxFractionCapacityQuota(max_any_consumer_fraction)]
    throttler = Throttler(capacity_limit, 0, consumer_quotas)
    server = Server(DELAY, throttler)
    handle_tasks = list(map(lambda x: server.handle("consumer"), range(0, succeed_count + failed_count)))

    start = time.monotonic()
    statuses = await gather(*handle_tasks)
    end = time.monotonic()

    counter = Counter(statuses)
    assert counter[SUCCEED] == succeed_count
    assert counter[FAILED] == failed_count
    assert multiplier * DELAY <= end - start <= (1.1 * multiplier * DELAY)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "capacity_limit, max_consumer_fractions, first_consumer_counts, second_consumer_counts, multiplier",
    [(4, (0.25, 0.75), (1, 3), (3, 1), 1), (4, (0.50, 0.50), (2, 2), (2, 2), 1), (4, (0.75, 0.25), (3, 1), (1, 3), 1)],
)
async def test_consumers_quota_workload(
    capacity_limit, max_consumer_fractions, first_consumer_counts, second_consumer_counts, multiplier
):
    max_first_consumer_fraction, max_second_consumer_fraction = max_consumer_fractions
    first_consumer_succeed_count, first_consumer_failed_count = first_consumer_counts
    second_consumer_succeed_count, second_consumer_failed_count = second_consumer_counts
    consumer_quotas = [
        MaxFractionCapacityQuota(max_first_consumer_fraction, FIRST_CONSUMER),
        MaxFractionCapacityQuota(max_second_consumer_fraction, SECOND_CONSUMER),
    ]
    throttler = Throttler(capacity_limit, 0, consumer_quotas)
    server = Server(DELAY, throttler)

    first_consumer_handle_tasks = list(
        map(
            lambda x: server.handle(FIRST_CONSUMER),
            range(0, first_consumer_succeed_count + first_consumer_failed_count),
        )
    )
    second_consumer_handle_tasks = list(
        map(
            lambda x: server.handle(SECOND_CONSUMER),
            range(0, second_consumer_succeed_count + second_consumer_failed_count),
        )
    )

    start = time.monotonic()
    first_consumer_statuses, second_consumer_statuses = await gather(
        gather(*first_consumer_handle_tasks), gather(*second_consumer_handle_tasks)
    )
    end = time.monotonic()

    counter = Counter(first_consumer_statuses)
    assert counter[SUCCEED] == first_consumer_succeed_count
    assert counter[FAILED] == first_consumer_failed_count

    counter = Counter(second_consumer_statuses)
    assert counter[SUCCEED] == second_consumer_succeed_count
    assert counter[FAILED] == second_consumer_failed_count

    assert multiplier * DELAY <= end - start <= (1.1 * multiplier * DELAY)
