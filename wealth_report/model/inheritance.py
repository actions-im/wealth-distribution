from __future__ import annotations

from dataclasses import dataclass
import math

import pandas as pd

from wealth_report.model.actuarial import conditional_survival
from wealth_report.model.numeric import (
    finite_float,
    finite_nonnegative_or_zero,
    finite_weighted_total,
    require_finite_series,
)


_REQUIRED_COLUMNS = {
    "household_weight",
    "net_worth",
    "age",
    "sex",
    "expected_inheritance_amount",
    "expects_sizable_estate",
}


@dataclass(frozen=True)
class InheritanceDiagnostics:
    """Weighted accounting totals for the constrained reallocation."""

    reported_claim_total: float
    discounted_claim_total: float
    donor_capacity_total: float
    reallocated_total: float
    unallocated_claim_total: float
    funding_ratio: float


def discounted_inheritance_claim(amount: float, years: int, discount_rate: float) -> float:
    """Discount a positive SCF expectation field value to the scenario horizon.

    Invalid, missing, or nonpositive SCF field values are treated as no claim.
    """
    rate = _validate_horizon_and_discount(horizon_years=years, discount_rate=discount_rate)
    numeric_amount = finite_nonnegative_or_zero(amount)
    if numeric_amount == 0:
        return 0.0
    try:
        discount_factor = (1 + rate) ** years
        claim = numeric_amount / discount_factor
    except (OverflowError, ZeroDivisionError) as error:
        raise ValueError("inheritance_claim must be finite") from error
    if not math.isfinite(discount_factor) or not math.isfinite(claim):
        raise ValueError("inheritance_claim must be finite")
    return claim


def allocate_inheritance_reallocation(
    households: pd.DataFrame,
    *,
    life_table: dict[str, dict[int, float]],
    horizon_years: int,
    discount_rate: float,
) -> tuple[pd.DataFrame, InheritanceDiagnostics]:
    """Allocate expected inheritances without increasing weighted national wealth.

    Recipient credits are funded only by a proportional reserve against the
    mortality-weighted capacity of households reporting sizable-estate intent.
    The SCF does not link recipients to donors, so this is an aggregate
    reallocation rather than a household-to-household transfer prediction.
    """
    rate = _validate_horizon_and_discount(
        horizon_years=horizon_years, discount_rate=discount_rate
    )
    missing = _REQUIRED_COLUMNS.difference(households.columns)
    if missing:
        raise ValueError(f"inheritance allocation is missing columns: {sorted(missing)}")

    result = households.copy()
    weights = _validated_weights(result["household_weight"])
    reported_amounts = result["expected_inheritance_amount"].map(finite_nonnegative_or_zero)
    claims = reported_amounts.map(
        lambda amount: discounted_inheritance_claim(
            amount, years=horizon_years, discount_rate=rate
        )
    )
    capacities = pd.Series(
        [
            _estate_donor_capacity(
                net_worth=net_worth,
                age=age,
                sex=sex,
                expects_sizable_estate=expects_sizable_estate,
                life_table=life_table,
                horizon_years=horizon_years,
            )
            for net_worth, age, sex, expects_sizable_estate in zip(
                result["net_worth"],
                result["age"],
                result["sex"],
                result["expects_sizable_estate"],
                strict=True,
            )
        ],
        index=result.index,
        dtype=float,
    )

    reported_claim_total = finite_weighted_total(
        weights.tolist(), reported_amounts.tolist(), name="reported_claim_total"
    )
    discounted_claim_total = finite_weighted_total(
        weights.tolist(), claims.tolist(), name="discounted_claim_total"
    )
    donor_capacity_total = finite_weighted_total(
        weights.tolist(), capacities.tolist(), name="donor_capacity_total"
    )
    reallocated_total = min(discounted_claim_total, donor_capacity_total)
    recipient_scale = reallocated_total / discounted_claim_total if discounted_claim_total else 0.0
    donor_scale = reallocated_total / donor_capacity_total if donor_capacity_total else 0.0

    credits = claims * recipient_scale
    reserves = capacities * donor_scale
    require_finite_series(credits, name="inheritance_credit")
    require_finite_series(reserves, name="estate_donor_reserve")
    result["inheritance_claim"] = claims
    result["inheritance_credit"] = credits
    result["estate_donor_capacity"] = capacities
    result["estate_donor_reserve"] = reserves
    result["inheritance_reallocation"] = credits - reserves

    diagnostics = InheritanceDiagnostics(
        reported_claim_total=reported_claim_total,
        discounted_claim_total=discounted_claim_total,
        donor_capacity_total=donor_capacity_total,
        reallocated_total=reallocated_total,
        unallocated_claim_total=discounted_claim_total - reallocated_total,
        funding_ratio=reallocated_total / discounted_claim_total if discounted_claim_total else 0.0,
    )
    return result, diagnostics


def _validate_horizon_and_discount(*, horizon_years: int, discount_rate: float) -> float:
    if (
        isinstance(horizon_years, bool)
        or not isinstance(horizon_years, int)
        or horizon_years <= 0
    ):
        raise ValueError("horizon_years must be a positive integer")
    numeric_rate = finite_float(discount_rate)
    if numeric_rate is None or numeric_rate <= -1:
        raise ValueError("discount_rate must be finite and greater than -1")
    return numeric_rate


def _validated_weights(values: pd.Series) -> pd.Series:
    weights = values.map(finite_float)
    if weights.isna().any() or (weights < 0).any():
        raise ValueError("household_weight must be finite and nonnegative")
    return weights.astype(float)


def _estate_donor_capacity(
    *,
    net_worth: object,
    age: object,
    sex: object,
    expects_sizable_estate: object,
    life_table: dict[str, dict[int, float]],
    horizon_years: int,
) -> float:
    wealth = finite_float(net_worth)
    current_age = _valid_age(age)
    if (
        not isinstance(expects_sizable_estate, bool)
        or not expects_sizable_estate
        or wealth is None
        or wealth <= 0
        or current_age is None
        or not isinstance(sex, str)
    ):
        return 0.0

    lives_by_age = life_table.get(sex.strip().lower())
    if lives_by_age is None:
        return 0.0
    try:
        survival_curve = conditional_survival(
            lives_by_age,
            current_age,
            max_age=current_age + horizon_years,
        )
    except (TypeError, ValueError):
        return 0.0
    if horizon_years >= len(survival_curve):
        return 0.0
    survival_at_horizon = survival_curve[horizon_years]
    mortality = 1 - survival_at_horizon
    return wealth * mortality if math.isfinite(mortality) and mortality > 0 else 0.0


def _valid_age(value: object) -> int | None:
    numeric = finite_float(value)
    if numeric is None or numeric < 0 or not numeric.is_integer():
        return None
    return int(numeric)
