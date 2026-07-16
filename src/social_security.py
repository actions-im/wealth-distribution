from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Literal, Sequence

from src.actuarial import present_value_stream
from src.ssa_parameters import parameters_for_year, primary_insurance_amount

SocialSecurityMode = Literal["accrued", "continuation"]


@dataclass(frozen=True)
class SocialSecurityPerson:
    age: int
    annual_wage: float
    career_years: int
    annual_reported_benefit: float = 0.0
    claiming_age: int = 67


@dataclass(frozen=True)
class SocialSecurityWealth:
    gross_benefits: float
    payable_factor: float
    future_employee_contributions: float
    net: float
    annual_scheduled_benefit: float
    credited_years: int
    used_reported_benefit: bool
    exclusions: tuple[str, ...] = ("spousal_and_survivor_benefits",)


def claiming_age_factor(claiming_age: int, *, full_retirement_age: int = 67) -> float:
    """Approximate retired-worker reduction or delayed-retirement credit."""
    months = (int(claiming_age) - int(full_retirement_age)) * 12
    if months == 0:
        return 1.0
    if months > 0:
        return 1 + min(months, 36) * (0.08 / 12)
    early_months = -months
    first_36 = min(early_months, 36)
    excess = max(early_months - 36, 0)
    return max(0.0, 1 - first_36 * (5 / 9 / 100) - excess * (5 / 12 / 100))


def _validate_person(person: SocialSecurityPerson) -> None:
    if person.age < 0 or person.age > 119:
        raise ValueError("age must be between 0 and 119")
    if person.career_years < 0:
        raise ValueError("career_years cannot be negative")
    for value, name in (
        (person.annual_wage, "annual_wage"),
        (person.annual_reported_benefit, "annual_reported_benefit"),
    ):
        if not math.isfinite(value) or value < 0:
            raise ValueError(f"{name} must be finite and nonnegative")


def social_security_wealth(
    person: SocialSecurityPerson,
    *,
    mode: SocialSecurityMode,
    survival: Sequence[float],
    discount_rate: float = 0.035,
    payable_factor: float = 0.80,
    year: int = 2022,
    retirement_age: int = 67,
) -> SocialSecurityWealth:
    """Value retired-worker benefits net of modeled future employee OASDI tax.

    The earnings history is a transparent proxy because the SCF does not contain
    respondents' SSA earnings records. Spousal and survivor benefits are excluded.
    """
    _validate_person(person)
    if mode not in {"accrued", "continuation"}:
        raise ValueError("mode must be 'accrued' or 'continuation'")
    if not math.isfinite(payable_factor) or not 0 <= payable_factor <= 1:
        raise ValueError("payable_factor must be between zero and one")
    if not survival:
        raise ValueError("survival cannot be empty")

    parameters = parameters_for_year(year)
    remaining_work_years = max(retirement_age - person.age, 0)
    added_years = remaining_work_years if mode == "continuation" else 0
    credited_years = min(person.career_years + added_years, 35)
    covered_wage = min(person.annual_wage, parameters.taxable_maximum)

    used_reported_benefit = person.annual_reported_benefit > 0
    if used_reported_benefit:
        annual_benefit = person.annual_reported_benefit
    else:
        aime = covered_wage * credited_years / 35 / 12
        annual_benefit = (
            primary_insurance_amount(aime, year=year)
            * 12
            * claiming_age_factor(
                person.claiming_age, full_retirement_age=parameters.full_retirement_age
            )
        )

    benefit_start_age = person.age if used_reported_benefit else max(person.claiming_age, person.age)
    benefit_offset = benefit_start_age - person.age
    benefit_survival = list(survival)[max(benefit_offset - 1, 0) :]
    gross_benefits = present_value_stream(
        [annual_benefit] * len(benefit_survival),
        discount_rate,
        survival=benefit_survival,
        start_period=max(benefit_offset, 1),
    )

    contribution_years = min(remaining_work_years, len(survival))
    future_employee_contributions = present_value_stream(
        [covered_wage * parameters.employee_oasdi_rate] * contribution_years,
        discount_rate,
        survival=list(survival)[:contribution_years],
        start_period=1,
    )
    net = gross_benefits * payable_factor - future_employee_contributions
    return SocialSecurityWealth(
        gross_benefits=gross_benefits,
        payable_factor=payable_factor,
        future_employee_contributions=future_employee_contributions,
        net=net,
        annual_scheduled_benefit=annual_benefit,
        credited_years=credited_years,
        used_reported_benefit=used_reported_benefit,
    )


def social_security_income_stream(
    person: SocialSecurityPerson,
    *,
    survival: Sequence[float],
    payable_factor: float,
    retirement_age: int,
    mode: SocialSecurityMode = "continuation",
) -> list[float]:
    """Return annual scheduled Social Security cash benefits for floor netting."""
    result = social_security_wealth(
        person,
        mode=mode,
        survival=survival,
        discount_rate=0.0,
        payable_factor=payable_factor,
        retirement_age=retirement_age,
    )
    if person.annual_reported_benefit > 0:
        start = 0
    else:
        start = max(max(person.claiming_age, person.age) - person.age, 1) - 1
    return [
        result.annual_scheduled_benefit * payable_factor if index >= start else 0.0
        for index in range(len(survival))
    ]
