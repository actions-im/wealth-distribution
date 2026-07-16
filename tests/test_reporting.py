import pytest
import pandas as pd

from src.reporting import (
    build_age_distribution_shift_data,
    build_distribution_shift_data,
    build_executive_share_table,
    build_fixed_rank_decomposition,
)
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


def test_distribution_shift_collapses_to_four_groups_and_two_states():
    shift = build_distribution_shift_data(_metric_specific_distribution())

    assert shift["group"].drop_duplicates().tolist() == [
        "Bottom 50%",
        "Next 40%",
        "Next 9%",
        "Top 1%",
    ]
    assert shift["state"].drop_duplicates().tolist() == [
        "Conventional net worth",
        "All modeled future resources",
    ]
    assert shift.groupby("state", observed=True)["share"].sum().tolist() == pytest.approx(
        [1, 1]
    )


def test_distribution_shift_combines_top_one_and_calculates_change():
    shift = build_distribution_shift_data(_metric_specific_distribution())
    top = shift.loc[shift["group"] == "Top 1%"].set_index("state")

    assert top.loc["Conventional net worth", "share"] == pytest.approx(0.35)
    assert top.loc["All modeled future resources", "share"] == pytest.approx(0.19)
    assert top.loc["All modeled future resources", "change_pp"] == pytest.approx(-16.0)
    assert top.loc["Conventional net worth", "weighted_total"] == 350


def test_age_distribution_shift_ranks_each_age_bucket_independently():
    data = pd.DataFrame(
        {
            "household_id": list(range(1, 21)),
            "household_weight": [1.0] * 20,
            "age": [30] * 10 + [70] * 10,
            "net_worth": list(range(10, 110, 10)) * 2,
            "continuation_resources": list(range(100, 0, -10))
            + list(range(10, 110, 10)),
            "defensive_resources": list(range(10, 210, 10)),
        }
    )

    result = build_age_distribution_shift_data(data)

    assert result["age_group"].drop_duplicates().tolist() == ["25-34", "65+"]
    assert set(result["state"]) == {
        "Conventional net worth",
        "All modeled future resources",
    }
    assert set(result["group"]) == {"Bottom 50%", "Next 40%", "Next 9%", "Top 1%"}
    shares = result.groupby(["age_group", "state"], observed=True)["share"].sum()
    assert shares.tolist() == pytest.approx([1, 1, 1, 1])


def _metric_specific_distribution():
    rows = []
    values = {
        "conventional": [0.02, 0.24, 0.39, 0.20, 0.15],
        "continuation": [0.10, 0.40, 0.31, 0.12, 0.07],
    }
    groups = ["Bottom 50%", "50-90%", "90-99%", "99-99.9%", "Top 0.1%"]
    for measure, shares in values.items():
        for group, share in zip(groups, shares, strict=True):
            rows.append(
                {
                    "measure": measure,
                    "rank_group": group,
                    "wealth_share": share,
                    "weighted_total": share * 1_000,
                    "household_share": {
                        "Bottom 50%": 0.50,
                        "50-90%": 0.40,
                        "90-99%": 0.09,
                        "99-99.9%": 0.009,
                        "Top 0.1%": 0.001,
                    }[group],
                }
            )
    return pd.DataFrame(rows)
