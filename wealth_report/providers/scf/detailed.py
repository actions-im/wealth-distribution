from __future__ import annotations

from dataclasses import dataclass
import math
from numbers import Real
from typing import Mapping
from pathlib import Path
from zipfile import ZipFile

import pandas as pd

from wealth_report.model.numeric import as_number, is_boolean_scalar


# ---------------------------------------------------------------------------
# SCF full-file (p22i6.dta) field codes — 2022 public microdata
# ---------------------------------------------------------------------------
ROW_ID = "y1"
FAMILY_ID = "yy1"
RESPONDENT_AGE = "x14"
RESPONDENT_SEX = "x8021"
SPOUSE_AGE = "x19"
SPOUSE_SEX = "x103"

# Respondent main-job wage: hours, weeks, amount, frequency
RESPONDENT_WAGE_HOURS = "x4110"
RESPONDENT_WAGE_WEEKS = "x4111"
RESPONDENT_WAGE_AMOUNT = "x4112"
RESPONDENT_WAGE_FREQUENCY = "x4113"

# Spouse main-job wage
SPOUSE_WAGE_HOURS = "x4710"
SPOUSE_WAGE_WEEKS = "x4711"
SPOUSE_WAGE_AMOUNT = "x4712"
SPOUSE_WAGE_FREQUENCY = "x4713"

# Current Social Security: type, amount, frequency (respondent / spouse)
RESPONDENT_SS_TYPE = "x5304"
RESPONDENT_SS_AMOUNT = "x5306"
RESPONDENT_SS_FREQUENCY = "x5307"
SPOUSE_SS_TYPE = "x5309"
SPOUSE_SS_AMOUNT = "x5311"
SPOUSE_SS_FREQUENCY = "x5312"

# Expected inheritance and estate intent
EXPECTS_INHERITANCE = "x5819"
EXPECTED_INHERITANCE_AMOUNT = "x5821"
EXPECTS_SIZABLE_ESTATE = "x5825"

FREQUENCY_MULTIPLIERS = {
    1: 260.0,
    2: 52.0,
    3: 26.0,
    4: 12.0,
    5: 4.0,
    6: 1.0,
    11: 2.0,
    12: 6.0,
}

DETAILED_COLUMNS = [
    ROW_ID,
    FAMILY_ID,
    RESPONDENT_AGE,
    SPOUSE_AGE,
    RESPONDENT_SEX,
    SPOUSE_SEX,
    RESPONDENT_WAGE_HOURS,
    RESPONDENT_WAGE_WEEKS,
    RESPONDENT_WAGE_AMOUNT,
    RESPONDENT_WAGE_FREQUENCY,
    SPOUSE_WAGE_HOURS,
    SPOUSE_WAGE_WEEKS,
    SPOUSE_WAGE_AMOUNT,
    SPOUSE_WAGE_FREQUENCY,
    RESPONDENT_SS_TYPE,
    RESPONDENT_SS_AMOUNT,
    RESPONDENT_SS_FREQUENCY,
    SPOUSE_SS_TYPE,
    SPOUSE_SS_AMOUNT,
    SPOUSE_SS_FREQUENCY,
    # Future DB pension slots (type, owner, claim age, amount, frequency) × 4
    "x5603",
    "x5606",
    "x5607",
    "x5608",
    "x5609",
    "x5611",
    "x5614",
    "x5615",
    "x5616",
    "x5617",
    "x5619",
    "x5622",
    "x5623",
    "x5624",
    "x5625",
    "x5627",
    "x5630",
    "x5631",
    "x5632",
    "x5633",
    # Current DB pension slots × 4
    "x6461",
    "x5315",
    "x5317",
    "x5318",
    "x5319",
    "x6466",
    "x5323",
    "x5325",
    "x5326",
    "x5327",
    "x6471",
    "x5331",
    "x5333",
    "x5334",
    "x5335",
    "x6476",
    "x5415",
    "x5417",
    "x5418",
    "x5419",
    EXPECTS_INHERITANCE,
    EXPECTED_INHERITANCE_AMOUNT,
    EXPECTS_SIZABLE_ESTATE,
]


def load_detailed_scf(zip_path: str | Path) -> pd.DataFrame:
    with ZipFile(zip_path) as archive:
        members = [name for name in archive.namelist() if name.lower().endswith(".dta")]
        if members != ["p22i6.dta"]:
            raise ValueError(f"expected exact SCF member p22i6.dta, found {members}")
        with archive.open(members[0]) as source:
            return pd.read_stata(source, columns=DETAILED_COLUMNS, convert_categoricals=False)


@dataclass(frozen=True)
class PersonInput:
    age: int
    sex: str
    annual_wage: float
    annual_social_security: float
    social_security_benefit_type: str = "none"


@dataclass(frozen=True)
class PensionBenefitInput:
    owner: str
    annual_benefit: float
    claiming_age: int
    status: str


@dataclass(frozen=True)
class DetailedHouseholdInput:
    row_id: int
    family_id: int
    implicate: int
    respondent: PersonInput
    spouse: PersonInput | None
    db_pensions: tuple[PensionBenefitInput, ...]
    expected_inheritance_amount: float = 0.0
    expects_sizable_estate: bool = False


def annualize(amount: object, frequency: object) -> float:
    numeric_amount = as_number(amount)
    numeric_frequency = int(as_number(frequency))
    if numeric_amount <= 0:
        return 0.0
    multiplier = FREQUENCY_MULTIPLIERS.get(numeric_frequency)
    return float(numeric_amount * multiplier) if multiplier else 0.0


def annualize_wage(
    amount: object,
    frequency: object,
    hours_per_week: object,
    weeks_per_year: object,
) -> float:
    """Annualize a main-job wage using the SCF's documented work schedule fields."""
    numeric_amount = as_number(amount)
    numeric_frequency = int(as_number(frequency))
    if numeric_amount <= 0:
        return 0.0

    weeks = as_number(weeks_per_year)
    if numeric_frequency == 18:  # Hour
        return float(numeric_amount * as_number(hours_per_week) * weeks)
    if numeric_frequency == 31:  # Twice a month
        return float(numeric_amount * 24.0)
    if numeric_frequency == 1:  # Day; SCF does not collect days per week.
        return float(numeric_amount * 5.0 * weeks) if weeks > 0 else 0.0
    if numeric_frequency == 2:  # Week
        return float(numeric_amount * weeks) if weeks > 0 else 0.0
    if numeric_frequency == 3:  # Every two weeks
        return float(numeric_amount * weeks / 2.0) if weeks > 0 else 0.0
    if numeric_frequency == 8:  # One payment for the whole year
        return float(numeric_amount)
    if numeric_frequency == 21:  # Three times a year
        return float(numeric_amount * 3.0)
    multiplier = FREQUENCY_MULTIPLIERS.get(numeric_frequency)
    return float(numeric_amount * multiplier) if multiplier else 0.0


def build_detailed_household_input(row: Mapping[str, object]) -> DetailedHouseholdInput:
    values = {str(key).lower(): value for key, value in row.items()}
    row_id = int(as_number(values.get(ROW_ID)))
    family_id = int(as_number(values.get(FAMILY_ID))) or row_id // 10
    implicate = row_id % 10 if row_id else 0

    respondent = PersonInput(
        age=int(as_number(values.get(RESPONDENT_AGE))),
        sex=_sex(values.get(RESPONDENT_SEX)),
        annual_wage=annualize_wage(
            values.get(RESPONDENT_WAGE_AMOUNT),
            values.get(RESPONDENT_WAGE_FREQUENCY),
            values.get(RESPONDENT_WAGE_HOURS),
            values.get(RESPONDENT_WAGE_WEEKS),
        ),
        annual_social_security=annualize(
            values.get(RESPONDENT_SS_AMOUNT), values.get(RESPONDENT_SS_FREQUENCY)
        ),
        social_security_benefit_type=_social_security_benefit_type(
            values.get(RESPONDENT_SS_TYPE)
        ),
    )
    spouse_age = int(as_number(values.get(SPOUSE_AGE)))
    spouse = None
    if spouse_age > 0:
        spouse = PersonInput(
            age=spouse_age,
            sex=_sex(values.get(SPOUSE_SEX)),
            annual_wage=annualize_wage(
                values.get(SPOUSE_WAGE_AMOUNT),
                values.get(SPOUSE_WAGE_FREQUENCY),
                values.get(SPOUSE_WAGE_HOURS),
                values.get(SPOUSE_WAGE_WEEKS),
            ),
            annual_social_security=annualize(
                values.get(SPOUSE_SS_AMOUNT), values.get(SPOUSE_SS_FREQUENCY)
            ),
            social_security_benefit_type=_social_security_benefit_type(
                values.get(SPOUSE_SS_TYPE)
            ),
        )

    pensions = _future_db_pensions(values) + _current_db_pensions(values, respondent, spouse)
    expected_inheritance_amount = _positive_finite_amount(
        values.get(EXPECTED_INHERITANCE_AMOUNT)
    )
    if not _is_affirmative_scf_code(values.get(EXPECTS_INHERITANCE)):
        expected_inheritance_amount = 0.0

    return DetailedHouseholdInput(
        row_id=row_id,
        family_id=family_id,
        implicate=implicate,
        respondent=respondent,
        spouse=spouse,
        db_pensions=tuple(pensions),
        expected_inheritance_amount=expected_inheritance_amount,
        expects_sizable_estate=_is_affirmative_scf_code(values.get(EXPECTS_SIZABLE_ESTATE)),
    )


def _future_db_pensions(values: Mapping[str, object]) -> list[PensionBenefitInput]:
    fields = [
        ("x5603", "x5606", "x5607", "x5608", "x5609"),
        ("x5611", "x5614", "x5615", "x5616", "x5617"),
        ("x5619", "x5622", "x5623", "x5624", "x5625"),
        ("x5627", "x5630", "x5631", "x5632", "x5633"),
    ]
    pensions = []
    for plan_type, owner, claim_age, amount, frequency in fields:
        if int(as_number(values.get(plan_type))) != 1:
            continue
        annual_benefit = annualize(values.get(amount), values.get(frequency))
        claiming_age = int(as_number(values.get(claim_age)))
        if annual_benefit > 0 and claiming_age > 0:
            pensions.append(
                PensionBenefitInput(
                    owner=_owner(values.get(owner)),
                    annual_benefit=annual_benefit,
                    claiming_age=claiming_age,
                    status="future",
                )
            )
    return pensions


def _current_db_pensions(
    values: Mapping[str, object],
    respondent: PersonInput,
    spouse: PersonInput | None,
) -> list[PensionBenefitInput]:
    fields = [
        ("x6461", "x5315", "x5317", "x5318", "x5319"),
        ("x6466", "x5323", "x5325", "x5326", "x5327"),
        ("x6471", "x5331", "x5333", "x5334", "x5335"),
        ("x6476", "x5415", "x5417", "x5418", "x5419"),
    ]
    pensions = []
    for account_plan, owner_field, years_field, amount, frequency in fields:
        if int(as_number(values.get(account_plan))) != 5:
            continue
        annual_benefit = annualize(values.get(amount), values.get(frequency))
        owner = _owner(values.get(owner_field))
        person = spouse if owner == "spouse" else respondent
        years_receiving = max(int(as_number(values.get(years_field))), 0)
        if annual_benefit > 0 and person is not None:
            pensions.append(
                PensionBenefitInput(
                    owner=owner,
                    annual_benefit=annual_benefit,
                    claiming_age=max(person.age - years_receiving, 0),
                    status="current",
                )
            )
    return pensions


def _is_affirmative_scf_code(value: object) -> bool:
    return (
        isinstance(value, Real)
        and not is_boolean_scalar(value)
        and math.isfinite(float(value))
        and value == 1
    )


def _positive_finite_amount(value: object) -> float:
    if is_boolean_scalar(value):
        return 0.0
    amount = as_number(value)
    return amount if math.isfinite(amount) and amount > 0 else 0.0


def _sex(value: object) -> str:
    return {1: "male", 2: "female"}.get(int(as_number(value)), "unknown")


def _social_security_benefit_type(value: object) -> str:
    return {
        1: "retirement",
        2: "disability",
        3: "survivor_or_dependent",
        6: "survivor_or_dependent",
        7: "ssi",
        8: "ssi",
    }.get(int(as_number(value)), "none")


def _owner(value: object) -> str:
    return "spouse" if int(as_number(value)) == 2 else "respondent"
