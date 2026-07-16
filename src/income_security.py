from __future__ import annotations

import math
from collections.abc import Sequence

from src.actuarial import present_value_stream


COUPLE_BENCHMARK_RATIO = 1.5


def annual_income_security_benchmark(*, monthly_benchmark: float, adult_count: int) -> float:
    """Return the annual modeled floor for one or more adults in an SCF family."""
    if not math.isfinite(monthly_benchmark) or monthly_benchmark < 0:
        raise ValueError("monthly_benchmark must be finite and nonnegative")
    if adult_count < 1:
        raise ValueError("adult_count must be at least one")
    household_multiplier = 1 + (adult_count - 1) * (COUPLE_BENCHMARK_RATIO - 1)
    return float(monthly_benchmark * 12 * household_multiplier)


def income_security_floor_stream(
    *,
    other_income: Sequence[float],
    monthly_benchmark: float,
    adult_count: int,
) -> list[float]:
    """Top up modeled annual income to the selected scenario benchmark."""
    benchmark = annual_income_security_benchmark(
        monthly_benchmark=monthly_benchmark,
        adult_count=adult_count,
    )
    income = [float(value) for value in other_income]
    if any(not math.isfinite(value) or value < 0 for value in income):
        raise ValueError("other_income must contain finite nonnegative values")
    return [max(0.0, benchmark - value) for value in income]


def value_income_security_floor(
    *,
    other_income: Sequence[float],
    monthly_benchmark: float,
    adult_count: int,
    survival: Sequence[float],
    discount_rate: float,
) -> float:
    """Present-value an annual nonmarketable income-security floor stream."""
    top_up = income_security_floor_stream(
        other_income=other_income,
        monthly_benchmark=monthly_benchmark,
        adult_count=adult_count,
    )
    return present_value_stream(top_up, discount_rate, survival=survival)
