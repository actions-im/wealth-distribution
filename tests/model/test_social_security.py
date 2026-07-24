import pytest

from wealth_report.model.social_security import (
    SocialSecurityPerson,
    claiming_age_factor,
    social_security_income_stream,
    social_security_wealth,
)
from wealth_report.providers.ssa.parameters import primary_insurance_amount


def test_2022_pia_formula_uses_official_bend_points():
    assert primary_insurance_amount(1_024, year=2022) == pytest.approx(921.60)
    assert primary_insurance_amount(6_172, year=2022) == pytest.approx(2_568.96)


def test_pia_formula_is_progressive_above_second_bend_point():
    assert primary_insurance_amount(7_172, year=2022) == pytest.approx(2_718.96)


def test_defensive_social_security_subtracts_future_contributions_and_haircut():
    person = SocialSecurityPerson(age=50, annual_wage=80_000, career_years=28)
    value = social_security_wealth(
        person,
        mode="accrued",
        payable_factor=0.80,
        survival=[1] * 70,
        discount_rate=0.03,
    )

    assert value.net == pytest.approx(
        value.gross_benefits * 0.80 - value.future_employee_contributions
    )


def test_current_recipient_uses_reported_benefit():
    person = SocialSecurityPerson(
        age=70,
        annual_wage=0,
        annual_reported_benefit=24_000,
        career_years=35,
        claiming_age=67,
    )
    value = social_security_wealth(
        person, mode="accrued", payable_factor=1, survival=[1] * 50, discount_rate=0
    )

    assert value.annual_scheduled_benefit == 24_000
    assert value.future_employee_contributions == 0


def test_current_ssi_payment_is_not_treated_as_retired_worker_benefit():
    person = SocialSecurityPerson(
        age=70,
        annual_wage=0,
        annual_reported_benefit=24_000,
        reported_benefit_type="ssi",
        career_years=35,
        claiming_age=67,
    )

    value = social_security_wealth(
        person, mode="accrued", payable_factor=1, survival=[1] * 50, discount_rate=0
    )

    assert value.used_reported_benefit is False
    assert "reported_ssi_benefit_excluded" in value.exclusions


def test_continuation_credits_more_earnings_years_than_accrued():
    person = SocialSecurityPerson(age=40, annual_wage=60_000, career_years=18)
    accrued = social_security_wealth(person, mode="accrued", survival=[1] * 80)
    continuation = social_security_wealth(person, mode="continuation", survival=[1] * 80)

    assert continuation.credited_years > accrued.credited_years
    assert continuation.annual_scheduled_benefit > accrued.annual_scheduled_benefit


def test_former_job_wage_can_proxy_accrued_earnings_history_for_current_non_earner():
    person = SocialSecurityPerson(
        age=50,
        annual_wage=0,
        historical_annual_wage=70_000,
        career_years=28,
    )

    value = social_security_wealth(
        person,
        mode="accrued",
        survival=[1] * 70,
        payable_factor=1,
        discount_rate=0.03,
    )

    assert value.annual_scheduled_benefit > 0
    assert value.future_employee_contributions == 0
    assert "earnings_history_former_job_proxy" in value.exclusions


def test_missing_non_earner_history_is_disclosed_instead_of_presented_as_observed_zero():
    person = SocialSecurityPerson(age=50, annual_wage=0, career_years=28)

    value = social_security_wealth(
        person,
        mode="accrued",
        survival=[1] * 70,
        payable_factor=1,
        discount_rate=0.03,
    )

    assert value.annual_scheduled_benefit == 0
    assert "earnings_history_unestimated" in value.exclusions


def test_reentry_wage_adds_only_future_covered_earnings():
    person = SocialSecurityPerson(
        age=50,
        annual_wage=0,
        historical_annual_wage=0,
        future_annual_wage=20_000,
        career_years=28,
    )

    accrued = social_security_wealth(person, mode="accrued", survival=[1] * 70)
    continuation = social_security_wealth(person, mode="continuation", survival=[1] * 70)

    assert accrued.annual_scheduled_benefit == 0
    assert continuation.annual_scheduled_benefit > 0
    assert continuation.future_employee_contributions > 0


def test_claiming_age_adjustments_have_expected_direction():
    assert claiming_age_factor(62, full_retirement_age=67) < 1
    assert claiming_age_factor(67, full_retirement_age=67) == 1
    assert claiming_age_factor(70, full_retirement_age=67) > 1


def test_social_security_income_stream_starts_at_claiming_age():
    stream = social_security_income_stream(
        SocialSecurityPerson(age=65, annual_wage=60_000, annual_reported_benefit=0, career_years=35),
        survival=[1] * 4,
        payable_factor=0.8,
        retirement_age=67,
    )

    assert stream[:1] == pytest.approx([0])
    assert stream[1:] == pytest.approx([stream[1], stream[1], stream[1]])
    assert stream[1] > 0
