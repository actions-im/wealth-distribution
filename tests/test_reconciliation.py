import pytest

from src.reconciliation import load_official_db_total, reconcile


def test_reconciliation_reports_difference_without_rescaling():
    result = reconcile(micro_total=90, official_total=100)

    assert result.ratio == pytest.approx(0.9)
    assert result.adjusted_micro_total == 90
    assert result.difference == -10


def test_bundled_2022_db_total_uses_billions_as_documented():
    result = load_official_db_total(year=2022)

    assert result.series_code == "FL594190045"
    assert result.value_dollars == pytest.approx(15_658.3e9)
