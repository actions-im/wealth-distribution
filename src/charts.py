from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


MONEY_TICK = "$,.0f"


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


def current_vs_adjusted_share_bar(data: pd.DataFrame, title: str):
    melted = data.melt(
        id_vars=["wealth_quantile"],
        value_vars=["traditional_net_worth_share", "combined_real_wealth_share"],
        var_name="measure",
        value_name="share",
    )
    labels = {
        "traditional_net_worth_share": "Current ledger",
        "combined_real_wealth_share": "Adjusted ledger",
    }
    colors = {
        "Current ledger": "#8f1d14",
        "Adjusted ledger": "#0f766e",
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
