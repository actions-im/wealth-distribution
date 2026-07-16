import numpy as np
import pandas as pd
import pytest

from src.real_data import normalize_scf_rows
from src.scf_detailed import build_detailed_household_input


@pytest.fixture
def detailed_scf_row():
    return {
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
        "x5819": 1,
        "x5821": 500_000,
        "x5825": 1,
    }


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


def test_detailed_inputs_keep_people_and_social_security_separate(detailed_scf_row):
    household = build_detailed_household_input(detailed_scf_row)

    assert household.respondent.age == 64
    assert household.spouse is not None
    assert household.spouse.age == 40
    assert household.respondent.annual_wage == pytest.approx(100_000)
    assert household.spouse.annual_wage == pytest.approx(48_000)
    assert household.respondent.annual_social_security == pytest.approx(24_000)
    assert household.spouse.annual_social_security == 0


@pytest.mark.parametrize("response", [1, 1.0])
def test_affirmative_inheritance_expectation_preserves_positive_amount(
    detailed_scf_row, response
):
    detailed_scf_row["x5819"] = response

    household = build_detailed_household_input(detailed_scf_row)

    assert household.expected_inheritance_amount == pytest.approx(500_000)


@pytest.mark.parametrize("response", [None, 0, 1.5, 2, 3, 5])
def test_nonaffirmative_inheritance_response_creates_no_future_claim(
    detailed_scf_row, response
):
    detailed_scf_row["x5819"] = response

    household = build_detailed_household_input(detailed_scf_row)

    assert household.expected_inheritance_amount == 0


def test_boolean_inheritance_expectation_code_creates_no_future_claim(detailed_scf_row):
    detailed_scf_row["x5819"] = True

    household = build_detailed_household_input(detailed_scf_row)

    assert household.expected_inheritance_amount == 0


def test_numpy_boolean_inheritance_expectation_code_creates_no_future_claim(
    detailed_scf_row,
):
    detailed_scf_row["x5819"] = np.bool_(True)

    household = build_detailed_household_input(detailed_scf_row)

    assert household.expected_inheritance_amount == 0


@pytest.mark.parametrize(
    "amount",
    [0, -1, None, float("nan"), float("inf"), float("-inf")],
)
def test_affirmative_inheritance_response_rejects_nonpositive_or_nonfinite_amounts(
    detailed_scf_row, amount
):
    detailed_scf_row["x5821"] = amount

    household = build_detailed_household_input(detailed_scf_row)

    assert household.expected_inheritance_amount == 0


def test_boolean_inheritance_amount_creates_no_future_claim(detailed_scf_row):
    detailed_scf_row["x5821"] = True

    household = build_detailed_household_input(detailed_scf_row)

    assert household.expected_inheritance_amount == 0


def test_numpy_boolean_inheritance_amount_creates_no_future_claim(detailed_scf_row):
    detailed_scf_row["x5821"] = np.bool_(True)

    household = build_detailed_household_input(detailed_scf_row)

    assert household.expected_inheritance_amount == 0


@pytest.mark.parametrize(
    "estate_response, expected",
    [(1, True), (None, False), (0, False), (1.5, False), (2, False), (5, False)],
)
def test_only_direct_sizable_estate_intent_sets_donor_flag(
    detailed_scf_row, estate_response, expected
):
    detailed_scf_row["x5825"] = estate_response

    household = build_detailed_household_input(detailed_scf_row)

    assert household.expects_sizable_estate is expected


def test_boolean_sizable_estate_code_creates_no_donor_intent(detailed_scf_row):
    detailed_scf_row["x5825"] = True

    household = build_detailed_household_input(detailed_scf_row)

    assert household.expects_sizable_estate is False


def test_numpy_boolean_sizable_estate_code_creates_no_donor_intent(detailed_scf_row):
    detailed_scf_row["x5825"] = np.bool_(True)

    household = build_detailed_household_input(detailed_scf_row)

    assert household.expects_sizable_estate is False


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
