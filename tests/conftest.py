import pytest

from src.real_data import (
    aggregate_real_country_distribution_by_quantile,
    build_real_wealth_household_data,
)


@pytest.fixture
def real_distribution():
    data = build_real_wealth_household_data(
        [
            {"wgt": 500, "age": 30, "wageinc": 55_000, "networth": 30_000},
            {"wgt": 400, "age": 40, "wageinc": 90_000, "networth": 200_000},
            {"wgt": 90, "age": 50, "wageinc": 160_000, "networth": 2_000_000},
            {"wgt": 9, "age": 55, "wageinc": 200_000, "networth": 15_000_000},
            {"wgt": 1, "age": 60, "wageinc": 250_000, "networth": 200_000_000},
        ],
        discount_rate=0.035,
        wage_growth=0.015,
        retirement_age=67,
        employment_probability=0.95,
        tax_rate=0.0,
        liquidity_weight=0.25,
    )
    return aggregate_real_country_distribution_by_quantile(data)
