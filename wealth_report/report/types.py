"""Shared household resource types and totals."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


SCF_2022_DATASET_LABEL = "Federal Reserve 2022 SCF public summary extract"


@dataclass(frozen=True)
class ComprehensiveHouseholdInput:
    net_worth: float
    accrued_labor: float
    continuation_labor: float
    accrued_social_security: float
    continuation_social_security: float
    accrued_db_pension: float
    continuation_db_pension: float
    continuation_income_security_floor: float = 0.0
    continuation_expected_inheritance: float = 0.0
    continuation_estate_donor_reserve: float = 0.0
    exclusions: tuple[str, ...] = ()
    source_version: str = "scf-2022"
    assumption_version: str = "2022-baseline-v1"


@dataclass(frozen=True)
class ComprehensiveHouseholdRecord:
    net_worth: float
    accrued_labor: float
    continuation_labor: float
    accrued_social_security: float
    continuation_social_security: float
    accrued_db_pension: float
    continuation_db_pension: float
    continuation_income_security_floor: float
    defensive_resources: float
    continuation_resources: float
    exclusions: tuple[str, ...]
    source_version: str
    assumption_version: str
    continuation_expected_inheritance: float = 0.0
    continuation_estate_donor_reserve: float = 0.0


def defensive_resources_total(
    *,
    net_worth,
    accrued_labor,
    accrued_social_security,
    accrued_db_pension,
):
    """Works for scalars or aligned pandas Series."""
    return net_worth + accrued_labor + accrued_social_security + accrued_db_pension


def continuation_resources_total(
    *,
    net_worth,
    continuation_labor,
    continuation_social_security,
    continuation_db_pension,
    continuation_income_security_floor=0.0,
    continuation_expected_inheritance=0.0,
    continuation_estate_donor_reserve=0.0,
):
    """Single definition of continuation resources used by assembly and inheritance.

    Works for scalars or aligned pandas Series.
    """
    return (
        net_worth
        + continuation_labor
        + continuation_social_security
        + continuation_db_pension
        + continuation_income_security_floor
        + continuation_expected_inheritance
        - continuation_estate_donor_reserve
    )


def build_comprehensive_household(
    household: ComprehensiveHouseholdInput,
) -> ComprehensiveHouseholdRecord:
    """Assemble auditable totals from separately valued household components."""
    values = (
        household.net_worth,
        household.accrued_labor,
        household.continuation_labor,
        household.accrued_social_security,
        household.continuation_social_security,
        household.accrued_db_pension,
        household.continuation_db_pension,
        household.continuation_income_security_floor,
        household.continuation_expected_inheritance,
        household.continuation_estate_donor_reserve,
    )
    if any(pd.isna(value) for value in values):
        raise ValueError("comprehensive household components cannot be missing")
    return ComprehensiveHouseholdRecord(
        **household.__dict__,
        defensive_resources=float(
            defensive_resources_total(
                net_worth=household.net_worth,
                accrued_labor=household.accrued_labor,
                accrued_social_security=household.accrued_social_security,
                accrued_db_pension=household.accrued_db_pension,
            )
        ),
        continuation_resources=float(
            continuation_resources_total(
                net_worth=household.net_worth,
                continuation_labor=household.continuation_labor,
                continuation_social_security=household.continuation_social_security,
                continuation_db_pension=household.continuation_db_pension,
                continuation_income_security_floor=household.continuation_income_security_floor,
                continuation_expected_inheritance=household.continuation_expected_inheritance,
                continuation_estate_donor_reserve=household.continuation_estate_donor_reserve,
            )
        ),
    )
