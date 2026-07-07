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


def weighted_mean(values, weights):
    value_array, weight_array = _validated_arrays(values, weights)
    return float(np.average(value_array, weights=weight_array))


def assign_weighted_quantile_group(values, weights, groups):
    value_array, weight_array = _validated_arrays(values, weights)
    if not isinstance(groups, Sequence) or len(groups) == 0:
        raise ValueError("groups must be a non-empty sequence")

    order = np.argsort(value_array)
    sorted_weights = weight_array[order]
    cumulative_before = np.concatenate(([0.0], np.cumsum(sorted_weights)[:-1]))
    percentile_positions = cumulative_before / sorted_weights.sum()

    labels_sorted: list[str | None] = [None] * len(value_array)
    for row_index, position in enumerate(percentile_positions):
        for label, lower, upper in groups:
            if lower <= position < upper or (upper == 1.0 and position <= 1.0 and lower <= position):
                labels_sorted[row_index] = label
                break

    if any(label is None for label in labels_sorted):
        raise ValueError("groups must cover the weighted percentile range from 0 to 1")

    labels = [None] * len(value_array)
    for sorted_index, original_index in enumerate(order):
        labels[original_index] = labels_sorted[sorted_index]

    return labels
