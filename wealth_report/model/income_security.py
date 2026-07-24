from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from itertools import product

from wealth_report.model.actuarial import present_value_stream


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


def value_state_contingent_income_security_floor(
    *,
    income_by_adult: Mapping[str, Sequence[float]],
    survival_by_adult: Mapping[str, Sequence[float]],
    monthly_benchmark: float,
    discount_rate: float,
) -> float:
    """Value the floor across mutually exclusive adult-survival states."""
    owners = tuple(survival_by_adult)
    if not owners:
        return 0.0
    if set(income_by_adult) != set(owners):
        raise ValueError("income and survival streams must cover the same adults")
    if len(owners) > 2:
        raise ValueError("income-security floor supports at most two adults")

    horizon = max(len(survival_by_adult[owner]) for owner in owners)
    expected_top_up: list[float] = []
    for period in range(horizon):
        state_value = 0.0
        for alive_state in product((False, True), repeat=len(owners)):
            alive_count = sum(alive_state)
            if alive_count == 0:
                continue
            probability = 1.0
            surviving_income = 0.0
            for owner, is_alive in zip(owners, alive_state, strict=True):
                survival = (
                    float(survival_by_adult[owner][period])
                    if period < len(survival_by_adult[owner])
                    else 0.0
                )
                probability *= survival if is_alive else 1 - survival
                if is_alive and period < len(income_by_adult[owner]):
                    surviving_income += float(income_by_adult[owner][period])
            benchmark = annual_income_security_benchmark(
                monthly_benchmark=monthly_benchmark,
                adult_count=alive_count,
            )
            state_value += probability * max(0.0, benchmark - surviving_income)
        expected_top_up.append(state_value)

    return present_value_stream(expected_top_up, discount_rate)
