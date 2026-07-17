"""Shared finite-number and weighted-total helpers.

Boolean scalars are never treated as numeric. Callers that need SCF-style
coercion (invalid → 0) use ``as_number``; callers that need validation use
``finite_float`` / ``is_finite_numeric``.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Sequence

import numpy as np


def is_boolean_scalar(value: object) -> bool:
    return isinstance(value, (bool, np.bool_))


def finite_float(value: object) -> float | None:
    """Return a finite float, or None if value is non-numeric or non-finite.

    Booleans are rejected. Strings that parse as floats are accepted (legacy
    validation behavior for inheritance inputs).
    """
    if is_boolean_scalar(value):
        return None
    try:
        numeric = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return numeric if math.isfinite(numeric) else None


def is_finite_numeric(value: object) -> bool:
    """Strict finite check: rejects bools, strings, and bytes."""
    if is_boolean_scalar(value) or isinstance(value, (str, bytes)):
        return False
    return finite_float(value) is not None


def as_number(value: object, *, default: float = 0.0) -> float:
    """Coerce survey-like inputs to float; invalid or non-finite values → default."""
    if is_boolean_scalar(value):
        return default
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def finite_nonnegative_or_zero(value: object) -> float:
    numeric = finite_float(value)
    return numeric if numeric is not None and numeric > 0 else 0.0


def require_finite_series(values: Iterable[float], *, name: str) -> None:
    if any(not math.isfinite(value) for value in values):
        raise ValueError(f"{name} must be finite")


def finite_weighted_total(
    weights: Sequence[float],
    values: Sequence[float],
    *,
    name: str,
    use_fsum: bool = False,
) -> float:
    """Return Σ weight×value, rejecting non-finite partial products."""
    contributions: list[float] = []
    total = 0.0
    for weight, value in zip(weights, values, strict=True):
        contribution = weight * value
        if not math.isfinite(contribution):
            raise ValueError(f"{name} must be finite")
        if use_fsum:
            contributions.append(contribution)
        else:
            total += contribution
            if not math.isfinite(total):
                raise ValueError(f"{name} must be finite")
    if use_fsum:
        total = math.fsum(contributions)
        if not math.isfinite(total):
            raise ValueError(f"{name} must be finite")
    return total
