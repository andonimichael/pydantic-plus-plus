from __future__ import annotations

import string
from decimal import Decimal
from random import Random
from typing import Any


def generate_constrained_int(random: Random, metadata: list[Any]) -> int:
    lower, upper = _resolve_numeric_bounds(metadata, exclusive_offset=1.0)
    multiple_of = _extract_bound(metadata, "multiple_of")

    value = random.randint(int(lower), int(upper))

    if multiple_of is not None:
        multiple_of_int = int(multiple_of)
        value = (value // multiple_of_int) * multiple_of_int
        if value < int(lower):
            value += multiple_of_int

    return value


def generate_constrained_float(random: Random, metadata: list[Any]) -> float:
    lower, upper = _resolve_numeric_bounds(metadata)
    return round(random.uniform(lower, upper), 2)


def generate_constrained_string(random: Random, metadata: list[Any]) -> str:
    min_length = _extract_bound(metadata, "min_length")
    max_length = _extract_bound(metadata, "max_length")

    if min_length is not None:
        min_length = int(min_length)
    else:
        min_length = 8

    if max_length is not None:
        max_length = int(max_length)
    else:
        max_length = max(min_length, 8)

    if min_length > max_length:
        max_length = min_length

    length = random.randint(min_length, max_length)
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))


def generate_constrained_decimal(random: Random, metadata: list[Any]) -> Decimal:
    float_value = generate_constrained_float(random, metadata)
    return Decimal(str(float_value))


def resolve_collection_length(random: Random, metadata: list[Any], default_min: int = 1, default_max: int = 3) -> int:
    min_length = _extract_bound(metadata, "min_length")
    max_length = _extract_bound(metadata, "max_length")

    raw_min = int(min_length) if min_length is not None else default_min
    raw_max = int(max_length) if max_length is not None else default_max

    resolved_min = max(raw_min, default_min)
    if max_length is not None:
        resolved_min = min(resolved_min, raw_max)

    resolved_max = max(min(raw_max, default_max), resolved_min)

    return random.randint(resolved_min, resolved_max)


def _extract_bound(metadata: list[Any], attr_name: str) -> int | float | None:
    for item in metadata:
        value = getattr(item, attr_name, None)
        if value is not None:
            return value  # type: ignore[no-any-return]
    return None


def _resolve_numeric_bounds(
    metadata: list[Any],
    default_lower: float = 0.0,
    default_range: float = 1000.0,
    exclusive_offset: float = 0.01,
) -> tuple[float, float]:
    lower = _extract_bound(metadata, "ge")
    upper = _extract_bound(metadata, "le")
    greater_than = _extract_bound(metadata, "gt")
    less_than = _extract_bound(metadata, "lt")

    if lower is None and greater_than is not None:
        resolved_lower = float(greater_than) + exclusive_offset
    elif lower is not None:
        resolved_lower = float(lower)
    else:
        resolved_lower = default_lower

    if upper is None and less_than is not None:
        resolved_upper = float(less_than) - exclusive_offset
    elif upper is not None:
        resolved_upper = float(upper)
    else:
        resolved_upper = resolved_lower + default_range

    return resolved_lower, resolved_upper
