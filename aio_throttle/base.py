import dataclasses
import enum
from typing import Optional, Mapping


class ThrottlePriority(str, enum.Enum):
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"

    def __str__(self) -> str:
        return self.value

    @staticmethod
    def parse(value: Optional[str]) -> "ThrottlePriority":
        if value is None:
            return ThrottlePriority.NORMAL
        try:
            return ThrottlePriority(value.lower())
        except ValueError:
            return ThrottlePriority.NORMAL


class ThrottleResult(str, enum.Enum):
    ACCEPTED = "accepted"
    REJECTED_DUE_TO_FULL_QUEUE = "rejected due to full queue"
    REJECTED_DUE_TO_PRIORITY_QUOTA = "rejected due to priority quota"
    REJECTED_DUE_TO_CONSUMER_QUOTA = "rejected due to consumer quota"
    REJECTED_DUE_TO_QUOTA = "rejected due to quota"

    def __bool__(self) -> bool:
        return self == self.ACCEPTED

    def __str__(self) -> str:
        return self.value


@dataclasses.dataclass(frozen=True)
class ThrottleStats:
    __slots__ = (
        "available_capacity",
        "capacity_limit",
        "queue_size",
        "queue_limit",
        "consumers_used_capacity",
        "priorities_used_capacity",
    )

    available_capacity: int
    capacity_limit: int
    queue_size: int
    queue_limit: int
    consumers_used_capacity: Mapping[str, int]
    priorities_used_capacity: Mapping[ThrottlePriority, int]
