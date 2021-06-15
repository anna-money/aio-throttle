from typing import TypeVar, Dict

T = TypeVar("T")


def increment_counter(dictionary: Dict[T, int], key: T) -> None:
    value = dictionary.get(key)
    if value is None:
        dictionary[key] = 1
    else:
        dictionary[key] = value + 1


def decrement_counter(dictionary: Dict[T, int], key: T) -> None:
    value = dictionary.get(key)
    if value is None:
        return
    if value - 1 == 0:
        del dictionary[key]
    else:
        dictionary[key] = value - 1
