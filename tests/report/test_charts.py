import pandas as pd

from wealth_report.report.charts import (
    SHIFT_COLORS,
    distribution_shift_accessible_table,
    distribution_shift_figure,
)


def test_distribution_shift_figure_has_two_states_and_four_groups():
    figure = distribution_shift_figure(_shift_data())

    assert len(figure.data) == 8
    assert {trace.name for trace in figure.data} == set(SHIFT_COLORS)
    assert {trace.y[0] for trace in figure.data} == {
        "Conventional net worth",
        "All modeled future resources",
    }


def test_accessible_table_contains_every_segment_value():
    table = distribution_shift_accessible_table(_shift_data())

    assert table["Rank group"].tolist() == list(SHIFT_COLORS)
    bottom = table.loc[table["Rank group"] == "Bottom 50%"].iloc[0]
    assert bottom["Conventional share"] == 0.02
    assert bottom["All modeled resources share"] == 0.10
    assert bottom["Conventional weighted resources"] == 0.02e12


def test_distribution_shift_figure_formats_static_labels_and_accessible_hover():
    figure = distribution_shift_figure(_shift_data())
    labels = {annotation["text"] for annotation in figure.layout.annotations}

    assert figure.layout.barmode == "stack"
    assert figure.layout.xaxis.tickformat == ".0%"
    assert figure.layout.xaxis.range == (0.0, 1.0)
    assert "10.0% [$0.1T]" in labels
    # Conventional Bottom 50% is only 2% — too narrow for an in-segment label.
    assert "2.0% [$0.0T]" not in labels
    assert figure.layout.hovermode == "closest"
    assert all(trace.hovertemplate for trace in figure.data)
    assert all("Resource share" in trace.hovertemplate for trace in figure.data)
    # Labels must not rely on bar text (Plotly drops it on stacked segments).
    assert all(not trace.text for trace in figure.data)


def test_distribution_shift_figure_keeps_negative_shares_visible():
    data = _shift_data()
    negative = data.index[
        (data["state"] == "Conventional net worth")
        & (data["group"] == "Bottom 50%")
    ][0]
    data.loc[negative, "share"] = -0.034
    data.loc[negative, "weighted_total"] = -22_600_000_000
    next_40 = data.index[
        (data["state"] == "Conventional net worth")
        & (data["group"] == "Next 40%")
    ][0]
    data.loc[next_40, "share"] = 0.294

    figure = distribution_shift_figure(data)
    labels = [annotation["text"] for annotation in figure.layout.annotations]

    assert figure.layout.xaxis.range[0] < 0
    assert figure.layout.xaxis.range[1] > 1
    assert "−3.4% [−$22.6B]" in labels


def test_distribution_shift_figure_labels_eligible_top_one_segment():
    figure = distribution_shift_figure(_shift_data())
    labels = [annotation["text"] for annotation in figure.layout.annotations]

    assert "19.0% [$0.2T]" in labels
    assert any(label.startswith("35.0%") for label in labels)


def test_narrow_top_one_segment_is_labeled_past_the_stack_edge():
    """Age-panel Top 1% shares are often ~10–14%; in-bar text does not fit."""
    data = _shift_data()
    narrow = data.index[
        (data["state"] == "All modeled future resources") & (data["group"] == "Top 1%")
    ][0]
    data.loc[narrow, "share"] = 0.107
    data.loc[narrow, "weighted_total"] = 5.9e12
    next_nine = data.index[
        (data["state"] == "All modeled future resources") & (data["group"] == "Next 9%")
    ][0]
    data.loc[next_nine, "share"] = float(data.loc[next_nine, "share"]) + (0.19 - 0.107)

    figure = distribution_shift_figure(data)
    top_labels = [
        annotation
        for annotation in figure.layout.annotations
        if annotation["text"] == "10.7% [$5.9T]"
    ]

    assert len(top_labels) == 1
    # Cumulative stack ends at 1.0; outside label sits at the stack edge.
    assert top_labels[0]["x"] == 1.0
    assert top_labels[0]["xanchor"] == "left"
    assert figure.layout.xaxis.range[1] > 1.0


def _shift_data():
    shares = {
        "Conventional net worth": [0.02, 0.24, 0.39, 0.35],
        "All modeled future resources": [0.10, 0.40, 0.31, 0.19],
    }
    rows = []
    for state, values in shares.items():
        for group, value in zip(SHIFT_COLORS, values, strict=True):
            rows.append(
                {
                    "group": group,
                    "state": state,
                    "share": value,
                    "weighted_total": value * 1e12,
                    "household_share": {
                        "Bottom 50%": 0.50,
                        "Next 40%": 0.40,
                        "Next 9%": 0.09,
                        "Top 1%": 0.01,
                    }[group],
                    "rank_basis": (
                        "net_worth"
                        if state == "Conventional net worth"
                        else "continuation_resources"
                    ),
                    "conventional_share": shares["Conventional net worth"][
                        list(SHIFT_COLORS).index(group)
                    ],
                    "future_resources_share": shares["All modeled future resources"][
                        list(SHIFT_COLORS).index(group)
                    ],
                    "change_pp": 100
                    * (
                        shares["All modeled future resources"][list(SHIFT_COLORS).index(group)]
                        - shares["Conventional net worth"][list(SHIFT_COLORS).index(group)]
                    ),
                }
            )
    return pd.DataFrame(rows)
