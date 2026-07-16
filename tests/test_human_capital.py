import math

import pytest

from src.human_capital import (
    PersonLaborInput,
    annuity_factor,
    estimate_household_labor_wealth,
    estimate_human_capital,
    estimate_labor_wealth,
    projected_labor_income_stream,
)


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


def test_non_earner_can_reenter_employment():
    value = estimate_labor_wealth(
        current_income=0,
        reentry_income=40_000,
        reentry_probability=0.25,
        age=30,
        retirement_age=67,
        survival=[1] * 37,
    )

    assert value > 0


def test_household_labor_wealth_sums_people_after_separate_projection():
    respondent = PersonLaborInput(age=64, current_income=50_000, sex="male")
    spouse = PersonLaborInput(age=40, current_income=70_000, sex="female")
    result = estimate_household_labor_wealth(
        respondent=respondent,
        spouse=spouse,
        survival_by_sex={"male": [1] * 3, "female": [1] * 27},
    )

    assert result.total == pytest.approx(result.respondent + result.spouse)
    assert result.spouse > result.respondent


def test_survival_weights_lower_labor_value():
    certain = estimate_labor_wealth(
        current_income=50_000, age=64, retirement_age=67, survival=[1, 1, 1]
    )
    risky = estimate_labor_wealth(
        current_income=50_000, age=64, retirement_age=67, survival=[1, 0.5, 0.25]
    )

    assert 0 < risky < certain


def test_defensive_mode_does_not_assume_real_wage_growth():
    defensive = estimate_labor_wealth(
        current_income=50_000,
        age=40,
        retirement_age=43,
        survival=[1, 1, 1],
        wage_growth=0.03,
        mode="defensive",
    )
    continuation = estimate_labor_wealth(
        current_income=50_000,
        age=40,
        retirement_age=43,
        survival=[1, 1, 1],
        wage_growth=0.03,
        mode="continuation",
    )

    assert continuation > defensive


def test_projected_labor_income_stream_uses_reentry_wage_for_non_earner():
    stream = projected_labor_income_stream(
        current_income=0,
        reentry_income=40_000,
        reentry_probability=0.25,
        age=30,
        retirement_age=32,
        employment_probability=0.95,
        wage_growth=0.0,
        tax_rate=0.0,
    )

    assert stream == pytest.approx([10_000, 10_000])
