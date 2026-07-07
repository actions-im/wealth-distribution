import pytest

from src.sample_data import (
    AGE_POPULATION_SHARE,
    PLACEHOLDER_HOUSEHOLD_COUNT,
    QUANTILE_POPULATION_SHARE,
    aggregate_country_distribution_by_quantile,
    build_sample_household_data,
)


def test_sample_data_contains_report_metrics():
    data = build_sample_household_data(
        discount_rate=0.035,
        wage_growth=0.015,
        retirement_age=67,
        employment_probability=0.95,
        tax_rate=0.0,
        liquidity_weight=0.25,
    )

    expected_columns = {
        "age_group",
        "age",
        "wealth_quantile",
        "traditional_net_worth",
        "labor_income",
        "human_capital",
        "combined_real_wealth",
        "liquidity_adjusted_real_wealth",
    }
    assert expected_columns.issubset(data.columns)
    assert len(data) == 35
    assert (data["combined_real_wealth"] >= data["traditional_net_worth"]).all()


def test_population_share_assumptions_sum_to_one():
    assert sum(AGE_POPULATION_SHARE.values()) == pytest.approx(1.0)
    assert sum(QUANTILE_POPULATION_SHARE.values()) == pytest.approx(1.0)


def test_country_distribution_shares_sum_to_one_for_each_metric():
    data = build_sample_household_data(
        discount_rate=0.035,
        wage_growth=0.015,
        retirement_age=67,
        employment_probability=0.95,
        tax_rate=0.0,
        liquidity_weight=0.25,
    )
    distribution = aggregate_country_distribution_by_quantile(data)

    assert distribution["population_share"].sum() == pytest.approx(1.0)
    for column in [
        "traditional_net_worth_share",
        "human_capital_share",
        "combined_real_wealth_share",
        "liquidity_adjusted_real_wealth_share",
    ]:
        assert distribution[column].sum() == pytest.approx(1.0)


def test_country_distribution_totals_are_scaled_to_household_count():
    data = build_sample_household_data(
        discount_rate=0.035,
        wage_growth=0.015,
        retirement_age=67,
        employment_probability=0.95,
        tax_rate=0.0,
        liquidity_weight=0.25,
    )
    distribution = aggregate_country_distribution_by_quantile(data)
    bottom_50 = distribution.loc[distribution["wealth_quantile"] == "Bottom 50%"].iloc[0]
    sample_bottom_50 = data[data["wealth_quantile"] == "Bottom 50%"].copy()
    expected_total = (
        sample_bottom_50["traditional_net_worth"]
        * sample_bottom_50["household_population_share"]
        * PLACEHOLDER_HOUSEHOLD_COUNT
    ).sum()

    assert bottom_50["household_count"] == pytest.approx(PLACEHOLDER_HOUSEHOLD_COUNT * 0.5)
    assert bottom_50["traditional_net_worth_total"] == pytest.approx(expected_total)


def test_combined_real_wealth_is_less_top_one_concentrated_than_traditional_wealth():
    data = build_sample_household_data(
        discount_rate=0.035,
        wage_growth=0.015,
        retirement_age=67,
        employment_probability=0.95,
        tax_rate=0.0,
        liquidity_weight=0.25,
    )
    distribution = aggregate_country_distribution_by_quantile(data)
    top_one = distribution[distribution["wealth_quantile"].isin(["99-99.9%", "Top 0.1%"])]

    traditional_top_one = top_one["traditional_net_worth_share"].sum()
    combined_top_one = top_one["combined_real_wealth_share"].sum()
    bottom_ninety_combined = distribution.loc[
        distribution["wealth_quantile"].isin(["Bottom 50%", "50-90%"]),
        "combined_real_wealth_share",
    ].sum()

    assert traditional_top_one > 0.35
    assert combined_top_one < traditional_top_one
    assert bottom_ninety_combined > 0.5
