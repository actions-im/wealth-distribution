import pytest
import pandas as pd

from src.real_data import (
    ComprehensiveHouseholdInput,
    apply_inheritance_reallocation,
    aggregate_real_country_distribution_by_quantile,
    build_comprehensive_household,
    build_ranked_distributions,
    build_real_wealth_household_data,
    value_detailed_household,
)
from src.config import ModelAssumptions
from src.scf_detailed import DetailedHouseholdInput, PersonInput


def test_real_household_data_assigns_weighted_scf_quantiles():
    raw_rows = _raw_scf_rows()

    data = build_real_wealth_household_data(
        raw_rows,
        discount_rate=0.035,
        wage_growth=0.015,
        retirement_age=67,
        employment_probability=1.0,
        tax_rate=0.0,
        liquidity_weight=0.25,
    )

    assert data["household_weight"].sum() == pytest.approx(1_000)
    assert set(data["wealth_quantile"]) == {
        "Bottom 50%",
        "50-90%",
        "90-99%",
        "99-99.9%",
        "Top 0.1%",
    }
    assert data.loc[data["scf_row_id"] == 1, "wealth_quantile"].item() == "Bottom 50%"
    assert data.loc[data["scf_row_id"] == 5, "wealth_quantile"].item() == "Top 0.1%"


def test_real_country_distribution_uses_weighted_totals_and_shares():
    data = build_real_wealth_household_data(
        _raw_scf_rows(),
        discount_rate=0.035,
        wage_growth=0.015,
        retirement_age=67,
        employment_probability=1.0,
        tax_rate=0.0,
        liquidity_weight=0.25,
    )

    distribution = aggregate_real_country_distribution_by_quantile(data)
    bottom_50 = distribution.loc[distribution["wealth_quantile"] == "Bottom 50%"].iloc[0]

    assert distribution["household_count"].sum() == pytest.approx(1_000)
    assert distribution["population_share"].sum() == pytest.approx(1.0)
    assert bottom_50["traditional_net_worth_total"] == pytest.approx(15_000_000)
    for column in [
        "traditional_net_worth_share",
        "human_capital_share",
        "combined_real_wealth_share",
        "liquidity_adjusted_real_wealth_share",
    ]:
        assert distribution[column].sum() == pytest.approx(1.0)


def test_real_country_distribution_is_ordered_bottom_to_top():
    data = build_real_wealth_household_data(
        list(reversed(_raw_scf_rows())),
        discount_rate=0.035,
        wage_growth=0.015,
        retirement_age=67,
        employment_probability=1.0,
        tax_rate=0.0,
        liquidity_weight=0.25,
    )

    distribution = aggregate_real_country_distribution_by_quantile(data)

    assert distribution["wealth_quantile"].tolist() == [
        "Bottom 50%",
        "50-90%",
        "90-99%",
        "99-99.9%",
        "Top 0.1%",
    ]


def test_discounted_wage_income_reduces_top_concentration():
    data = build_real_wealth_household_data(
        _raw_scf_rows(),
        discount_rate=0.035,
        wage_growth=0.015,
        retirement_age=67,
        employment_probability=1.0,
        tax_rate=0.0,
        liquidity_weight=0.25,
    )

    distribution = aggregate_real_country_distribution_by_quantile(data)
    top_one = distribution[distribution["wealth_quantile"].isin(["99-99.9%", "Top 0.1%"])]

    assert top_one["combined_real_wealth_share"].sum() < top_one["traditional_net_worth_share"].sum()


def test_comprehensive_resources_equal_documented_components():
    row = build_comprehensive_household(
        ComprehensiveHouseholdInput(
            net_worth=100,
            accrued_labor=20,
            continuation_labor=40,
            accrued_social_security=30,
            continuation_social_security=50,
            accrued_db_pension=10,
            continuation_db_pension=15,
        )
    )

    assert row.defensive_resources == pytest.approx(
        row.net_worth + row.accrued_labor + row.accrued_social_security + row.accrued_db_pension
    )
    assert row.continuation_resources == pytest.approx(
        row.net_worth
        + row.continuation_labor
        + row.continuation_social_security
        + row.continuation_db_pension
    )


def test_comprehensive_resources_include_income_security_floor_separately():
    row = build_comprehensive_household(
        ComprehensiveHouseholdInput(
            net_worth=100,
            accrued_labor=20,
            continuation_labor=40,
            accrued_social_security=30,
            continuation_social_security=50,
            accrued_db_pension=10,
            continuation_db_pension=15,
            continuation_income_security_floor=5,
        )
    )

    assert row.continuation_income_security_floor == 5
    assert row.continuation_resources == pytest.approx(210)


def test_default_comprehensive_household_keeps_prior_totals_without_inheritance():
    row = build_comprehensive_household(
        ComprehensiveHouseholdInput(
            net_worth=100,
            accrued_labor=20,
            continuation_labor=40,
            accrued_social_security=30,
            continuation_social_security=50,
            accrued_db_pension=10,
            continuation_db_pension=15,
        )
    )

    assert row.continuation_expected_inheritance == 0
    assert row.continuation_estate_donor_reserve == 0
    assert row.defensive_resources == pytest.approx(160)
    assert row.continuation_resources == pytest.approx(205)


def test_inheritance_reallocation_updates_only_continuation_resources():
    households = _inheritance_households()
    original_components = households[
        [
            "net_worth",
            "continuation_labor",
            "continuation_social_security",
            "continuation_db_pension",
            "continuation_income_security_floor",
        ]
    ].copy()

    result = apply_inheritance_reallocation(
        households,
        life_table=_inheritance_life_table(),
        assumptions=ModelAssumptions(inheritance_horizon_years=5),
    )

    weighted_credits = (
        result["household_weight"] * result["continuation_expected_inheritance"]
    ).sum()
    weighted_reserves = (
        result["household_weight"] * result["continuation_estate_donor_reserve"]
    ).sum()
    assert weighted_credits == pytest.approx(weighted_reserves)
    pd.testing.assert_frame_equal(result[original_components.columns], original_components)
    assert {
        "inheritance_claim",
        "inheritance_credit",
        "estate_donor_capacity",
        "estate_donor_reserve",
        "inheritance_reallocation",
    }.issubset(result.columns)

    expected_continuation = (
        original_components["net_worth"]
        + original_components["continuation_labor"]
        + original_components["continuation_social_security"]
        + original_components["continuation_db_pension"]
        + original_components["continuation_income_security_floor"]
        + result["continuation_expected_inheritance"]
        - result["continuation_estate_donor_reserve"]
    )
    assert result["continuation_resources"].tolist() == pytest.approx(
        expected_continuation.tolist()
    )
    assert result["defensive_resources"].tolist() == households[
        "defensive_resources"
    ].tolist()


@pytest.mark.parametrize(
    ("component", "invalid_value"),
    [
        (component, invalid_value)
        for component in (
            "net_worth",
            "continuation_labor",
            "continuation_social_security",
            "continuation_db_pension",
            "continuation_income_security_floor",
        )
        for invalid_value in ("not-a-number", float("nan"), float("inf"), -float("inf"))
    ],
)
def test_inheritance_reallocation_rejects_invalid_continuation_components(
    component, invalid_value
):
    households = _inheritance_households()
    households[component] = households[component].astype(object)
    households.loc[0, component] = invalid_value

    with pytest.raises(ValueError, match=component):
        apply_inheritance_reallocation(
            households,
            life_table=_inheritance_life_table(),
            assumptions=ModelAssumptions(inheritance_horizon_years=5),
        )


def test_inheritance_reallocation_rejects_missing_continuation_component():
    households = _inheritance_households().drop(columns=["continuation_db_pension"])

    with pytest.raises(ValueError, match="continuation_db_pension"):
        apply_inheritance_reallocation(
            households,
            life_table=_inheritance_life_table(),
            assumptions=ModelAssumptions(inheritance_horizon_years=5),
        )


def test_invalid_probability_is_rejected():
    with pytest.raises(ValueError, match="employment_probability"):
        ModelAssumptions(employment_probability=1.2)


def test_model_assumptions_reject_nonpositive_real_discount_factor():
    with pytest.raises(ValueError, match="discount_rate"):
        ModelAssumptions(discount_rate=-1)


def test_inheritance_horizon_is_validated():
    assert ModelAssumptions(inheritance_horizon_years=15).inheritance_horizon_years == 15

    for value in (4, 31):
        with pytest.raises(ValueError, match="inheritance_horizon_years"):
            ModelAssumptions(inheritance_horizon_years=value)


def test_each_distribution_ranks_by_its_own_metric():
    data = pd.DataFrame(
        {
            "household_id": [1, 2, 3, 4],
            "household_weight": [1, 1, 1, 1],
            "net_worth": [0, 10, 20, 100],
            "defensive_resources": [0, 10, 200, 100],
            "continuation_resources": [0, 10, 300, 100],
        }
    )
    result = build_ranked_distributions(data)

    conventional_top = result["conventional"].sort_values("rank_position").iloc[-1]["household_id"]
    defensive_top = result["defensive"].sort_values("rank_position").iloc[-1]["household_id"]
    assert conventional_top != defensive_top


def test_working_age_non_earner_uses_scf_calibrated_reentry_wage():
    household = DetailedHouseholdInput(
        row_id=1,
        family_id=1,
        implicate=1,
        respondent=PersonInput(age=30, sex="female", annual_wage=0, annual_social_security=0),
        spouse=None,
        db_pensions=(),
    )

    value = value_detailed_household(
        net_worth=0,
        household=household,
        life_table=_life_table(),
        assumptions=ModelAssumptions(reentry_probability=0.25),
        reentry_wage_schedule={("female", "25-34"): 40_000},
    )

    assert value.continuation_labor > 0


def test_retired_non_earner_does_not_receive_reentry_labor_income():
    household = DetailedHouseholdInput(
        row_id=1,
        family_id=1,
        implicate=1,
        respondent=PersonInput(age=70, sex="female", annual_wage=0, annual_social_security=0),
        spouse=None,
        db_pensions=(),
    )

    value = value_detailed_household(
        net_worth=0,
        household=household,
        life_table=_life_table(),
        assumptions=ModelAssumptions(retirement_age=67),
        reentry_wage_schedule={("female", "65-74"): 40_000},
    )

    assert value.continuation_labor == 0


def test_high_income_stream_does_not_receive_income_security_top_up():
    household = DetailedHouseholdInput(
        row_id=1,
        family_id=1,
        implicate=1,
        respondent=PersonInput(
            age=30, sex="female", annual_wage=100_000, annual_social_security=0
        ),
        spouse=None,
        db_pensions=(),
    )

    value = value_detailed_household(
        net_worth=0,
        household=household,
        life_table=_life_table(),
        assumptions=ModelAssumptions(income_security_floor_monthly=622),
    )

    assert value.continuation_income_security_floor == 0


def _life_table():
    return {sex: {age: 1.0 for age in range(0, 121)} for sex in ("female", "male")}


def _inheritance_life_table():
    return {
        "female": {age: 100.0 - 3.0 * (age - 40) for age in range(40, 66)},
    }


def _inheritance_households():
    return pd.DataFrame(
        [
            {
                "household_id": 1,
                "household_weight": 2.0,
                "net_worth": 0.0,
                "age": 40,
                "sex": "female",
                "expected_inheritance_amount": 1_000.0,
                "expects_sizable_estate": False,
                "continuation_labor": 10.0,
                "continuation_social_security": 20.0,
                "continuation_db_pension": 30.0,
                "continuation_income_security_floor": 40.0,
                "defensive_resources": 60.0,
                "continuation_resources": 100.0,
            },
            {
                "household_id": 2,
                "household_weight": 3.0,
                "net_worth": 1_000.0,
                "age": 60,
                "sex": "female",
                "expected_inheritance_amount": 0.0,
                "expects_sizable_estate": True,
                "continuation_labor": 1.0,
                "continuation_social_security": 2.0,
                "continuation_db_pension": 3.0,
                "continuation_income_security_floor": 4.0,
                "defensive_resources": 80.0,
                "continuation_resources": 1_010.0,
            },
        ]
    )


def _raw_scf_rows():
    return [
        {"scf_row_id": 1, "wgt": 500, "age": 30, "wageinc": 55_000, "networth": 30_000},
        {"scf_row_id": 2, "wgt": 400, "age": 40, "wageinc": 90_000, "networth": 200_000},
        {"scf_row_id": 3, "wgt": 90, "age": 50, "wageinc": 160_000, "networth": 2_000_000},
        {"scf_row_id": 4, "wgt": 9, "age": 55, "wageinc": 200_000, "networth": 15_000_000},
        {"scf_row_id": 5, "wgt": 1, "age": 60, "wageinc": 250_000, "networth": 200_000_000},
    ]
