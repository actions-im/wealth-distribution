import pytest

from wealth_report.model.pensions import (
    DefinedBenefitPlan,
    defined_benefit_wealth,
    defined_benefit_income_stream,
    real_growth_from_cola,
    value_defined_benefit_plan,
)


def test_reported_cola_preserves_real_benefit_while_fixed_nominal_benefit_declines():
    assert real_growth_from_cola(True, inflation_rate=0.02) == 0
    assert real_growth_from_cola(False, inflation_rate=0.02) == pytest.approx(
        1 / 1.02 - 1
    )
    assert real_growth_from_cola(None, inflation_rate=0.02) == pytest.approx(
        1 / 1.02 - 1
    )


def test_fixed_nominal_db_has_lower_real_value_than_reported_cola_plan():
    cola_plan = DefinedBenefitPlan(
        annual_benefit=20_000,
        current_age=65,
        claiming_age=65,
        real_cola=real_growth_from_cola(True, inflation_rate=0.02),
    )
    nominal_plan = DefinedBenefitPlan(
        annual_benefit=20_000,
        current_age=65,
        claiming_age=65,
        real_cola=real_growth_from_cola(False, inflation_rate=0.02),
    )

    cola = value_defined_benefit_plan(
        cola_plan, mode="continuation", survival=[1] * 30, discount_rate=0.03
    )
    nominal = value_defined_benefit_plan(
        nominal_plan, mode="continuation", survival=[1] * 30, discount_rate=0.03
    )

    assert nominal.present_value < cola.present_value


def test_db_income_stream_applies_real_cola_after_benefits_start():
    plan = DefinedBenefitPlan(
        annual_benefit=12_000,
        current_age=64,
        claiming_age=66,
        real_cola=1 / 1.02 - 1,
    )

    stream = defined_benefit_income_stream(plan, mode="continuation", years=4)

    assert stream[0] == 0
    assert stream[1] == pytest.approx(12_000 / 1.02**2)
    assert stream[2] == pytest.approx(12_000 / 1.02**3)
    assert stream[3] == pytest.approx(12_000 / 1.02**4)


def test_deferred_fixed_nominal_benefit_erodes_before_claiming():
    value = defined_benefit_wealth(
        annual_benefit=12_000,
        current_age=55,
        claiming_age=65,
        survival=[1] * 30,
        discount_rate=0,
        real_cola=1 / 1.02 - 1,
    )

    expected = sum(12_000 / 1.02**period for period in range(10, 31))
    assert value == pytest.approx(expected)


def test_db_annuity_is_survival_weighted_from_claiming_age():
    value = defined_benefit_wealth(
        annual_benefit=24_000,
        current_age=55,
        claiming_age=65,
        survival=[1] * 10 + [0.9] * 30,
        discount_rate=0.03,
    )

    assert 0 < value < 24_000 * 40


def test_accrued_db_applies_reported_or_explicit_accrual_fraction():
    plan = DefinedBenefitPlan(
        annual_benefit=30_000,
        current_age=50,
        claiming_age=65,
        accrued_fraction=0.6,
    )
    accrued = value_defined_benefit_plan(plan, mode="accrued", survival=[1] * 60)
    continuation = value_defined_benefit_plan(plan, mode="continuation", survival=[1] * 60)

    assert accrued.annual_benefit == 18_000
    assert continuation.annual_benefit == 30_000
    assert accrued.present_value < continuation.present_value


def test_account_type_plan_is_excluded_from_incremental_db_wealth():
    plan = DefinedBenefitPlan(
        annual_benefit=30_000,
        current_age=50,
        claiming_age=65,
        account_type=True,
        account_balance=200_000,
    )
    value = value_defined_benefit_plan(plan, mode="continuation", survival=[1] * 60)

    assert value.present_value == 0
    assert value.excluded_account_balance == 200_000
    assert "account_balance_already_in_net_worth" in value.exclusions


def test_survivor_fraction_is_disclosed_but_not_imputed_without_joint_curve():
    plan = DefinedBenefitPlan(
        annual_benefit=30_000,
        current_age=60,
        claiming_age=65,
        survivor_fraction=0.5,
    )
    value = value_defined_benefit_plan(plan, mode="continuation", survival=[1] * 50)

    assert "survivor_annuity_without_joint_survival_curve" in value.exclusions


def test_db_income_stream_starts_at_claiming_age():
    plan = DefinedBenefitPlan(annual_benefit=12_000, current_age=64, claiming_age=66)

    assert defined_benefit_income_stream(plan, mode="continuation", years=4) == [
        0,
        12_000,
        12_000,
        12_000,
    ]
