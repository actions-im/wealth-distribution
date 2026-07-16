import pytest
import pandas as pd

from src.real_data import (
    ComprehensiveHouseholdInput,
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


def test_invalid_probability_is_rejected():
    with pytest.raises(ValueError, match="employment_probability"):
        ModelAssumptions(employment_probability=1.2)


def test_model_assumptions_reject_nonpositive_real_discount_factor():
    with pytest.raises(ValueError, match="discount_rate"):
        ModelAssumptions(discount_rate=-1)


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


def _life_table():
    return {sex: {age: 1.0 for age in range(0, 121)} for sex in ("female", "male")}


def _raw_scf_rows():
    return [
        {"scf_row_id": 1, "wgt": 500, "age": 30, "wageinc": 55_000, "networth": 30_000},
        {"scf_row_id": 2, "wgt": 400, "age": 40, "wageinc": 90_000, "networth": 200_000},
        {"scf_row_id": 3, "wgt": 90, "age": 50, "wageinc": 160_000, "networth": 2_000_000},
        {"scf_row_id": 4, "wgt": 9, "age": 55, "wageinc": 200_000, "networth": 15_000_000},
        {"scf_row_id": 5, "wgt": 1, "age": 60, "wageinc": 250_000, "networth": 200_000_000},
    ]
