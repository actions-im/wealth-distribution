import pytest

from src.real_data import (
    aggregate_real_country_distribution_by_quantile,
    build_real_wealth_household_data,
)


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


def _raw_scf_rows():
    return [
        {"scf_row_id": 1, "wgt": 500, "age": 30, "wageinc": 55_000, "networth": 30_000},
        {"scf_row_id": 2, "wgt": 400, "age": 40, "wageinc": 90_000, "networth": 200_000},
        {"scf_row_id": 3, "wgt": 90, "age": 50, "wageinc": 160_000, "networth": 2_000_000},
        {"scf_row_id": 4, "wgt": 9, "age": 55, "wageinc": 200_000, "networth": 15_000_000},
        {"scf_row_id": 5, "wgt": 1, "age": 60, "wageinc": 250_000, "networth": 200_000_000},
    ]
