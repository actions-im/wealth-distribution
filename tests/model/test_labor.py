import pytest

from wealth_report.model.labor import (
    PersonLaborInput,
    estimate_household_labor_wealth,
    estimate_labor_wealth,
    projected_labor_income_stream,
)


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
