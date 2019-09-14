import pytest

from aio_throttle.quotas import MaxFractionConsumerQuota


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
def test_max_fraction_any_consumer_quota(max_fraction, used, limit, accept):
    assert accept == MaxFractionConsumerQuota(max_fraction).accept("consumer", used, limit)


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
def test_max_fraction_consumer_quota_match(max_fraction, used, limit, accept):
    assert accept == MaxFractionConsumerQuota(max_fraction, "consumer").accept("consumer", used, limit)


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
def test_max_fraction_consumer_quota_not_match(max_fraction, used, limit, accept):
    assert accept == MaxFractionConsumerQuota(max_fraction, "consumer").accept("yet_another_consumer", used, limit)
