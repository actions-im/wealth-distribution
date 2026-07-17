from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Literal, Sequence

from wealth_report.model.actuarial import present_value_stream

LaborMode = Literal["defensive", "continuation"]


@dataclass(frozen=True)
class PersonLaborInput:
    age: int
    current_income: float
    sex: str
    reentry_income: float = 0.0
    reentry_probability: float = 0.0


@dataclass(frozen=True)
class HouseholdLaborWealth:
    respondent: float
    spouse: float

    @property
    def total(self) -> float:
        return self.respondent + self.spouse


def _probability(value: float, name: str) -> float:
    if not math.isfinite(value) or not 0 <= value <= 1:
        raise ValueError(f"{name} must be finite and between zero and one")
    return float(value)


def projected_labor_income_stream(
    *,
    current_income: float,
    age: int,
    retirement_age: int = 67,
    reentry_income: float = 0.0,
    reentry_probability: float = 0.0,
    employment_probability: float = 0.95,
    wage_growth: float = 0.015,
    tax_rate: float = 0.0,
    mode: LaborMode = "continuation",
) -> list[float]:
    """Return expected annual after-tax labor income before survival discounting."""
    years = max(int(retirement_age) - int(age), 0)
    if mode not in {"defensive", "continuation"}:
        raise ValueError("mode must be 'defensive' or 'continuation'")
    for value, name in (
        (employment_probability, "employment_probability"),
        (reentry_probability, "reentry_probability"),
        (tax_rate, "tax_rate"),
    ):
        _probability(value, name)
    if not math.isfinite(wage_growth) or wage_growth <= -1:
        raise ValueError("wage_growth must be finite and greater than -1")
    if current_income < 0 or reentry_income < 0:
        raise ValueError("labor incomes cannot be negative")
    if current_income > 0:
        base_income = float(current_income)
        work_probability = float(employment_probability)
    else:
        base_income = float(reentry_income)
        work_probability = float(reentry_probability)
    if years == 0 or base_income == 0 or work_probability == 0:
        return [0.0] * years
    applied_growth = wage_growth if mode == "continuation" else 0.0
    after_tax_base = base_income * (1 - tax_rate) * work_probability
    return [after_tax_base * (1 + applied_growth) ** period for period in range(1, years + 1)]


def estimate_labor_wealth(
    *,
    current_income: float,
    age: int,
    retirement_age: int = 67,
    survival: Sequence[float] | None = None,
    reentry_income: float = 0.0,
    reentry_probability: float = 0.0,
    employment_probability: float = 0.95,
    wage_growth: float = 0.015,
    discount_rate: float = 0.035,
    tax_rate: float = 0.0,
    mode: LaborMode = "continuation",
) -> float:
    """Value expected after-tax labor income, with the first cash flow one year ahead."""
    payments = projected_labor_income_stream(
        current_income=current_income,
        age=age,
        retirement_age=retirement_age,
        reentry_income=reentry_income,
        reentry_probability=reentry_probability,
        employment_probability=employment_probability,
        wage_growth=wage_growth,
        tax_rate=tax_rate,
        mode=mode,
    )
    years = len(payments)
    if not payments or not any(payments):
        return 0.0
    survival_weights = [1.0] * years if survival is None else list(survival)
    if len(survival_weights) < years:
        raise ValueError("survival must cover every projected working year")
    return present_value_stream(
        payments,
        discount_rate,
        survival=survival_weights[:years],
        start_period=1,
    )


def estimate_household_labor_wealth(
    *,
    respondent: PersonLaborInput,
    spouse: PersonLaborInput | None,
    survival_by_sex: dict[str, Sequence[float]],
    retirement_age: int = 67,
    employment_probability: float = 0.95,
    wage_growth: float = 0.015,
    discount_rate: float = 0.035,
    tax_rate: float = 0.0,
    mode: LaborMode = "continuation",
) -> HouseholdLaborWealth:
    def value(person: PersonLaborInput | None) -> float:
        if person is None:
            return 0.0
        if person.sex not in survival_by_sex:
            raise ValueError(f"missing survival curve for {person.sex}")
        return estimate_labor_wealth(
            current_income=person.current_income,
            age=person.age,
            retirement_age=retirement_age,
            survival=survival_by_sex[person.sex],
            reentry_income=person.reentry_income,
            reentry_probability=person.reentry_probability,
            employment_probability=employment_probability,
            wage_growth=wage_growth,
            discount_rate=discount_rate,
            tax_rate=tax_rate,
            mode=mode,
        )

    return HouseholdLaborWealth(respondent=value(respondent), spouse=value(spouse))
