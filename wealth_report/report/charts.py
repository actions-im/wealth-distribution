from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from wealth_report.report.formatting import dollars_trillions


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
SHIFT_GROUP_ORDER = list(SHIFT_COLORS)
SHIFT_STATES = ["Conventional net worth", "All modeled future resources"]

# Segments narrower than this cannot hold a full "12.6% [$39.9T]" label.
MIN_INSIDE_LABEL_SHARE = 0.055
# Rightmost (Top 1%) segments below this use an end-cap annotation past the stack.
TOP_ONE_INSIDE_MIN_SHARE = 0.18
OUTSIDE_LABEL_AXIS_PAD = 0.18


def distribution_shift_figure(data: pd.DataFrame) -> go.Figure:
    """Show two independently ranked resource distributions as paired signed bars.

    Labels are layout annotations (not bar ``text``). Plotly often clips or drops
    in-bar text on stacked horizontal segments — especially the rightmost Top 1%
    block in half-width Age slicing panels — even when the trace carries a label.
    """
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
            figure.add_bar(
                x=[float(row["share"])],
                y=[state],
                orientation="h",
                name=group,
                legendgroup=group,
                showlegend=state == SHIFT_STATES[0],
                marker={"color": color, "line": {"color": "#FFFFFF", "width": 1.5}},
                # Labels are annotations; keep bar text empty so Plotly cannot hide them.
                text=None,
                hoverinfo="skip",
            )

    annotations, needs_outside_pad = _segment_annotations(data)
    xaxis_range = _signed_share_axis_range(data, pad_outside_labels=needs_outside_pad)
    figure.update_layout(
        barmode="stack",
        barnorm=None,
        height=370,
        margin={"l": 20, "r": 48, "t": 65, "b": 45},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        hoverlabel={"bgcolor": "#FFFFFF", "font": {"color": "#172121"}},
        hovermode=False,
        annotations=annotations,
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
    )
    return figure


def _segment_annotations(data: pd.DataFrame) -> tuple[list[dict], bool]:
    """Place share+dollar labels by cumulative stack position."""
    annotations: list[dict] = []
    needs_outside_pad = False
    for state in SHIFT_STATES:
        state_rows = data.loc[data["state"] == state].set_index("group")
        positive_cursor = 0.0
        negative_cursor = 0.0
        for group in SHIFT_GROUP_ORDER:
            share = float(state_rows.loc[group, "share"])
            weighted_total = float(state_rows.loc[group, "weighted_total"])
            if share < 0:
                # Plotly stacks negatives leftward from zero.
                start = negative_cursor + share
                end = negative_cursor
                mid = (start + end) / 2
                negative_cursor = start
                label = _share_label(share, weighted_total)
                annotations.append(
                    _annotation(
                        x=start,
                        y=state,
                        text=label,
                        color="#172121",
                        xanchor="right",
                        xshift=-4,
                    )
                )
                needs_outside_pad = True
                continue

            start = positive_cursor
            end = positive_cursor + share
            mid = (start + end) / 2
            positive_cursor = end

            if group == "Top 1%" and share > 0:
                label = _share_label(share, weighted_total)
                if share < TOP_ONE_INSIDE_MIN_SHARE:
                    # Past the right edge of the stack — never clipped by bar width.
                    annotations.append(
                        _annotation(
                            x=end,
                            y=state,
                            text=label,
                            color="#172121",
                            xanchor="left",
                            xshift=6,
                        )
                    )
                    needs_outside_pad = True
                else:
                    annotations.append(
                        _annotation(
                            x=mid,
                            y=state,
                            text=label,
                            color=SHIFT_TEXT_COLORS[group],
                            xanchor="center",
                        )
                    )
                continue

            if share >= MIN_INSIDE_LABEL_SHARE:
                annotations.append(
                    _annotation(
                        x=mid,
                        y=state,
                        text=_share_label(share, weighted_total),
                        color=SHIFT_TEXT_COLORS[group],
                        xanchor="center",
                    )
                )
    return annotations, needs_outside_pad


def _annotation(
    *,
    x: float,
    y: str,
    text: str,
    color: str,
    xanchor: str,
    xshift: int = 0,
) -> dict:
    return {
        "x": x,
        "y": y,
        "text": text,
        "showarrow": False,
        "xref": "x",
        "yref": "y",
        "xanchor": xanchor,
        "yanchor": "middle",
        "xshift": xshift,
        "font": {"color": color, "size": 11},
        # Keep labels above bar strokes / white separators.
        "bgcolor": "rgba(255,255,255,0)",
    }


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


def _signed_share_axis_range(
    data: pd.DataFrame, *, pad_outside_labels: bool = False
) -> list[float]:
    totals = data.groupby("state", observed=True)["share"].agg(
        negative=lambda values: values[values < 0].sum(),
        positive=lambda values: values[values > 0].sum(),
    )
    lower = float(min(0.0, totals["negative"].min()))
    upper = float(max(1.0, totals["positive"].max()))
    right_pad = OUTSIDE_LABEL_AXIS_PAD if pad_outside_labels else 0.0
    if lower == 0:
        return [0.0, upper + right_pad]
    padding = max(0.02, abs(lower) * 0.15)
    return [lower - padding, upper + max(padding, right_pad)]
