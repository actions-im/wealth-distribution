from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Literal, Sequence

from src.actuarial import present_value_stream

PensionMode = Literal["accrued", "continuation"]


@dataclass(frozen=True)
class DefinedBenefitPlan:
    annual_benefit: float
    current_age: int
    claiming_age: int
    accrued_fraction: float = 1.0
    real_cola: float = 0.0
    survivor_fraction: float = 0.0
    account_type: bool = False
    account_balance: float = 0.0


@dataclass(frozen=True)
class DefinedBenefitValue:
    present_value: float
    annual_benefit: float
    excluded_account_balance: float
    exclusions: tuple[str, ...]


@dataclass(frozen=True)
class PensionComponents:
    incremental_pension_wealth: float
    excluded_account_balance: float
    networth_includes_dc: bool


def defined_benefit_wealth(
    *,
    annual_benefit: float,
    current_age: int,
    claiming_age: int,
    survival: Sequence[float],
    discount_rate: float = 0.035,
    real_cola: float = 0.0,
) -> float:
    if not math.isfinite(annual_benefit) or annual_benefit < 0:
        raise ValueError("annual_benefit must be finite and nonnegative")
    if not math.isfinite(real_cola) or real_cola <= -1:
        raise ValueError("real_cola must be finite and greater than -1")
    if not survival or annual_benefit == 0:
        return 0.0

    benefit_offset = max(int(claiming_age) - int(current_age), 0)
    if benefit_offset >= len(survival):
        return 0.0
    benefit_survival = list(survival)[benefit_offset:]
    payments = [
        annual_benefit * (1 + real_cola) ** period
        for period in range(len(benefit_survival))
    ]
    return present_value_stream(
        payments,
        discount_rate,
        survival=benefit_survival,
        start_period=max(benefit_offset, 1),
    )


def value_defined_benefit_plan(
    plan: DefinedBenefitPlan,
    *,
    mode: PensionMode,
    survival: Sequence[float],
    discount_rate: float = 0.035,
) -> DefinedBenefitValue:
    if mode not in {"accrued", "continuation"}:
        raise ValueError("mode must be 'accrued' or 'continuation'")
    if not 0 <= plan.accrued_fraction <= 1:
        raise ValueError("accrued_fraction must be between zero and one")
    if not 0 <= plan.survivor_fraction <= 1:
        raise ValueError("survivor_fraction must be between zero and one")
    if plan.account_balance < 0:
        raise ValueError("account_balance cannot be negative")

    exclusions: list[str] = []
    if plan.account_type:
        exclusions.append("account_balance_already_in_net_worth")
        return DefinedBenefitValue(
            present_value=0.0,
            annual_benefit=0.0,
            excluded_account_balance=plan.account_balance,
            exclusions=tuple(exclusions),
        )
    if plan.survivor_fraction > 0:
        exclusions.append("survivor_annuity_without_joint_survival_curve")

    benefit = plan.annual_benefit * (plan.accrued_fraction if mode == "accrued" else 1)
    value = defined_benefit_wealth(
        annual_benefit=benefit,
        current_age=plan.current_age,
        claiming_age=plan.claiming_age,
        survival=survival,
        discount_rate=discount_rate,
        real_cola=plan.real_cola,
    )
    return DefinedBenefitValue(
        present_value=value,
        annual_benefit=benefit,
        excluded_account_balance=0.0,
        exclusions=tuple(exclusions),
    )


def pension_components(
    *, networth_includes_dc: bool, dc_balance: float, db_wealth: float
) -> PensionComponents:
    """Return only pension wealth incremental to the supplied net-worth measure."""
    if dc_balance < 0 or db_wealth < 0:
        raise ValueError("pension component values cannot be negative")
    incremental = db_wealth if networth_includes_dc else db_wealth + dc_balance
    excluded = dc_balance if networth_includes_dc else 0.0
    return PensionComponents(
        incremental_pension_wealth=incremental,
        excluded_account_balance=excluded,
        networth_includes_dc=networth_includes_dc,
    )
