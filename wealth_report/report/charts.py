from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from wealth_report.report.formatting import dollars_trillions


MONEY_TICK = "$,.0f"

SHIFT_COLORS = {
    "Bottom 50%": "#0F766E",
    "Next 40%": "#5FB3A9",
    "Next 9%": "#D6B56C",
    "Top 1%": "#B4533C",
}
SHIFT_TEXT_COLORS = {
    "Bottom 50%": "#FFFFFF",
    "Next 40%": "#102A2A",
    "Next 9%": "#352A12",
    "Top 1%": "#FFFFFF",
}
SHIFT_STATES = ["Conventional net worth", "All modeled future resources"]


def distribution_shift_figure(data: pd.DataFrame) -> go.Figure:
    """Show two independently ranked resource distributions as paired signed bars."""
    required = {
        "group",
        "state",
        "share",
        "weighted_total",
        "household_share",
        "rank_basis",
        "conventional_share",
        "future_resources_share",
        "change_pp",
    }
    missing = required - set(data.columns)
    if missing:
        raise ValueError(f"distribution shift figure is missing columns: {sorted(missing)}")

    figure = go.Figure()
    for state in SHIFT_STATES:
        for group, color in SHIFT_COLORS.items():
            selected = data.loc[(data["state"] == state) & (data["group"] == group)]
            if len(selected) != 1:
                raise ValueError(f"expected one row for {state} / {group}, found {len(selected)}")
            row = selected.iloc[0]
            share = float(row["share"])
            is_negative = share < 0
            figure.add_bar(
                x=[share],
                y=[state],
                orientation="h",
                name=group,
                legendgroup=group,
                showlegend=state == SHIFT_STATES[0],
                marker={"color": color, "line": {"color": "#FFFFFF", "width": 1.5}},
                text=[
                    _share_label(share, float(row["weighted_total"]))
                    if share < 0 or share >= 0.055
                    else ""
                ],
                textposition="outside" if is_negative else "inside",
                insidetextanchor="middle",
                textfont={
                    "color": "#172121" if is_negative else SHIFT_TEXT_COLORS[group],
                    "size": 12,
                },
                cliponaxis=False,
                hoverinfo="skip",
            )

    xaxis_range = _signed_share_axis_range(data)
    figure.update_layout(
        barmode="stack",
        barnorm=None,
        height=370,
        margin={"l": 20, "r": 20, "t": 65, "b": 45},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        hoverlabel={"bgcolor": "#FFFFFF", "font": {"color": "#172121"}},
        hovermode=False,
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.12,
            "xanchor": "left",
            "x": 0,
            "title": {"text": ""},
        },
        xaxis={
            "range": xaxis_range,
            "tickformat": ".0%",
            "dtick": 0.25,
            "showgrid": False,
            "zeroline": xaxis_range[0] < 0,
            "zerolinecolor": "#64748B",
            "zerolinewidth": 1,
            "title": None,
            "fixedrange": True,
        },
        yaxis={
            "categoryorder": "array",
            "categoryarray": list(reversed(SHIFT_STATES)),
            "showgrid": False,
            "title": None,
            "tickfont": {"size": 15},
            "fixedrange": True,
        },
        uniformtext={"minsize": 12, "mode": "show"},
    )
    return figure


def _share_label(share: float, weighted_total: float) -> str:
    dollars = (
        _compact_dollars(weighted_total)
        if weighted_total < 0
        else dollars_trillions(weighted_total)
    )
    return f"{_signed_percent(share)} [{dollars}]"


def _signed_percent(value: float) -> str:
    return f"{value:.1%}".replace("-", "−")


def _compact_dollars(value: float) -> str:
    sign = "−" if value < 0 else ""
    absolute_value = abs(value)
    if absolute_value < 1_000_000_000_000:
        return f"{sign}${absolute_value / 1_000_000_000:,.1f}B"
    return f"{sign}{dollars_trillions(absolute_value)}"


def _signed_share_axis_range(data: pd.DataFrame) -> list[float]:
    totals = data.groupby("state", observed=True)["share"].agg(
        negative=lambda values: values[values < 0].sum(),
        positive=lambda values: values[values > 0].sum(),
    )
    lower = float(min(0.0, totals["negative"].min()))
    upper = float(max(1.0, totals["positive"].max()))
    if lower == 0:
        return [0.0, 1.0]
    padding = max(0.02, abs(lower) * 0.15)
    return [lower - padding, upper + padding]
