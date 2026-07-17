"""Value detailed SCF households into comprehensive resource components."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Mapping, Sequence

import pandas as pd

from wealth_report.model.actuarial import conditional_survival
from wealth_report.model.assumptions import ModelAssumptions
from wealth_report.model.income_security import value_income_security_floor
from wealth_report.model.inheritance import allocate_inheritance_reallocation
from wealth_report.model.labor import estimate_labor_wealth, projected_labor_income_stream
from wealth_report.model.numeric import is_finite_numeric
from wealth_report.model.pensions import (
    DefinedBenefitPlan,
    defined_benefit_income_stream,
    value_defined_benefit_plan,
)
from wealth_report.model.social_security import (
    SocialSecurityPerson,
    social_security_income_stream,
    social_security_wealth,
)
from wealth_report.providers.scf.detailed import DetailedHouseholdInput, PersonInput
from wealth_report.report.ranking import age_group
from wealth_report.report.types import (
    ComprehensiveHouseholdInput,
    ComprehensiveHouseholdRecord,
    build_comprehensive_household,
    continuation_resources_total,
)


def apply_inheritance_reallocation(
    households: pd.DataFrame,
    *,
    life_table: dict[str, dict[int, float]],
    assumptions: ModelAssumptions,
) -> pd.DataFrame:
    """Reallocate expected inheritance claims without changing current net worth."""
    component_columns = (
        "net_worth",
        "continuation_labor",
        "continuation_social_security",
        "continuation_db_pension",
        "continuation_income_security_floor",
    )
    missing = set(component_columns).difference(households.columns)
    if missing:
        raise ValueError(
            "inheritance reallocation is missing continuation components: "
            f"{sorted(missing)}"
        )
    for column in component_columns:
        if not households[column].map(is_finite_numeric).all():
            raise ValueError(
                f"inheritance reallocation {column} must be finite and numeric"
            )
    allocated, _ = allocate_inheritance_reallocation(
        households,
        life_table=life_table,
        horizon_years=assumptions.inheritance_horizon_years,
        discount_rate=assumptions.discount_rate,
    )
    allocated["continuation_expected_inheritance"] = allocated["inheritance_credit"]
    allocated["continuation_estate_donor_reserve"] = allocated["estate_donor_reserve"]
    allocated["continuation_resources"] = continuation_resources_total(
        net_worth=allocated["net_worth"],
        continuation_labor=allocated["continuation_labor"],
        continuation_social_security=allocated["continuation_social_security"],
        continuation_db_pension=allocated["continuation_db_pension"],
        continuation_income_security_floor=allocated["continuation_income_security_floor"],
        continuation_expected_inheritance=allocated["continuation_expected_inheritance"],
        continuation_estate_donor_reserve=allocated["continuation_estate_donor_reserve"],
    )
    return allocated


def value_detailed_household(
    *,
    net_worth: float,
    household: DetailedHouseholdInput,
    life_table: dict[str, dict[int, float]],
    assumptions: ModelAssumptions = ModelAssumptions(),
    reentry_wage_schedule: Mapping[tuple[str, str], float] | None = None,
    survival_cache: dict[tuple[str, int], list[float]] | None = None,
) -> ComprehensiveHouseholdRecord:
    """Value person-level SCF inputs and retain explicit model exclusions.

    Pass a shared ``survival_cache`` when valuing many households so survival
    curves are reused across people with the same sex and age.
    """
    exclusions: set[str] = set()
    people = _household_people(household)
    survival = {
        owner: _future_survival(
            person,
            life_table=life_table,
            exclusions=exclusions,
            survival_cache=survival_cache,
        )
        for owner, person in people
    }

    labor = _value_labor(
        people,
        survival=survival,
        assumptions=assumptions,
        reentry_wage_schedule=reentry_wage_schedule,
        exclusions=exclusions,
    )
    social = _value_social_security(
        people,
        survival=survival,
        assumptions=assumptions,
        exclusions=exclusions,
    )
    pension = _value_pensions(
        household,
        people=people,
        survival=survival,
        assumptions=assumptions,
        exclusions=exclusions,
    )
    floor = _value_income_floor(
        people=people,
        survival=survival,
        labor_streams=labor.streams,
        social_streams=social.streams,
        pension_streams=pension.streams,
        assumptions=assumptions,
    )

    return build_comprehensive_household(
        ComprehensiveHouseholdInput(
            net_worth=float(net_worth),
            accrued_labor=labor.accrued,
            continuation_labor=labor.continuation,
            accrued_social_security=social.accrued,
            continuation_social_security=social.continuation,
            accrued_db_pension=pension.accrued,
            continuation_db_pension=pension.continuation,
            continuation_income_security_floor=floor,
            exclusions=tuple(sorted(exclusions)),
            assumption_version=assumptions.version,
        )
    )


@dataclass(frozen=True)
class _ComponentTotals:
    accrued: float
    continuation: float
    streams: dict[str, list[float]] | dict[str, list[list[float]]]


def _household_people(
    household: DetailedHouseholdInput,
) -> list[tuple[str, PersonInput]]:
    people = [("respondent", household.respondent)]
    if household.spouse is not None:
        people.append(("spouse", household.spouse))
    return people


def _future_survival(
    person: PersonInput,
    *,
    life_table: dict[str, dict[int, float]],
    exclusions: set[str],
    survival_cache: dict[tuple[str, int], list[float]] | None = None,
) -> list[float]:
    if person.sex not in life_table:
        exclusions.add(f"unknown_sex_{person.sex}")
        return []
    key = (person.sex, int(person.age))
    if survival_cache is not None and key in survival_cache:
        return survival_cache[key]
    curve = conditional_survival(life_table[person.sex], person.age)[1:]
    if survival_cache is not None:
        survival_cache[key] = curve
    return curve


def _value_labor(
    people: Sequence[tuple[str, PersonInput]],
    *,
    survival: Mapping[str, list[float]],
    assumptions: ModelAssumptions,
    reentry_wage_schedule: Mapping[tuple[str, str], float] | None,
    exclusions: set[str],
) -> _ComponentTotals:
    defensive = 0.0
    continuation = 0.0
    streams: dict[str, list[float]] = {}
    for owner, person in people:
        if not survival[owner]:
            exclusions.add(f"labor_missing_survival_{owner}")
            continue
        reentry_income = 0.0
        if person.age < assumptions.retirement_age and reentry_wage_schedule:
            reentry_income = float(
                reentry_wage_schedule.get((person.sex, age_group(person.age)), 0.0)
            )
        streams[owner] = projected_labor_income_stream(
            current_income=person.annual_wage,
            age=person.age,
            retirement_age=assumptions.retirement_age,
            reentry_income=reentry_income,
            reentry_probability=assumptions.reentry_probability,
            employment_probability=assumptions.employment_probability,
            wage_growth=assumptions.wage_growth,
            tax_rate=assumptions.tax_rate,
            mode="continuation",
        )
        for mode, target in (("defensive", "defensive"), ("continuation", "continuation")):
            value = estimate_labor_wealth(
                current_income=person.annual_wage,
                age=person.age,
                retirement_age=assumptions.retirement_age,
                survival=survival[owner],
                reentry_income=reentry_income,
                reentry_probability=assumptions.reentry_probability,
                employment_probability=assumptions.employment_probability,
                wage_growth=assumptions.wage_growth,
                discount_rate=assumptions.discount_rate,
                tax_rate=assumptions.tax_rate,
                mode=mode,
            )
            if target == "defensive":
                defensive += value
            else:
                continuation += value
    return _ComponentTotals(accrued=defensive, continuation=continuation, streams=streams)


def _value_social_security(
    people: Sequence[tuple[str, PersonInput]],
    *,
    survival: Mapping[str, list[float]],
    assumptions: ModelAssumptions,
    exclusions: set[str],
) -> _ComponentTotals:
    accrued = 0.0
    continuation = 0.0
    streams: dict[str, list[float]] = {}
    for owner, person in people:
        if not survival[owner]:
            exclusions.add(f"social_security_missing_survival_{owner}")
            continue
        career_years = min(max(person.age - 22, 0), 35)
        ss_person = SocialSecurityPerson(
            age=person.age,
            annual_wage=person.annual_wage,
            annual_reported_benefit=person.annual_social_security,
            reported_benefit_type=person.social_security_benefit_type,
            career_years=career_years,
            claiming_age=assumptions.retirement_age,
        )
        for mode in ("accrued", "continuation"):
            result = social_security_wealth(
                ss_person,
                mode=mode,
                survival=survival[owner],
                discount_rate=assumptions.discount_rate,
                payable_factor=assumptions.payable_benefit_factor,
                retirement_age=assumptions.retirement_age,
            )
            if mode == "accrued":
                accrued += result.net
            else:
                continuation += result.net
            exclusions.update(result.exclusions)
        streams[owner] = social_security_income_stream(
            ss_person,
            survival=survival[owner],
            payable_factor=assumptions.payable_benefit_factor,
            retirement_age=assumptions.retirement_age,
            mode="continuation",
        )
    return _ComponentTotals(accrued=accrued, continuation=continuation, streams=streams)


def _value_pensions(
    household: DetailedHouseholdInput,
    *,
    people: Sequence[tuple[str, PersonInput]],
    survival: Mapping[str, list[float]],
    assumptions: ModelAssumptions,
    exclusions: set[str],
) -> _ComponentTotals:
    accrued = 0.0
    continuation = 0.0
    streams: dict[str, list[list[float]]] = {owner: [] for owner, _ in people}
    for pension in household.db_pensions:
        person = household.spouse if pension.owner == "spouse" else household.respondent
        if person is None or not survival.get(pension.owner):
            exclusions.add(f"pension_missing_owner_or_survival_{pension.owner}")
            continue
        remaining = max(assumptions.retirement_age - person.age, 0)
        career = max(person.age - 22, 0)
        accrued_fraction = (
            1.0 if pension.status == "current" else career / max(career + remaining, 1)
        )
        plan = DefinedBenefitPlan(
            annual_benefit=pension.annual_benefit,
            current_age=person.age,
            claiming_age=pension.claiming_age,
            accrued_fraction=min(max(accrued_fraction, 0), 1),
        )
        for mode in ("accrued", "continuation"):
            result = value_defined_benefit_plan(
                plan,
                mode=mode,
                survival=survival[pension.owner],
                discount_rate=assumptions.discount_rate,
            )
            if mode == "accrued":
                accrued += result.present_value
            else:
                continuation += result.present_value
            exclusions.update(result.exclusions)
        streams[pension.owner].append(
            defined_benefit_income_stream(
                plan,
                mode="continuation",
                years=len(survival[pension.owner]),
            )
        )
    return _ComponentTotals(accrued=accrued, continuation=continuation, streams=streams)


def _value_income_floor(
    *,
    people: Sequence[tuple[str, PersonInput]],
    survival: Mapping[str, list[float]],
    labor_streams: Mapping[str, list[float]],
    social_streams: Mapping[str, list[float]],
    pension_streams: Mapping[str, list[list[float]]],
    assumptions: ModelAssumptions,
) -> float:
    horizon = max((len(values) for values in survival.values()), default=0)
    annual_other_income = [0.0] * horizon
    household_survival = [0.0] * horizon
    for period in range(horizon):
        survival_values = [
            curve[period] for curve in survival.values() if period < len(curve)
        ]
        household_survival[period] = (
            1 - math.prod(1 - value for value in survival_values)
            if survival_values
            else 0.0
        )
        for owner, _ in people:
            if period < len(labor_streams.get(owner, [])):
                annual_other_income[period] += labor_streams[owner][period]
            if period < len(social_streams.get(owner, [])):
                annual_other_income[period] += social_streams[owner][period]
            for stream in pension_streams.get(owner, []):
                if period < len(stream):
                    annual_other_income[period] += stream[period]
    return value_income_security_floor(
        other_income=annual_other_income,
        monthly_benchmark=assumptions.income_security_floor_monthly,
        adult_count=len(people),
        survival=household_survival,
        discount_rate=assumptions.discount_rate,
    )
