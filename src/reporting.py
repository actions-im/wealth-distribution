from __future__ import annotations

import math

import pandas as pd

from src.formatting import percent
from src.provenance import computed_scf_row_source


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
    weighted_credits = _finite_weighted_total(
        weights,
        values["continuation_expected_inheritance"],
        name="weighted credits",
    )
    weighted_reserves = _finite_weighted_total(
        weights,
        values["continuation_estate_donor_reserve"],
        name="weighted donor reserves",
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
        if isinstance(value, bool) or type(value).__name__ == "bool":
            raise ValueError(f"{column} must be finite and numeric")
        try:
            numeric = float(value)
        except (TypeError, ValueError) as error:
            raise ValueError(f"{column} must be finite and numeric") from error
        if not math.isfinite(numeric):
            raise ValueError(f"{column} must be finite and numeric")
        numeric_values.append(numeric)
    return numeric_values


def _finite_weighted_total(
    weights: list[float], values: list[float], *, name: str
) -> float:
    contributions: list[float] = []
    for weight, value in zip(weights, values, strict=True):
        contribution = weight * value
        if not math.isfinite(contribution):
            raise ValueError(f"{name} must be finite")
        contributions.append(contribution)
    total = math.fsum(contributions)
    if not math.isfinite(total):
        raise ValueError(f"{name} must be finite")
    return total


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

    group_labels = {
        "Bottom 50%": "Bottom 50%",
        "50-90%": "Next 40%",
        "90-99%": "Next 9%",
        "99-99.9%": "Top 1%",
        "Top 0.1%": "Top 1%",
    }
    state_labels = {
        "conventional": "Conventional net worth",
        "continuation": "All modeled future resources",
    }
    working = distribution.loc[distribution["measure"].isin(state_labels)].copy()
    if set(working["measure"]) != set(state_labels):
        raise ValueError("distribution shift requires conventional and continuation measures")
    working["group"] = working["rank_group"].map(group_labels)
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

    from src.real_data import (
        age_group,
        aggregate_ranked_resource_distributions,
    )

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


def build_executive_share_table(distribution: pd.DataFrame) -> pd.DataFrame:
    table = pd.DataFrame(
        {
            "Quantile": distribution["wealth_quantile"],
            "Conventional net-worth share": distribution["traditional_net_worth_share"].map(percent),
            "Net worth plus modeled labor share": distribution["combined_real_wealth_share"].map(percent),
            "Change": distribution["combined_minus_marketable_share"].map(lambda value: percent(value, signed=True)),
            "Source": computed_scf_row_source(),
        }
    )
    return table


def build_detail_wealth_table(distribution: pd.DataFrame) -> pd.DataFrame:
    from src.formatting import dollars_trillions

    table = distribution[
        [
            "wealth_quantile",
            "population_share",
            "household_count",
            "traditional_net_worth_total",
            "human_capital_total",
            "combined_real_wealth_total",
        ]
    ].copy()
    table.columns = [
        "Quantile",
        "Population share",
        "Households",
        "Conventional net worth",
        "Discounted future earnings",
        "Net worth plus modeled labor resources",
    ]
    table["Population share"] = table["Population share"].map(percent)
    table["Households"] = table["Households"].map(lambda value: f"{value / 1_000_000:,.1f}M")
    for column in [
        "Conventional net worth",
        "Discounted future earnings",
        "Net worth plus modeled labor resources",
    ]:
        table[column] = table[column].map(dollars_trillions)
    table["Source"] = computed_scf_row_source()
    return table


def build_fixed_rank_decomposition(
    data: pd.DataFrame,
    *,
    group_column: str,
    component_columns: list[str],
) -> pd.DataFrame:
    """Aggregate components without re-ranking away from conventional net worth."""
    required = {group_column, "household_weight", *component_columns}
    missing = required - set(data.columns)
    if missing:
        raise ValueError(f"fixed-rank decomposition is missing columns: {sorted(missing)}")
    working = data.copy()
    for column in component_columns:
        working[column] = working[column] * working["household_weight"]
    table = working.groupby(group_column, observed=False, sort=False)[component_columns].sum()
    table.attrs["definition"] = (
        "Component decomposition at fixed conventional-net-worth rank; this is not a "
        "metric-specific distribution."
    )
    return table.reset_index()
