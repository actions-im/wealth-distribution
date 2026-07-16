from __future__ import annotations

from dataclasses import dataclass
import math
from numbers import Real
from typing import Mapping
from pathlib import Path
from zipfile import ZipFile

import numpy as np
import pandas as pd


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
    "y1", "yy1", "x14", "x19", "x8021", "x103", "x4112", "x4113", "x4712", "x4713",
    "x5306", "x5307", "x5311", "x5312",
    "x5603", "x5606", "x5607", "x5608", "x5609",
    "x5611", "x5614", "x5615", "x5616", "x5617",
    "x5619", "x5622", "x5623", "x5624", "x5625",
    "x5627", "x5630", "x5631", "x5632", "x5633",
    "x6461", "x5315", "x5317", "x5318", "x5319",
    "x6466", "x5323", "x5325", "x5326", "x5327",
    "x6471", "x5331", "x5333", "x5334", "x5335",
    "x6476", "x5415", "x5417", "x5418", "x5419",
    "x5819", "x5821", "x5825",
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
    numeric_amount = _number(amount)
    numeric_frequency = int(_number(frequency))
    if numeric_amount <= 0:
        return 0.0
    multiplier = FREQUENCY_MULTIPLIERS.get(numeric_frequency)
    return float(numeric_amount * multiplier) if multiplier else 0.0


def build_detailed_household_input(row: Mapping[str, object]) -> DetailedHouseholdInput:
    values = {str(key).lower(): value for key, value in row.items()}
    row_id = int(_number(values.get("y1")))
    family_id = int(_number(values.get("yy1"))) or row_id // 10
    implicate = row_id % 10 if row_id else 0

    respondent = PersonInput(
        age=int(_number(values.get("x14"))),
        sex=_sex(values.get("x8021")),
        annual_wage=annualize(values.get("x4112"), values.get("x4113")),
        annual_social_security=annualize(values.get("x5306"), values.get("x5307")),
    )
    spouse_age = int(_number(values.get("x19")))
    spouse = None
    if spouse_age > 0:
        spouse = PersonInput(
            age=spouse_age,
            sex=_sex(values.get("x103")),
            annual_wage=annualize(values.get("x4712"), values.get("x4713")),
            annual_social_security=annualize(values.get("x5311"), values.get("x5312")),
        )

    pensions = _future_db_pensions(values) + _current_db_pensions(values, respondent, spouse)
    expected_inheritance_amount = _positive_finite_amount(values.get("x5821"))
    if not _is_affirmative_scf_code(values.get("x5819")):
        expected_inheritance_amount = 0.0

    return DetailedHouseholdInput(
        row_id=row_id,
        family_id=family_id,
        implicate=implicate,
        respondent=respondent,
        spouse=spouse,
        db_pensions=tuple(pensions),
        expected_inheritance_amount=expected_inheritance_amount,
        expects_sizable_estate=_is_affirmative_scf_code(values.get("x5825")),
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
        if int(_number(values.get(plan_type))) != 1:
            continue
        annual_benefit = annualize(values.get(amount), values.get(frequency))
        claiming_age = int(_number(values.get(claim_age)))
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
        if int(_number(values.get(account_plan))) != 5:
            continue
        annual_benefit = annualize(values.get(amount), values.get(frequency))
        owner = _owner(values.get(owner_field))
        person = spouse if owner == "spouse" else respondent
        years_receiving = max(int(_number(values.get(years_field))), 0)
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


def _number(value: object) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    return number if number == number else 0.0


def _is_affirmative_scf_code(value: object) -> bool:
    return (
        isinstance(value, Real)
        and not _is_boolean_scalar(value)
        and math.isfinite(float(value))
        and value == 1
    )


def _positive_finite_amount(value: object) -> float:
    if _is_boolean_scalar(value):
        return 0.0
    amount = _number(value)
    return amount if math.isfinite(amount) and amount > 0 else 0.0


def _is_boolean_scalar(value: object) -> bool:
    return isinstance(value, (bool, np.bool_))


def _sex(value: object) -> str:
    return {1: "male", 2: "female"}.get(int(_number(value)), "unknown")


def _owner(value: object) -> str:
    return "spouse" if int(_number(value)) == 2 else "respondent"
