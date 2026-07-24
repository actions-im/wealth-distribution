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

# Respondent second-job wage and nonworker former-job history
RESPONDENT_SECOND_WAGE_HOURS = "x4507"
RESPONDENT_SECOND_WAGE_WEEKS = "x4508"
RESPONDENT_SECOND_WAGE_AMOUNT = "x4509"
RESPONDENT_SECOND_WAGE_FREQUENCY = "x4510"
RESPONDENT_HISTORY_WAGE_FIELDS = (
    ("x4613", "x4614"),
    ("x4605", "x4606"),
)
RESPONDENT_CAREER_YEAR_FIELDS = (
    ("x4602", "x4616"),
)

# Spouse main-job wage
SPOUSE_WAGE_HOURS = "x4710"
SPOUSE_WAGE_WEEKS = "x4711"
SPOUSE_WAGE_AMOUNT = "x4712"
SPOUSE_WAGE_FREQUENCY = "x4713"

SPOUSE_SECOND_WAGE_HOURS = "x5107"
SPOUSE_SECOND_WAGE_WEEKS = "x5108"
SPOUSE_SECOND_WAGE_AMOUNT = "x5109"
SPOUSE_SECOND_WAGE_FREQUENCY = "x5110"
SPOUSE_HISTORY_WAGE_FIELDS = (
    ("x5213", "x5214"),
    ("x5205", "x5206"),
)
SPOUSE_CAREER_YEAR_FIELDS = (
    ("x5202", "x5216"),
)

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
    RESPONDENT_SECOND_WAGE_HOURS,
    RESPONDENT_SECOND_WAGE_WEEKS,
    RESPONDENT_SECOND_WAGE_AMOUNT,
    RESPONDENT_SECOND_WAGE_FREQUENCY,
    *(field for pair in RESPONDENT_HISTORY_WAGE_FIELDS for field in pair),
    *(field for pair in RESPONDENT_CAREER_YEAR_FIELDS for field in pair),
    SPOUSE_WAGE_HOURS,
    SPOUSE_WAGE_WEEKS,
    SPOUSE_WAGE_AMOUNT,
    SPOUSE_WAGE_FREQUENCY,
    SPOUSE_SECOND_WAGE_HOURS,
    SPOUSE_SECOND_WAGE_WEEKS,
    SPOUSE_SECOND_WAGE_AMOUNT,
    SPOUSE_SECOND_WAGE_FREQUENCY,
    *(field for pair in SPOUSE_HISTORY_WAGE_FIELDS for field in pair),
    *(field for pair in SPOUSE_CAREER_YEAR_FIELDS for field in pair),
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
    "x5320",
    "x6466",
    "x5323",
    "x5325",
    "x5326",
    "x5327",
    "x5328",
    "x6471",
    "x5331",
    "x5333",
    "x5334",
    "x5335",
    "x5336",
    "x6476",
    "x5415",
    "x5417",
    "x5418",
    "x5419",
    "x5420",
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
    historical_annual_wage: float | None = None
    career_years: int | None = None


@dataclass(frozen=True)
class PensionBenefitInput:
    owner: str
    annual_benefit: float
    claiming_age: int
    status: str
    has_cost_of_living_adjustment: bool | None = None


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

    respondent_wage = _total_current_wage(
        values,
        main_fields=(
            RESPONDENT_WAGE_AMOUNT,
            RESPONDENT_WAGE_FREQUENCY,
            RESPONDENT_WAGE_HOURS,
            RESPONDENT_WAGE_WEEKS,
        ),
        second_fields=(
            RESPONDENT_SECOND_WAGE_AMOUNT,
            RESPONDENT_SECOND_WAGE_FREQUENCY,
            RESPONDENT_SECOND_WAGE_HOURS,
            RESPONDENT_SECOND_WAGE_WEEKS,
        ),
    )
    respondent_career_years = _reported_career_years(
        values, RESPONDENT_CAREER_YEAR_FIELDS
    )
    respondent = PersonInput(
        age=int(as_number(values.get(RESPONDENT_AGE))),
        sex=_sex(values.get(RESPONDENT_SEX)),
        annual_wage=respondent_wage,
        annual_social_security=annualize(
            values.get(RESPONDENT_SS_AMOUNT), values.get(RESPONDENT_SS_FREQUENCY)
        ),
        social_security_benefit_type=_social_security_benefit_type(
            values.get(RESPONDENT_SS_TYPE)
        ),
        historical_annual_wage=(
            None
            if respondent_wage > 0 or respondent_career_years is None
            else _historical_annual_wage(values, RESPONDENT_HISTORY_WAGE_FIELDS)
        ),
        career_years=respondent_career_years,
    )
    spouse_age = int(as_number(values.get(SPOUSE_AGE)))
    spouse = None
    if spouse_age > 0:
        spouse_wage = _total_current_wage(
            values,
            main_fields=(
                SPOUSE_WAGE_AMOUNT,
                SPOUSE_WAGE_FREQUENCY,
                SPOUSE_WAGE_HOURS,
                SPOUSE_WAGE_WEEKS,
            ),
            second_fields=(
                SPOUSE_SECOND_WAGE_AMOUNT,
                SPOUSE_SECOND_WAGE_FREQUENCY,
                SPOUSE_SECOND_WAGE_HOURS,
                SPOUSE_SECOND_WAGE_WEEKS,
            ),
        )
        spouse_career_years = _reported_career_years(
            values, SPOUSE_CAREER_YEAR_FIELDS
        )
        spouse = PersonInput(
            age=spouse_age,
            sex=_sex(values.get(SPOUSE_SEX)),
            annual_wage=spouse_wage,
            annual_social_security=annualize(
                values.get(SPOUSE_SS_AMOUNT), values.get(SPOUSE_SS_FREQUENCY)
            ),
            social_security_benefit_type=_social_security_benefit_type(
                values.get(SPOUSE_SS_TYPE)
            ),
            historical_annual_wage=(
                None
                if spouse_wage > 0 or spouse_career_years is None
                else _historical_annual_wage(values, SPOUSE_HISTORY_WAGE_FIELDS)
            ),
            career_years=spouse_career_years,
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


def _total_current_wage(
    values: Mapping[str, object],
    *,
    main_fields: tuple[str, str, str, str],
    second_fields: tuple[str, str, str, str],
) -> float:
    return sum(
        annualize_wage(
            values.get(amount),
            values.get(frequency),
            values.get(hours),
            values.get(weeks),
        )
        for amount, frequency, hours, weeks in (main_fields, second_fields)
    )


def _historical_annual_wage(
    values: Mapping[str, object],
    fields: tuple[tuple[str, str], ...],
) -> float | None:
    for amount, frequency in fields:
        annual_wage = annualize(values.get(amount), values.get(frequency))
        if annual_wage > 0:
            return annual_wage
    return None


def _reported_career_years(
    values: Mapping[str, object],
    fields: tuple[tuple[str, str], ...],
) -> int | None:
    branch_years = [
        sum(max(int(as_number(values.get(field))), 0) for field in branch)
        for branch in fields
    ]
    reported = max(branch_years, default=0)
    return reported if reported > 0 else None


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
        ("x6461", "x5315", "x5317", "x5318", "x5319", "x5320"),
        ("x6466", "x5323", "x5325", "x5326", "x5327", "x5328"),
        ("x6471", "x5331", "x5333", "x5334", "x5335", "x5336"),
        ("x6476", "x5415", "x5417", "x5418", "x5419", "x5420"),
    ]
    pensions = []
    for account_plan, owner_field, years_field, amount, frequency, cola in fields:
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
                    has_cost_of_living_adjustment=_cola_status(values.get(cola)),
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


def _cola_status(value: object) -> bool | None:
    code = int(as_number(value))
    if code == 1:
        return True
    if code == 5:
        return False
    return None
