import logging
import time
from asyncio import sleep, gather
from collections import Counter

import pytest

from aio_throttle import ThrottlePriority, MaxFractionCapacityQuota, Throttler

DELAY = 1
SUCCEED = "+"
FAILED = "-"

logger = logging.getLogger(__name__)


class Server:
    def __init__(self, delay, throttler):
        self.throttler = throttler
        self.delay = delay

    async def handle(self, priority):
        async with self.throttler.throttle(priority=priority) as result:
            if not result:
                return FAILED
            await sleep(self.delay)
            return SUCCEED


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "capacity_limit, max_priority_fractions, normal_counts, critical_counts, multiplier",
    [(4, (0.25, 0.75), (1, 3), (3, 1), 1), (4, (0.50, 0.50), (2, 2), (2, 2), 1), (4, (0.75, 0.25), (3, 1), (1, 3), 1)],
)
async def test(capacity_limit, max_priority_fractions, normal_counts, critical_counts, multiplier):
    max_normal_fraction, max_critical_fraction = max_priority_fractions
    priority_quotas = [
        MaxFractionCapacityQuota(max_normal_fraction, ThrottlePriority.NORMAL),
        MaxFractionCapacityQuota(max_critical_fraction, ThrottlePriority.HIGH),
    ]
    throttler = Throttler(capacity_limit, 0, [], priority_quotas)
    server = Server(DELAY, throttler)

    normal_tasks = list(map(lambda x: server.handle(ThrottlePriority.NORMAL), range(0, sum(normal_counts))))
    critical_tasks = list(map(lambda x: server.handle(ThrottlePriority.HIGH), range(0, sum(critical_counts))))

    start = time.monotonic()
    normal_statuses, critical_statuses = await gather(gather(*normal_tasks), gather(*critical_tasks))
    end = time.monotonic()

    normal_counter = Counter(normal_statuses)
    assert (normal_counter[SUCCEED], normal_counter[FAILED]) == normal_counts

    critical_counter = Counter(critical_statuses)
    assert (critical_counter[SUCCEED], critical_counter[FAILED]) == critical_counts

    assert multiplier * DELAY <= end - start <= (1.1 * multiplier * DELAY)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "capacity_limit, queue_limit, counts, multiplier", [(1, 1, (2, 0), 2), (1, 2, (2, 1), 2), (1, 2, (2, 2), 2)]
)
async def test_low_priority_queueing(capacity_limit, queue_limit, counts, multiplier):
    throttler = Throttler(capacity_limit, queue_limit)
    server = Server(DELAY, throttler)

    handle_tasks = list(map(lambda x: server.handle(ThrottlePriority.LOW), range(0, sum(counts))))
    start = time.monotonic()
    statuses = await gather(*handle_tasks)
    end = time.monotonic()

    statuses_counter = Counter(statuses)
    assert (statuses_counter[SUCCEED], statuses_counter[FAILED]) == counts

    assert multiplier * DELAY <= end - start <= (1.1 * multiplier * DELAY)
