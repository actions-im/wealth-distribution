import pytest
import pandas as pd

from wealth_report.report.distribution import (
    validate_inheritance_reallocation_conservation,
    build_age_distribution_shift_data,
    build_distribution_shift_data,
)


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


def test_inheritance_reallocation_conservation_accepts_equal_weighted_components():
    data = pd.DataFrame(
        {
            "household_weight": [2.0, 3.0],
            "continuation_expected_inheritance": [30.0, 20.0],
            "continuation_estate_donor_reserve": [45.0, 10.0],
        }
    )

    imbalance = validate_inheritance_reallocation_conservation(data)

    assert imbalance == pytest.approx(0.0)


def test_inheritance_reallocation_conservation_rejects_mismatched_components():
    data = pd.DataFrame(
        {
            "household_weight": [1.0, 1.0],
            "continuation_expected_inheritance": [10.0, 20.0],
            "continuation_estate_donor_reserve": [10.0, 19.0],
        }
    )

    with pytest.raises(ValueError, match="conservation failed"):
        validate_inheritance_reallocation_conservation(data)


def test_inheritance_reallocation_conservation_rejects_nonfinite_weighted_total():
    data = pd.DataFrame(
        {
            "household_weight": [1e308],
            "continuation_expected_inheritance": [1e308],
            "continuation_estate_donor_reserve": [1e308],
        }
    )

    with pytest.raises(ValueError, match="weighted credits must be finite"):
        validate_inheritance_reallocation_conservation(data)


@pytest.mark.parametrize(
    ("column", "message"),
    [
        ("household_weight", "household_weight must be finite and numeric"),
        (
            "continuation_expected_inheritance",
            "continuation_expected_inheritance must be finite and numeric",
        ),
        (
            "continuation_estate_donor_reserve",
            "continuation_estate_donor_reserve must be finite and numeric",
        ),
    ],
)
def test_inheritance_reallocation_conservation_rejects_nonfinite_inputs(column, message):
    data = pd.DataFrame(
        {
            "household_weight": [1.0],
            "continuation_expected_inheritance": [10.0],
            "continuation_estate_donor_reserve": [10.0],
        }
    )
    data.loc[0, column] = float("nan")

    with pytest.raises(ValueError, match=message):
        validate_inheritance_reallocation_conservation(data)


@pytest.mark.parametrize(
    "column",
    [
        "household_weight",
        "continuation_expected_inheritance",
        "continuation_estate_donor_reserve",
    ],
)
def test_inheritance_reallocation_conservation_rejects_negative_inputs(column):
    data = pd.DataFrame(
        {
            "household_weight": [1.0],
            "continuation_expected_inheritance": [10.0],
            "continuation_estate_donor_reserve": [10.0],
        }
    )
    data.loc[0, column] = -1.0

    with pytest.raises(ValueError, match=f"{column} must be nonnegative"):
        validate_inheritance_reallocation_conservation(data)


def test_inheritance_reallocation_conservation_rejects_missing_component():
    data = pd.DataFrame(
        {
            "household_weight": [1.0],
            "continuation_expected_inheritance": [10.0],
        }
    )

    with pytest.raises(ValueError, match="continuation_estate_donor_reserve"):
        validate_inheritance_reallocation_conservation(data)


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
