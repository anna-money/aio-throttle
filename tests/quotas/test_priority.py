import pytest

from aio_throttle import ThrottlePriority
from aio_throttle.quotas.priority import MaxFractionPriorityQuota


@pytest.mark.parametrize(
    "max_fraction, used, limit, accept",
    [
        (0, 0, 100, True),
        (0, 1, 100, False),
        (0, 100, 100, False),
        (0.01, 1, 100, True),
        (0.01, 2, 100, False),
        (0.01, 100, 100, False),
        (0.10, 1, 100, True),
        (0.10, 10, 100, True),
        (0.10, 11, 100, False),
        (0.10, 100, 100, False),
        (1, 0, 100, True),
        (1, 100, 100, True),
    ],
)
def test_max_fraction_priority_quota_match(max_fraction, used, limit, accept):
    quota = MaxFractionPriorityQuota(max_fraction, ThrottlePriority.NORMAL)
    assert accept == quota.accept(ThrottlePriority.NORMAL, used, limit)


@pytest.mark.parametrize(
    "max_fraction, used, limit, accept",
    [
        (0, 0, 100, True),
        (0, 100, 100, True),
        (0.01, 1, 100, True),
        (0.01, 100, 100, True),
        (0.10, 1, 100, True),
        (0.10, 100, 100, True),
        (1, 0, 100, True),
        (1, 100, 100, True),
    ],
)
def test_max_fraction_priority_quota_not_match(max_fraction, used, limit, accept):
    quota = MaxFractionPriorityQuota(max_fraction, ThrottlePriority.NORMAL)
    assert accept == quota.accept(ThrottlePriority.CRITICAL, used, limit)
