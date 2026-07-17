import pytest

from wealth_report.model.income_security import (
    annual_income_security_benchmark,
    income_security_floor_stream,
    value_income_security_floor,
)


def test_income_security_benchmark_scales_for_two_adult_family():
    assert annual_income_security_benchmark(monthly_benchmark=622, adult_count=1) == 7_464
    assert annual_income_security_benchmark(monthly_benchmark=622, adult_count=2) == 11_196


def test_income_security_floor_only_tops_up_income_below_benchmark():
    floor = income_security_floor_stream(
        other_income=[1_000, 8_000],
        monthly_benchmark=622,
        adult_count=1,
    )

    assert floor == pytest.approx([6_464, 0])


def test_income_security_floor_value_is_survival_weighted_and_discounted():
    value = value_income_security_floor(
        other_income=[0, 0],
        monthly_benchmark=622,
        adult_count=1,
        survival=[1.0, 0.5],
        discount_rate=0.035,
    )

    assert value == pytest.approx(7_464 / 1.035 + (7_464 * 0.5) / 1.035**2)
