from __future__ import annotations

from dataclasses import dataclass
import math
from collections.abc import Sequence

import numpy as np


@dataclass(frozen=True)
class ImplicateEstimate:
    estimate: float
    between_implicate_variance: float
    implicate_count: int


@dataclass(frozen=True)
class SCFUncertainty:
    estimate: float
    within_implicate_variance: float
    between_implicate_variance: float
    total_variance: float
    standard_error: float
    confidence_low: float
    confidence_high: float
    implicate_count: int
    effective_unweighted_count: int | None = None


def _finite(values: Sequence[float], name: str) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    if array.ndim != 1 or len(array) == 0:
        raise ValueError(f"{name} must be a nonempty one-dimensional sequence")
    if np.any(~np.isfinite(array)):
        raise ValueError(f"{name} must contain only finite values")
    return array


def combine_implicates(estimates: Sequence[float]) -> ImplicateEstimate:
    values = _finite(estimates, "estimates")
    between = float(np.var(values, ddof=1)) if len(values) > 1 else 0.0
    return ImplicateEstimate(
        estimate=float(np.mean(values)),
        between_implicate_variance=between,
        implicate_count=len(values),
    )


def replicate_variance(
    full_sample_estimate: float,
    replicate_estimates: Sequence[float],
    *,
    scale: float,
) -> float:
    replicates = _finite(replicate_estimates, "replicate_estimates")
    if not math.isfinite(full_sample_estimate):
        raise ValueError("full_sample_estimate must be finite")
    if not math.isfinite(scale) or scale < 0:
        raise ValueError("scale must be finite and nonnegative")
    return float(scale * np.sum((replicates - full_sample_estimate) ** 2))


def combine_scf_variance(
    *,
    estimates: Sequence[float],
    sampling_variances: Sequence[float],
    confidence_level: float = 0.95,
    effective_unweighted_count: int | None = None,
) -> SCFUncertainty:
    """Combine within- and between-implicate variance using Rubin's rule.

    Callers must first calculate each statistic and its replicate-weight sampling
    variance separately within every implicate.
    """
    point_values = _finite(estimates, "estimates")
    sampling = _finite(sampling_variances, "sampling_variances")
    if len(point_values) != len(sampling):
        raise ValueError("estimates and sampling_variances must have the same length")
    if np.any(sampling < 0):
        raise ValueError("sampling_variances cannot be negative")
    if confidence_level != 0.95:
        raise ValueError("only a 0.95 normal-approximation interval is currently supported")
    if effective_unweighted_count is not None and effective_unweighted_count <= 0:
        raise ValueError("effective_unweighted_count must be positive")

    combined = combine_implicates(point_values)
    within = float(np.mean(sampling))
    total = within + (1 + 1 / len(point_values)) * combined.between_implicate_variance
    standard_error = math.sqrt(total)
    critical_value = 1.959963984540054
    return SCFUncertainty(
        estimate=combined.estimate,
        within_implicate_variance=within,
        between_implicate_variance=combined.between_implicate_variance,
        total_variance=total,
        standard_error=standard_error,
        confidence_low=combined.estimate - critical_value * standard_error,
        confidence_high=combined.estimate + critical_value * standard_error,
        implicate_count=len(point_values),
        effective_unweighted_count=effective_unweighted_count,
    )
