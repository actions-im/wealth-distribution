"""Independent ranking and age/sex grouping for resource measures."""

from __future__ import annotations

import pandas as pd

from wealth_report.model.statistics import weighted_rank_groups, weighted_rank_positions


# Five analysis quantiles used for ranking and export.
# The Home chart collapses the top two into a single "Top 1%" bar via
# DISPLAY_GROUP_LABELS below — keep that map aligned with SHIFT_GROUP_ORDER
# in distribution.py.
WEALTH_QUANTILE_GROUPS = [
    ("Bottom 50%", 0.0, 0.5),
    ("50-90%", 0.5, 0.9),
    ("90-99%", 0.9, 0.99),
    ("99-99.9%", 0.99, 0.999),
    ("Top 0.1%", 0.999, 1.0),
]

# Map analysis rank groups → four-bar chart labels (must stay in sync with
# wealth_report.report.distribution.SHIFT_GROUP_ORDER).
DISPLAY_GROUP_LABELS = {
    "Bottom 50%": "Bottom 50%",
    "50-90%": "Next 40%",
    "90-99%": "Next 9%",
    "99-99.9%": "Top 1%",
    "Top 0.1%": "Top 1%",
}

DEFAULT_RESOURCE_METRICS = {
    "conventional": "net_worth",
    "defensive": "defensive_resources",
    "continuation": "continuation_resources",
}


def age_group(age: int | float) -> str:
    """Respondent-age bucket used for re-entry wages and age-sliced views."""
    if age < 25:
        return "<25"
    if age < 35:
        return "25-34"
    if age < 45:
        return "35-44"
    if age < 55:
        return "45-54"
    if age < 65:
        return "55-64"
    if age < 75:
        return "65-74"
    return "75+"


def build_ranked_distributions(
    data: pd.DataFrame,
    *,
    metrics: dict[str, str] | None = None,
) -> dict[str, pd.DataFrame]:
    """Rank each reported resource measure by itself, never by a shared proxy."""
    metrics = metrics or dict(DEFAULT_RESOURCE_METRICS)
    required = {"household_id", "household_weight", *metrics.values()}
    missing = required - set(data.columns)
    if missing:
        raise ValueError(f"ranked distributions are missing columns: {sorted(missing)}")

    distributions: dict[str, pd.DataFrame] = {}
    for name, metric in metrics.items():
        ranked = data.copy()
        ranked["rank_position"] = weighted_rank_positions(
            ranked[metric],
            ranked["household_weight"],
            tie_breaker=ranked["household_id"],
        )
        ranked["rank_group"] = weighted_rank_groups(
            ranked[metric],
            ranked["household_weight"],
            WEALTH_QUANTILE_GROUPS,
            tie_breaker=ranked["household_id"],
        )
        ranked["rank_basis"] = metric
        distributions[name] = ranked
    return distributions


def aggregate_ranked_resource_distributions(data: pd.DataFrame) -> pd.DataFrame:
    """Return comparable shares after independently ranking each measure."""
    ranked = build_ranked_distributions(data)
    rows: list[dict[str, object]] = []
    for measure, frame in ranked.items():
        metric = DEFAULT_RESOURCE_METRICS[measure]
        weighted_values = frame[metric] * frame["household_weight"]
        grand_total = weighted_values.sum()
        for group_name, _, _ in WEALTH_QUANTILE_GROUPS:
            selected = frame["rank_group"] == group_name
            group_total = weighted_values[selected].sum()
            rows.append(
                {
                    "measure": measure,
                    "rank_basis": metric,
                    "rank_group": group_name,
                    "household_share": frame.loc[selected, "household_weight"].sum()
                    / frame["household_weight"].sum(),
                    "weighted_total": group_total,
                    "wealth_share": group_total / grand_total if grand_total else 0.0,
                }
            )
    return pd.DataFrame(rows)
