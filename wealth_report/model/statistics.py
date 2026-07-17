from __future__ import annotations

from collections.abc import Sequence

import numpy as np


def _validated_arrays(values, weights) -> tuple[np.ndarray, np.ndarray]:
    value_array = np.asarray(values, dtype=float)
    weight_array = np.asarray(weights, dtype=float)

    if value_array.ndim != 1 or weight_array.ndim != 1:
        raise ValueError("values and weights must be one-dimensional")
    if len(value_array) != len(weight_array):
        raise ValueError("values and weights must have the same length")
    if len(value_array) == 0:
        raise ValueError("values and weights must not be empty")
    if np.any(~np.isfinite(value_array)) or np.any(~np.isfinite(weight_array)):
        raise ValueError("values and weights must be finite")
    if np.any(weight_array < 0):
        raise ValueError("weights must be non-negative")
    if weight_array.sum() <= 0:
        raise ValueError("at least one weight must be positive")

    return value_array, weight_array


def weighted_quantile(values, weights, quantiles):
    value_array, weight_array = _validated_arrays(values, weights)
    quantile_array = np.asarray(quantiles, dtype=float)
    if quantile_array.ndim != 1:
        raise ValueError("quantiles must be one-dimensional")
    if np.any((quantile_array < 0) | (quantile_array > 1)):
        raise ValueError("quantiles must be between 0 and 1")

    order = np.argsort(value_array)
    sorted_values = value_array[order]
    sorted_weights = weight_array[order]
    cumulative = np.cumsum(sorted_weights)
    thresholds = quantile_array * sorted_weights.sum()

    indexes = np.searchsorted(cumulative, thresholds, side="left")
    indexes = np.clip(indexes, 0, len(sorted_values) - 1)
    return sorted_values[indexes]


def weighted_median(values, weights):
    return float(weighted_quantile(values, weights, [0.5])[0])


def weighted_rank_positions(values, weights, *, tie_breaker=None) -> np.ndarray:
    """Return cumulative-weight positions with deterministic ascending ties."""
    value_array, weight_array = _validated_arrays(values, weights)
    if tie_breaker is None:
        tie_array = np.arange(len(value_array))
    else:
        tie_array = np.asarray(tie_breaker)
        if tie_array.ndim != 1 or len(tie_array) != len(value_array):
            raise ValueError("tie_breaker must be one-dimensional and match values")
    order = np.lexsort((tie_array, value_array))
    cumulative_before = np.concatenate(([0.0], np.cumsum(weight_array[order])[:-1]))
    sorted_positions = cumulative_before / weight_array.sum()
    positions = np.empty(len(value_array), dtype=float)
    positions[order] = sorted_positions
    return positions


def weighted_rank_groups(values, weights, groups, *, tie_breaker=None):
    if not isinstance(groups, Sequence) or len(groups) == 0:
        raise ValueError("groups must be a non-empty sequence")
    positions = weighted_rank_positions(values, weights, tie_breaker=tie_breaker)
    labels: list[str | None] = []
    for position in positions:
        label = next(
            (
                name
                for name, lower, upper in groups
                if lower <= position < upper or (upper == 1 and lower <= position <= upper)
            ),
            None,
        )
        labels.append(label)
    if any(label is None for label in labels):
        raise ValueError("groups must cover the weighted percentile range from 0 to 1")
    return labels
