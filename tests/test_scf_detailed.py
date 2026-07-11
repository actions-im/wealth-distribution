import pandas as pd
import pytest

from src.real_data import normalize_scf_rows
from src.scf_detailed import build_detailed_household_input


def test_normalization_preserves_family_and_implicate_ids():
    data = normalize_scf_rows(
        pd.DataFrame(
            [
                {
                    "y1": 12341,
                    "yy1": 1234,
                    "wgt": 2,
                    "age": 40,
                    "wageinc": 10,
                    "networth": 20,
                }
            ]
        )
    )

    assert data.loc[0, "family_id"] == 1234
    assert data.loc[0, "implicate"] == 1
    assert data.loc[0, "scf_row_id"] == 12341


def test_detailed_inputs_keep_people_and_social_security_separate():
    household = build_detailed_household_input(
        {
            "y1": 12341,
            "yy1": 1234,
            "x14": 64,
            "x19": 40,
            "x8021": 1,
            "x103": 2,
            "x4112": 100_000,
            "x4113": 6,
            "x4712": 4_000,
            "x4713": 4,
            "x5306": 2_000,
            "x5307": 4,
            "x5311": 0,
            "x5312": 0,
        }
    )

    assert household.respondent.age == 64
    assert household.spouse is not None
    assert household.spouse.age == 40
    assert household.respondent.annual_wage == pytest.approx(100_000)
    assert household.spouse.annual_wage == pytest.approx(48_000)
    assert household.respondent.annual_social_security == pytest.approx(24_000)
    assert household.spouse.annual_social_security == 0


def test_future_db_benefit_is_mapped_without_account_balance():
    household = build_detailed_household_input(
        {
            "y1": 12341,
            "yy1": 1234,
            "x14": 55,
            "x19": 0,
            "x8021": 1,
            "x103": 0,
            "x5603": 1,
            "x5606": 1,
            "x5607": 65,
            "x5608": 2_500,
            "x5609": 4,
        }
    )

    assert len(household.db_pensions) == 1
    benefit = household.db_pensions[0]
    assert benefit.owner == "respondent"
    assert benefit.claiming_age == 65
    assert benefit.annual_benefit == pytest.approx(30_000)
    assert benefit.status == "future"
