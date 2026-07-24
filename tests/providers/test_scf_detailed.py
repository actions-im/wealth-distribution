import numpy as np
import pandas as pd
import pytest

from wealth_report.providers.scf.summary import normalize_scf_rows
from wealth_report.providers.scf.detailed import (
    DETAILED_COLUMNS,
    build_detailed_household_input,
)


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


def test_hourly_wage_uses_reported_hours_and_weeks(detailed_scf_row):
    detailed_scf_row.update(
        {
            "x4112": 25,
            "x4113": 18,
            "x4110": 40,
            "x4111": 50,
        }
    )

    household = build_detailed_household_input(detailed_scf_row)

    assert household.respondent.annual_wage == pytest.approx(50_000)


def test_twice_monthly_wage_is_annualized(detailed_scf_row):
    detailed_scf_row.update({"x4112": 2_000, "x4113": 31})

    household = build_detailed_household_input(detailed_scf_row)

    assert household.respondent.annual_wage == pytest.approx(48_000)


def test_weekly_wage_uses_reported_weeks_worked(detailed_scf_row):
    detailed_scf_row.update({"x4112": 1_000, "x4113": 2, "x4111": 40})

    household = build_detailed_household_input(detailed_scf_row)

    assert household.respondent.annual_wage == pytest.approx(40_000)


def test_spouse_biweekly_wage_uses_reported_weeks_worked(detailed_scf_row):
    detailed_scf_row.update({"x4712": 2_000, "x4713": 3, "x4711": 40})

    household = build_detailed_household_input(detailed_scf_row)

    assert household.spouse is not None
    assert household.spouse.annual_wage == pytest.approx(40_000)


def test_second_job_wage_is_added_to_main_job_wage(detailed_scf_row):
    detailed_scf_row.update(
        {
            "x4507": 10,
            "x4508": 50,
            "x4509": 20,
            "x4510": 18,
        }
    )

    household = build_detailed_household_input(detailed_scf_row)

    assert household.respondent.annual_wage == pytest.approx(110_000)


def test_nonworker_respondent_uses_annualized_former_job_history(detailed_scf_row):
    detailed_scf_row.update(
        {
            "x4112": 0,
            "x4113": 0,
            "x4613": 5_000,
            "x4614": 4,
            "x4602": 12,
            "x4616": 5,
        }
    )

    household = build_detailed_household_input(detailed_scf_row)

    assert household.respondent.annual_wage == 0
    assert household.respondent.historical_annual_wage == pytest.approx(60_000)
    assert household.respondent.career_years == 17


def test_nonworker_spouse_uses_annualized_former_job_history(detailed_scf_row):
    detailed_scf_row.update(
        {
            "x4712": 0,
            "x4713": 0,
            "x5205": 52_000,
            "x5206": 6,
            "x5202": 8,
            "x5216": 3,
        }
    )

    household = build_detailed_household_input(detailed_scf_row)

    assert household.spouse is not None
    assert household.spouse.annual_wage == 0
    assert household.spouse.historical_annual_wage == pytest.approx(52_000)
    assert household.spouse.career_years == 11


def test_former_job_pay_without_reported_tenure_is_not_used(detailed_scf_row):
    detailed_scf_row.update(
        {"x4112": 0, "x4113": 0, "x4613": 5_000, "x4614": 4}
    )

    household = build_detailed_household_input(detailed_scf_row)

    assert household.respondent.historical_annual_wage is None
    assert household.respondent.career_years is None


def test_nonworker_history_combines_reported_full_and_part_time_years(
    detailed_scf_row,
):
    detailed_scf_row.update(
        {
            "x4112": 0,
            "x4113": 0,
            "x4605": 50_000,
            "x4606": 6,
            "x4602": 10,
            "x4616": 4,
        }
    )

    household = build_detailed_household_input(detailed_scf_row)

    assert household.respondent.historical_annual_wage == pytest.approx(50_000)
    assert household.respondent.career_years == 14


def test_detailed_projection_includes_nonworker_history_branches():
    assert {
        "x4602",
        "x4605",
        "x4606",
        "x4613",
        "x4614",
        "x4616",
        "x5202",
        "x5205",
        "x5206",
        "x5213",
        "x5214",
        "x5216",
    } <= set(DETAILED_COLUMNS)


@pytest.mark.parametrize(
    ("code", "expected_type"),
    [
        (1, "retirement"),
        (2, "disability"),
        (3, "survivor_or_dependent"),
        (7, "ssi"),
    ],
)
def test_social_security_payment_type_is_retained(detailed_scf_row, code, expected_type):
    detailed_scf_row["x5304"] = code

    household = build_detailed_household_input(detailed_scf_row)

    assert household.respondent.social_security_benefit_type == expected_type


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


@pytest.mark.parametrize(
    ("cola_code", "expected"),
    [(1, True), (5, False), (0, None), (None, None)],
)
def test_current_db_benefit_retains_reported_cola_status(cola_code, expected):
    household = build_detailed_household_input(
        {
            "y1": 12341,
            "yy1": 1234,
            "x14": 70,
            "x8021": 1,
            "x6461": 5,
            "x5315": 1,
            "x5317": 5,
            "x5318": 2_000,
            "x5319": 4,
            "x5320": cola_code,
        }
    )

    assert len(household.db_pensions) == 1
    assert household.db_pensions[0].has_cost_of_living_adjustment is expected
