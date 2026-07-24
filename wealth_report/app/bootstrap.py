"""Shared page bootstrap: sidebar assumptions, cached data, conservation check."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from wealth_report.app import cache as report_cache
from wealth_report.app.ui import render_assumption_sidebar
from wealth_report.report.distribution import validate_inheritance_reallocation_conservation


def load_page_report() -> tuple[dict[str, float | int], pd.DataFrame]:
    """Render assumption controls and return (assumptions, valued household table)."""
    if st.session_state.get("assumptions_rendered_by_entrypoint", False):
        assumptions = dict(st.session_state["model_assumptions"])
    else:
        # Direct page execution (including AppTest) must redraw widgets every rerun.
        assumptions = dict(render_assumption_sidebar())
        st.session_state["model_assumptions"] = assumptions
    # Look up via module attribute so tests can monkeypatch cache.load_*.
    data = report_cache.load_comprehensive_report_data(**assumptions)
    validate_inheritance_reallocation_conservation(data)
    return assumptions, data
