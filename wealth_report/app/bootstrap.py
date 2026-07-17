"""Shared page bootstrap: sidebar assumptions, cached data, conservation check."""

from __future__ import annotations

import pandas as pd

from wealth_report.app import cache as report_cache
from wealth_report.app.ui import render_assumption_sidebar
from wealth_report.report.distribution import validate_inheritance_reallocation_conservation


def load_page_report() -> tuple[dict[str, float | int], pd.DataFrame]:
    """Render assumption controls and return (assumptions, valued household table)."""
    assumptions = render_assumption_sidebar()
    # Look up via module attribute so tests can monkeypatch cache.load_*.
    data = report_cache.load_comprehensive_report_data(**assumptions)
    validate_inheritance_reallocation_conservation(data)
    return assumptions, data
