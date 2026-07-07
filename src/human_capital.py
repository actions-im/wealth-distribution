from __future__ import annotations

import math


def annuity_factor(years: int, wage_growth: float, discount_rate: float) -> float:
    """Present-value factor for a finite growing income stream."""
    if years <= 0:
        return 0.0

    ratio = (1 + wage_growth) / (1 + discount_rate)
    if math.isclose(ratio, 1.0, rel_tol=1e-12, abs_tol=1e-12):
        return float(years)

    return float((1 - ratio**years) / (1 - ratio))


def estimate_human_capital(
    current_labor_income: float,
    age: int,
    retirement_age: int = 67,
    wage_growth: float = 0.015,
    discount_rate: float = 0.035,
    employment_probability: float = 0.95,
    tax_rate: float = 0.0,
) -> float:
    years = max(retirement_age - age, 0)
    if years == 0 or current_labor_income <= 0:
        return 0.0

    after_tax_income = current_labor_income * (1 - tax_rate)
    expected_income = after_tax_income * employment_probability
    return float(expected_income * annuity_factor(years, wage_growth, discount_rate))
