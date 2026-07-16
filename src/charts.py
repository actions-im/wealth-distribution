from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from src.formatting import dollars_trillions


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
    """Show two independently ranked resource distributions as paired 100% bars."""
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
            figure.add_bar(
                x=[share],
                y=[state],
                orientation="h",
                name=group,
                legendgroup=group,
                showlegend=state == SHIFT_STATES[0],
                marker={"color": color, "line": {"color": "#FFFFFF", "width": 1.5}},
                text=[
                    f"{share:.1%} [{dollars_trillions(float(row['weighted_total']))}]"
                    if share >= 0.055
                    else ""
                ],
                textposition="inside",
                insidetextanchor="middle",
                textfont={"color": SHIFT_TEXT_COLORS[group], "size": 12},
                hoverinfo="skip",
            )

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
            "range": [0, 1],
            "tickformat": ".0%",
            "dtick": 0.25,
            "showgrid": False,
            "zeroline": False,
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
        uniformtext={"minsize": 12, "mode": "hide"},
    )
    return figure


def color_for_change(change_pp: float) -> str:
    return "#0F766E" if change_pp >= 0 else "#9F3A2B"


def money_bar(data: pd.DataFrame, x: str, y: str, title: str, color: str | None = None):
    fig = px.bar(data, x=x, y=y, color=color, title=title)
    fig.update_layout(yaxis_tickformat=MONEY_TICK, hovermode="x unified")
    fig.update_traces(hovertemplate="%{x}<br>$%{y:,.0f}<extra></extra>")
    return fig


def wealth_definition_line(data: pd.DataFrame, x: str, title: str):
    melted = data.melt(
        id_vars=[x],
        value_vars=["traditional_net_worth", "human_capital", "combined_real_wealth"],
        var_name="wealth_definition",
        value_name="value",
    )
    fig = px.line(
        melted,
        x=x,
        y="value",
        color="wealth_definition",
        markers=True,
        title=title,
    )
    fig.update_layout(yaxis_tickformat=MONEY_TICK, hovermode="x unified")
    return fig


def wealth_share_bar(data: pd.DataFrame, title: str):
    melted = data.melt(
        id_vars=["wealth_quantile"],
        value_vars=[
            "population_share",
            "traditional_net_worth_share",
            "human_capital_share",
            "combined_real_wealth_share",
        ],
        var_name="measure",
        value_name="share",
    )
    labels = {
        "population_share": "Population",
        "traditional_net_worth_share": "Marketable net worth",
        "human_capital_share": "Human capital",
        "combined_real_wealth_share": "Marketable + human capital",
    }
    melted["measure"] = melted["measure"].map(labels)
    fig = px.bar(
        melted,
        x="wealth_quantile",
        y="share",
        color="measure",
        barmode="group",
        title=title,
    )
    fig.update_layout(yaxis_tickformat=".0%", hovermode="x unified")
    fig.update_traces(hovertemplate="%{x}<br>%{y:.1%}<extra></extra>")
    return fig


def priced_vs_full_share_bar(data: pd.DataFrame, title: str):
    melted = data.melt(
        id_vars=["wealth_quantile"],
        value_vars=["traditional_net_worth_share", "combined_real_wealth_share"],
        var_name="measure",
        value_name="share",
    )
    labels = {
        "traditional_net_worth_share": "Conventional net worth",
        "combined_real_wealth_share": "Net worth plus modeled labor",
    }
    colors = {
        "Conventional net worth": "#8f1d14",
        "Net worth plus modeled labor": "#0f766e",
    }
    melted["measure"] = melted["measure"].map(labels)
    fig = px.bar(
        melted,
        x="wealth_quantile",
        y="share",
        color="measure",
        barmode="group",
        text=melted["share"].map(lambda value: f"{value:.1%}"),
        color_discrete_map=colors,
        title=title,
    )
    fig.update_traces(textposition="outside", hovertemplate="%{x}<br>%{y:.1%}<extra></extra>")
    fig.update_layout(
        yaxis_tickformat=".0%",
        yaxis_title="Share",
        xaxis_title="Wealth quantile",
        legend_title_text="",
        hovermode="x unified",
        uniformtext_minsize=10,
        uniformtext_mode="hide",
    )
    return fig


def single_distribution_share_bar(
    data: pd.DataFrame,
    share_column: str,
    title: str,
    color: str,
):
    fig = px.bar(
        data,
        x="wealth_quantile",
        y=share_column,
        text=data[share_column].map(lambda value: f"{value:.1%}"),
        title=title,
    )
    fig.update_traces(
        marker_color=color,
        textposition="outside",
        hovertemplate="%{x}<br>%{y:.1%}<extra></extra>",
    )
    fig.update_layout(
        yaxis_tickformat=".0%",
        yaxis_title="Share",
        xaxis_title="Wealth quantile",
        title=dict(font=dict(size=16)),
        hovermode="x unified",
        uniformtext_minsize=10,
        uniformtext_mode="hide",
    )
    return fig


def stacked_marketable_vs_human(data: pd.DataFrame, x: str, title: str):
    fig = go.Figure()
    fig.add_bar(
        x=data[x],
        y=data["traditional_net_worth"],
        name="Marketable net worth",
        hovertemplate="%{x}<br>$%{y:,.0f}<extra></extra>",
    )
    fig.add_bar(
        x=data[x],
        y=data["human_capital"],
        name="Human capital",
        hovertemplate="%{x}<br>$%{y:,.0f}<extra></extra>",
    )
    fig.update_layout(barmode="stack", title=title, yaxis_tickformat=MONEY_TICK)
    return fig


def matrix_heatmap(data: pd.DataFrame, metric: str):
    pivot = data.pivot(index="age_group", columns="wealth_quantile", values=metric)
    fig = px.imshow(
        pivot,
        aspect="auto",
        text_auto="$.2s",
        title=f"{metric.replace('_', ' ').title()} by age and wealth quantile",
    )
    fig.update_layout(coloraxis_colorbar_tickformat=MONEY_TICK)
    return fig
