from wealth_report.model.pensions import (
    DefinedBenefitPlan,
    defined_benefit_wealth,
    defined_benefit_income_stream,
    value_defined_benefit_plan,
)


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
