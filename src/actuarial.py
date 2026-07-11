from __future__ import annotations

import math
from collections.abc import Iterable, Mapping, Sequence


def _validate_rate(rate: float, name: str) -> None:
    if not math.isfinite(rate) or rate <= -1:
        raise ValueError(f"{name} must be finite and greater than -1")


def conditional_survival(
    lives_by_age: Mapping[int, float], current_age: int, max_age: int | None = None
) -> list[float]:
    """Return survival probabilities conditional on being alive at current_age."""
    if current_age not in lives_by_age:
        raise ValueError("current_age is absent from the life table")
    current_lives = float(lives_by_age[current_age])
    if not math.isfinite(current_lives) or current_lives <= 0:
        raise ValueError("life-table lives at current_age must be positive")

    last_age = max(lives_by_age) if max_age is None else max_age
    if last_age < current_age:
        raise ValueError("max_age cannot be below current_age")

    probabilities: list[float] = []
    prior = 1.0
    for age in range(current_age, last_age + 1):
        if age not in lives_by_age:
            raise ValueError(f"life table is missing age {age}")
        probability = float(lives_by_age[age]) / current_lives
        if not math.isfinite(probability) or probability < 0 or probability > prior + 1e-12:
            raise ValueError("life-table survival must be finite, nonnegative, and nonincreasing")
        probabilities.append(min(probability, prior))
        prior = probability
    return probabilities


def present_value_stream(
    payments: Iterable[float],
    discount_rate: float,
    survival: Sequence[float] | None = None,
    *,
    start_period: int = 1,
) -> float:
    """Value finite annual payments; the default first payment is one year ahead."""
    _validate_rate(discount_rate, "discount_rate")
    if start_period < 0:
        raise ValueError("start_period must be nonnegative")

    cash_flows = [float(payment) for payment in payments]
    if any(not math.isfinite(payment) for payment in cash_flows):
        raise ValueError("payments must be finite")
    weights = [1.0] * len(cash_flows) if survival is None else [float(value) for value in survival]
    if len(weights) != len(cash_flows):
        raise ValueError("survival and payments must have equal lengths")
    if any(not math.isfinite(value) or not 0 <= value <= 1 for value in weights):
        raise ValueError("survival probabilities must be finite and between zero and one")

    return float(
        sum(
            payment * probability / (1 + discount_rate) ** (start_period + offset)
            for offset, (payment, probability) in enumerate(zip(cash_flows, weights, strict=True))
        )
    )


def survival_weighted_annuity(
    annual_payment: float,
    *,
    current_age: int,
    claiming_age: int,
    lives_by_age: Mapping[int, float],
    discount_rate: float,
    max_age: int | None = None,
) -> float:
    """Value an annual life annuity with payments beginning at claiming age."""
    if claiming_age < current_age:
        claiming_age = current_age
    final_age = max(lives_by_age) if max_age is None else min(max_age, max(lives_by_age))
    if claiming_age > final_age:
        return 0.0
    survival = conditional_survival(lives_by_age, current_age, final_age)
    first_offset = claiming_age - current_age
    payment_count = final_age - claiming_age + 1
    return present_value_stream(
        [annual_payment] * payment_count,
        discount_rate,
        survival=survival[first_offset:],
        start_period=max(first_offset, 1),
    )
