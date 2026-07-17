import numpy as np
import pytest

from wealth_report.model.statistics import (
    assign_weighted_quantile_group,
    weighted_mean,
    weighted_median,
    weighted_quantile,
    weighted_rank_groups,
)


def test_weighted_mean_uses_weights():
    assert weighted_mean([10, 20, 100], [1, 1, 8]) == pytest.approx(83.0)


def test_weighted_median_respects_large_weight():
    assert weighted_median([10, 20, 100], [1, 1, 8]) == 100


def test_weighted_quantile_matches_unweighted_for_equal_weights():
    result = weighted_quantile([0, 10, 20, 30], [1, 1, 1, 1], [0.25, 0.5, 0.75])

    assert np.allclose(result, [0, 10, 20])


def test_weighted_quantile_sorts_values_before_computing():
    result = weighted_quantile([30, 0, 20, 10], [1, 1, 1, 1], [0.5])

    assert result[0] == 10


def test_weighted_quantile_rejects_invalid_inputs():
    with pytest.raises(ValueError):
        weighted_quantile([1, 2], [1], [0.5])

    with pytest.raises(ValueError):
        weighted_quantile([1, 2], [0, 0], [0.5])

    with pytest.raises(ValueError):
        weighted_quantile([1, 2], [1, 1], [-0.1])


def test_assign_weighted_quantile_group_labels_observations():
    labels = assign_weighted_quantile_group(
        values=[10, 20, 30, 40],
        weights=[1, 1, 1, 1],
        groups=[("Bottom half", 0.0, 0.5), ("Top half", 0.5, 1.0)],
    )

    assert labels == ["Bottom half", "Bottom half", "Top half", "Top half"]


def test_weighted_rank_groups_uses_explicit_tie_breaker():
    labels = weighted_rank_groups(
        values=[10, 10, 20],
        weights=[1, 1, 1],
        groups=[("Bottom", 0, 0.5), ("Top", 0.5, 1)],
        tie_breaker=[2, 1, 3],
    )

    assert labels == ["Bottom", "Bottom", "Top"]
