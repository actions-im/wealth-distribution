import math

import pandas as pd
import pytest

from src.inheritance import (
    allocate_inheritance_reallocation,
    discounted_inheritance_claim,
)


LIFE_TABLE = {
    "female": {
        40: 10_000,
        41: 9_900,
        42: 9_780,
        43: 9_640,
        44: 9_480,
        45: 9_300,
        46: 9_000,
        47: 8_650,
        48: 8_250,
        49: 7_800,
        50: 7_300,
    },
    "male": {
        40: 10_000,
        41: 9_850,
        42: 9_650,
        43: 9_400,
        44: 9_100,
        45: 8_750,
        46: 8_350,
        47: 7_900,
        48: 7_400,
        49: 6_850,
        50: 6_250,
    },
}


def _households(rows: list[dict[str, object]]) -> pd.DataFrame:
    return pd.DataFrame(rows).reindex(
        columns=[
            "household_weight",
            "net_worth",
            "age",
            "sex",
            "expected_inheritance_amount",
            "expects_sizable_estate",
        ]
    )


def _allocate(rows: list[dict[str, object]], *, horizon_years: int = 5):
    return allocate_inheritance_reallocation(
        _households(rows),
        life_table=LIFE_TABLE,
        horizon_years=horizon_years,
        discount_rate=0.10,
    )


def test_discounted_inheritance_claim_uses_the_horizon_and_discount_rate():
    assert discounted_inheritance_claim(1_000, years=10, discount_rate=0.10) == pytest.approx(
        1_000 / 1.1**10
    )


def test_weighted_credits_equal_weighted_reserves_when_donor_capacity_exists():
    result, diagnostics = _allocate(
        [
            {
                "household_weight": 2,
                "net_worth": 0,
                "age": 40,
                "sex": "female",
                "expected_inheritance_amount": 100,
                "expects_sizable_estate": False,
            },
            {
                "household_weight": 3,
                "net_worth": 1_000,
                "age": 45,
                "sex": "male",
                "expected_inheritance_amount": 0,
                "expects_sizable_estate": True,
            },
        ]
    )

    weighted_credit = (result["household_weight"] * result["inheritance_credit"]).sum()
    weighted_reserve = (result["household_weight"] * result["estate_donor_reserve"]).sum()

    assert weighted_credit == pytest.approx(weighted_reserve)
    assert weighted_credit == pytest.approx(diagnostics.reallocated_total)
    assert diagnostics.unallocated_claim_total == pytest.approx(0)


def test_higher_mortality_donor_receives_a_larger_reserve():
    result, _ = _allocate(
        [
            {
                "household_weight": 1,
                "net_worth": 0,
                "age": 40,
                "sex": "female",
                "expected_inheritance_amount": 100_000,
                "expects_sizable_estate": False,
            },
            {
                "household_weight": 1,
                "net_worth": 1_000_000,
                "age": 40,
                "sex": "female",
                "expected_inheritance_amount": 0,
                "expects_sizable_estate": True,
            },
            {
                "household_weight": 1,
                "net_worth": 1_000_000,
                "age": 45,
                "sex": "female",
                "expected_inheritance_amount": 0,
                "expects_sizable_estate": True,
            },
        ]
    )

    younger_reserve = result.loc[1, "estate_donor_reserve"]
    older_reserve = result.loc[2, "estate_donor_reserve"]

    assert older_reserve > younger_reserve


def test_reserve_never_exceeds_positive_net_worth_or_donor_capacity():
    result, _ = _allocate(
        [
            {
                "household_weight": 1,
                "net_worth": 0,
                "age": 40,
                "sex": "female",
                "expected_inheritance_amount": 10_000_000,
                "expects_sizable_estate": False,
            },
            {
                "household_weight": 1,
                "net_worth": 1_000,
                "age": 45,
                "sex": "male",
                "expected_inheritance_amount": 0,
                "expects_sizable_estate": True,
            },
        ]
    )

    donor = result.loc[1]
    assert donor["estate_donor_reserve"] <= donor["estate_donor_capacity"]
    assert donor["estate_donor_reserve"] <= donor["net_worth"]
    assert donor["estate_donor_capacity"] <= donor["net_worth"]


def test_zero_capacity_leaves_claim_unallocated_and_creates_no_credit_or_reserve():
    result, diagnostics = _allocate(
        [
            {
                "household_weight": 2,
                "net_worth": 0,
                "age": 40,
                "sex": "female",
                "expected_inheritance_amount": 1_000,
                "expects_sizable_estate": False,
            }
        ]
    )

    assert result["inheritance_credit"].sum() == 0
    assert result["estate_donor_reserve"].sum() == 0
    assert diagnostics.donor_capacity_total == 0
    assert diagnostics.reallocated_total == 0
    assert diagnostics.unallocated_claim_total == pytest.approx(
        diagnostics.discounted_claim_total
    )


def test_claims_larger_than_capacity_are_prorated_and_funding_ratio_is_below_one():
    result, diagnostics = _allocate(
        [
            {
                "household_weight": 1,
                "net_worth": 0,
                "age": 40,
                "sex": "female",
                "expected_inheritance_amount": 100_000,
                "expects_sizable_estate": False,
            },
            {
                "household_weight": 1,
                "net_worth": 1_000,
                "age": 45,
                "sex": "male",
                "expected_inheritance_amount": 0,
                "expects_sizable_estate": True,
            },
        ]
    )

    claim = result.loc[0, "inheritance_claim"]
    credit = result.loc[0, "inheritance_credit"]

    assert 0 < credit < claim
    assert diagnostics.reallocated_total == pytest.approx(diagnostics.donor_capacity_total)
    assert diagnostics.funding_ratio < 1


def test_invalid_claim_values_become_zero_while_invalid_donor_data_produce_no_capacity():
    result, _ = _allocate(
        [
            {
                "household_weight": 1,
                "net_worth": -1_000,
                "age": 45,
                "sex": "female",
                "expected_inheritance_amount": 100,
                "expects_sizable_estate": True,
            },
            {
                "household_weight": 1,
                "net_worth": 1_000,
                "age": 45,
                "sex": "female",
                "expected_inheritance_amount": -100,
                "expects_sizable_estate": False,
            },
            {
                "household_weight": 1,
                "net_worth": 1_000,
                "age": 45,
                "sex": "unknown",
                "expected_inheritance_amount": math.nan,
                "expects_sizable_estate": True,
            },
            {
                "household_weight": 1,
                "net_worth": 1_000,
                "age": 45,
                "sex": None,
                "expected_inheritance_amount": 0,
                "expects_sizable_estate": False,
            },
        ]
    )

    assert result["inheritance_claim"].tolist() == [
        pytest.approx(100 / 1.1**5),
        0,
        0,
        0,
    ]
    assert result["inheritance_credit"].sum() == 0
    assert result["estate_donor_capacity"].sum() == 0
    assert result["estate_donor_reserve"].sum() == 0


@pytest.mark.parametrize(
    ("household_weight", "match"),
    [(-1, "household_weight"), (math.nan, "household_weight"), (math.inf, "household_weight")],
)
def test_invalid_household_weight_is_rejected(household_weight, match):
    with pytest.raises(ValueError, match=match):
        _allocate(
            [
                {
                    "household_weight": household_weight,
                    "net_worth": 0,
                    "age": 40,
                    "sex": "female",
                    "expected_inheritance_amount": 0,
                    "expects_sizable_estate": False,
                }
            ]
        )


@pytest.mark.parametrize(
    ("horizon_years", "discount_rate", "match"),
    [
        (0, 0.10, "horizon_years"),
        (True, 0.10, "horizon_years"),
        (5, -1.0, "discount_rate"),
        (5, math.nan, "discount_rate"),
    ],
)
def test_invalid_horizon_or_discount_factor_is_rejected(horizon_years, discount_rate, match):
    with pytest.raises(ValueError, match=match):
        allocate_inheritance_reallocation(
            _households(
                [
                    {
                        "household_weight": 1,
                        "net_worth": 0,
                        "age": 40,
                        "sex": "female",
                        "expected_inheritance_amount": 0,
                        "expects_sizable_estate": False,
                    }
                ]
            ),
            life_table=LIFE_TABLE,
            horizon_years=horizon_years,
            discount_rate=discount_rate,
        )
