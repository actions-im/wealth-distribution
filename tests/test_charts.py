import pandas as pd

from src.charts import SHIFT_COLORS, distribution_shift_figure


def test_distribution_shift_figure_has_two_states_and_four_groups():
    figure = distribution_shift_figure(_shift_data())

    assert len(figure.data) == 8
    assert {trace.name for trace in figure.data} == set(SHIFT_COLORS)
    assert {trace.y[0] for trace in figure.data} == {
        "Conventional net worth",
        "All modeled future resources",
    }
    assert not figure.layout.annotations


def test_distribution_shift_figure_formats_static_in_block_labels_without_hover():
    figure = distribution_shift_figure(_shift_data())
    full_resources_bottom_50 = next(
        trace
        for trace in figure.data
        if trace.name == "Bottom 50%"
        and trace.y[0] == "All modeled future resources"
    )
    conventional_bottom_50 = next(
        trace
        for trace in figure.data
        if trace.name == "Bottom 50%"
        and trace.y[0] == "Conventional net worth"
    )

    assert figure.layout.barmode == "stack"
    assert figure.layout.xaxis.tickformat == ".0%"
    assert figure.layout.xaxis.range == (0, 1)
    assert full_resources_bottom_50.text == ("10.0% [$0.1T]",)
    assert conventional_bottom_50.text == ("",)
    assert not figure.layout.annotations
    assert all(trace.hoverinfo == "skip" for trace in figure.data)
    assert all(trace.hovertemplate is None for trace in figure.data)


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
