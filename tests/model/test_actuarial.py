import pytest

from wealth_report.model.actuarial import conditional_survival, present_value_stream


def test_future_payment_starts_one_period_ahead():
    assert present_value_stream([100], discount_rate=0.05) == pytest.approx(100 / 1.05)


def test_survival_curve_is_conditional_on_current_age():
    curve = conditional_survival({40: 90_000, 41: 89_000, 42: 88_000}, current_age=40)

    assert curve == pytest.approx([1.0, 89 / 90, 88 / 90])


def test_present_value_applies_period_specific_survival():
    assert present_value_stream([100, 100], discount_rate=0, survival=[1, 0.5]) == 150


@pytest.mark.parametrize("rate", [-1, -1.5, float("nan")])
def test_present_value_rejects_invalid_discount_rates(rate):
    with pytest.raises(ValueError, match="discount_rate"):
        present_value_stream([100], discount_rate=rate)


def test_conditional_survival_requires_current_age_and_positive_lives():
    with pytest.raises(ValueError, match="current_age"):
        conditional_survival({41: 90_000}, current_age=40)
    with pytest.raises(ValueError, match="positive"):
        conditional_survival({40: 0, 41: 0}, current_age=40)
