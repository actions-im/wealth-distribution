import math

import pytest

from src.human_capital import annuity_factor, estimate_human_capital


def test_annuity_factor_returns_year_count_when_growth_equals_discount_rate():
    assert annuity_factor(years=12, wage_growth=0.03, discount_rate=0.03) == pytest.approx(12.0)


def test_annuity_factor_discounts_growing_income_stream():
    ratio = (1.015) / (1.035)
    expected = (1 - ratio**30) / (1 - ratio)

    assert annuity_factor(years=30, wage_growth=0.015, discount_rate=0.035) == pytest.approx(expected)


def test_annuity_factor_returns_zero_for_non_positive_years():
    assert annuity_factor(years=0, wage_growth=0.015, discount_rate=0.035) == 0
    assert annuity_factor(years=-4, wage_growth=0.015, discount_rate=0.035) == 0


def test_estimate_human_capital_zero_after_retirement_age():
    assert estimate_human_capital(current_labor_income=80_000, age=67, retirement_age=67) == 0
    assert estimate_human_capital(current_labor_income=80_000, age=72, retirement_age=67) == 0


def test_estimate_human_capital_applies_employment_and_tax_adjustments():
    factor = annuity_factor(years=20, wage_growth=0.01, discount_rate=0.04)
    expected = 100_000 * 0.9 * (1 - 0.2) * factor

    actual = estimate_human_capital(
        current_labor_income=100_000,
        age=45,
        retirement_age=65,
        wage_growth=0.01,
        discount_rate=0.04,
        employment_probability=0.9,
        tax_rate=0.2,
    )

    assert math.isfinite(actual)
    assert actual == pytest.approx(expected)

