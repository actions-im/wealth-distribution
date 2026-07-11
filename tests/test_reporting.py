import pandas as pd

from src.reporting import build_executive_share_table, build_fixed_rank_decomposition
from src.real_data import (
    aggregate_real_country_distribution_by_quantile,
    build_real_wealth_household_data,
)


def test_executive_share_table_uses_neutral_measure_names():
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
    distribution = aggregate_real_country_distribution_by_quantile(data)

    table = build_executive_share_table(distribution)

    assert list(table.columns) == [
        "Quantile",
        "Conventional net-worth share",
        "Net worth plus modeled labor share",
        "Change",
        "Source",
    ]
    assert table.loc[0, "Conventional net-worth share"].endswith("%")
    assert table.loc[0, "Net worth plus modeled labor share"].endswith("%")
    assert table["Change"].str.endswith("%").all()
    assert table["Source"].str.contains("SCF").all()


def test_fixed_rank_view_is_labeled_as_decomposition():
    data = pd.DataFrame(
        {
            "conventional_rank_group": ["Bottom 90%", "Top 10%"],
            "household_weight": [9, 1],
            "net_worth": [10, 100],
            "accrued_labor": [50, 1],
        }
    )
    table = build_fixed_rank_decomposition(
        data,
        group_column="conventional_rank_group",
        component_columns=["net_worth", "accrued_labor"],
    )

    assert "conventional-net-worth rank" in table.attrs["definition"]
