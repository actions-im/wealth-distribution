from __future__ import annotations

import math

import pandas as pd

from wealth_report.model.numeric import finite_float, finite_weighted_total, is_boolean_scalar
from wealth_report.report.ranking import (
    DISPLAY_GROUP_LABELS,
    age_group,
    aggregate_ranked_resource_distributions,
)

# Four-bar Home / Age chart order. Labels come from DISPLAY_GROUP_LABELS
# (five analysis quantiles collapse into these four display groups).
SHIFT_GROUP_ORDER = ["Bottom 50%", "Next 40%", "Next 9%", "Top 1%"]
SHIFT_STATE_ORDER = ["Conventional net worth", "All modeled future resources"]
AGE_SHIFT_BUCKETS = ["<25", "25-34", "35-44", "45-54", "55-64", "65+"]

# `math.fsum` minimizes accumulation error; at 2022-dollar national totals these
# tolerances permit only rounding noise, not a material unreserved credit.
INHERITANCE_REALLOCATION_RELATIVE_TOLERANCE = 1e-12
INHERITANCE_REALLOCATION_ABSOLUTE_TOLERANCE = 0.01


def validate_inheritance_reallocation_conservation(data: pd.DataFrame) -> float:
    """Return the weighted inheritance imbalance after verifying conservation.

    Weighted recipient credits and donor reserves must agree within one cent or
    one part in 10^12, whichever tolerance is larger. The allowance covers
    floating-point summation only; it does not permit a material addition to
    national resources.
    """
    required = {
        "household_weight",
        "continuation_expected_inheritance",
        "continuation_estate_donor_reserve",
    }
    missing = required - set(data.columns)
    if missing:
        raise ValueError(
            "inheritance reallocation conservation is missing columns: "
            f"{sorted(missing)}"
        )

    values = {
        column: _finite_numeric_values(data[column], column=column)
        for column in required
    }
    weights = values["household_weight"]
    weighted_credits = finite_weighted_total(
        weights,
        values["continuation_expected_inheritance"],
        name="weighted credits",
        use_fsum=True,
    )
    weighted_reserves = finite_weighted_total(
        weights,
        values["continuation_estate_donor_reserve"],
        name="weighted donor reserves",
        use_fsum=True,
    )
    imbalance = weighted_credits - weighted_reserves
    if not math.isclose(
        weighted_credits,
        weighted_reserves,
        rel_tol=INHERITANCE_REALLOCATION_RELATIVE_TOLERANCE,
        abs_tol=INHERITANCE_REALLOCATION_ABSOLUTE_TOLERANCE,
    ):
        raise ValueError(
            "inheritance reallocation conservation failed: weighted credits "
            f"({weighted_credits:.12g}) differ from weighted donor reserves "
            f"({weighted_reserves:.12g}) by {imbalance:.12g}"
        )
    return imbalance


def _finite_numeric_values(values: pd.Series, *, column: str) -> list[float]:
    numeric_values: list[float] = []
    for value in values:
        if is_boolean_scalar(value):
            raise ValueError(f"{column} must be finite and numeric")
        numeric = finite_float(value)
        if numeric is None:
            raise ValueError(f"{column} must be finite and numeric")
        if numeric < 0:
            raise ValueError(f"{column} must be nonnegative")
        numeric_values.append(numeric)
    return numeric_values


def build_distribution_shift_data(distribution: pd.DataFrame) -> pd.DataFrame:
    """Collapse metric-specific distributions into the two-state headline view."""
    required = {
        "measure",
        "rank_group",
        "wealth_share",
        "weighted_total",
        "household_share",
    }
    missing = required - set(distribution.columns)
    if missing:
        raise ValueError(f"distribution shift data is missing columns: {sorted(missing)}")

    state_labels = {
        "conventional": "Conventional net worth",
        "continuation": "All modeled future resources",
    }
    working = distribution.loc[distribution["measure"].isin(state_labels)].copy()
    if set(working["measure"]) != set(state_labels):
        raise ValueError("distribution shift requires conventional and continuation measures")
    working["group"] = working["rank_group"].map(DISPLAY_GROUP_LABELS)
    if working["group"].isna().any():
        unsupported = sorted(working.loc[working["group"].isna(), "rank_group"].unique())
        raise ValueError(f"unsupported rank groups: {unsupported}")
    working["state"] = working["measure"].map(state_labels)
    working["rank_basis"] = working.get(
        "rank_basis",
        working["measure"].map(
            {"conventional": "net_worth", "continuation": "continuation_resources"}
        ),
    )

    grouped = (
        working.groupby(["group", "state"], as_index=False, observed=True)
        .agg(
            share=("wealth_share", "sum"),
            weighted_total=("weighted_total", "sum"),
            household_share=("household_share", "sum"),
            rank_basis=("rank_basis", "first"),
        )
    )
    comparison = grouped.pivot(index="group", columns="state", values="share")
    grouped["conventional_share"] = grouped["group"].map(
        comparison["Conventional net worth"]
    )
    grouped["future_resources_share"] = grouped["group"].map(
        comparison["All modeled future resources"]
    )
    grouped["change_pp"] = 100 * (
        grouped["future_resources_share"] - grouped["conventional_share"]
    )
    grouped["group"] = pd.Categorical(
        grouped["group"], categories=SHIFT_GROUP_ORDER, ordered=True
    )
    grouped["state"] = pd.Categorical(
        grouped["state"], categories=SHIFT_STATE_ORDER, ordered=True
    )
    return grouped.sort_values(["group", "state"]).reset_index(drop=True)


def build_age_distribution_shift_data(data: pd.DataFrame) -> pd.DataFrame:
    """Build independently ranked distribution shifts within respondent-age buckets."""
    required = {
        "household_id",
        "household_weight",
        "age",
        "net_worth",
        "defensive_resources",
        "continuation_resources",
    }
    missing = required - set(data.columns)
    if missing:
        raise ValueError(f"age distribution data is missing columns: {sorted(missing)}")

    working = data.copy()
    working["age_group"] = pd.Categorical(
        working["age"].map(lambda age: "65+" if age >= 65 else age_group(age)),
        categories=AGE_SHIFT_BUCKETS,
        ordered=True,
    )
    tables: list[pd.DataFrame] = []
    for bucket in AGE_SHIFT_BUCKETS:
        bucket_data = working.loc[working["age_group"] == bucket].copy()
        if bucket_data.empty:
            continue
        shift = build_distribution_shift_data(
            aggregate_ranked_resource_distributions(bucket_data)
        )
        shift["age_group"] = bucket
        shift["weighted_family_count"] = bucket_data["household_weight"].sum()
        shift["all_resources_total"] = (
            bucket_data["continuation_resources"] * bucket_data["household_weight"]
        ).sum()
        tables.append(shift)
    if not tables:
        raise ValueError("age distribution data has no non-empty age buckets")
    result = pd.concat(tables, ignore_index=True)
    result["age_group"] = pd.Categorical(
        result["age_group"], categories=AGE_SHIFT_BUCKETS, ordered=True
    )
    return result.sort_values(["age_group", "group", "state"]).reset_index(drop=True)


