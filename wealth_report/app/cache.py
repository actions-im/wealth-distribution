from __future__ import annotations

import pandas as pd
import streamlit as st

from wealth_report.model.assumptions import ModelAssumptions
from wealth_report.report.pipeline import (
    load_comprehensive_household_data,
    load_scf_household_bundle,
)


@st.cache_resource(show_spinner="Loading Federal Reserve SCF microdata...")
def _cached_scf_bundle(raw_dir: str = "data/raw"):
    """Keep joined SCF inputs warm across Streamlit reruns and assumption changes."""
    return load_scf_household_bundle(raw_dir)


@st.cache_data(
    show_spinner="Valuing Federal Reserve SCF household resources...",
    max_entries=8,
)
def load_comprehensive_report_data(
    discount_rate: float,
    wage_growth: float,
    inflation_rate: float,
    retirement_age: int,
    employment_probability: float,
    reentry_probability: float,
    tax_rate: float,
    payable_benefit_factor: float,
    income_security_floor_monthly: float,
    inheritance_horizon_years: int,
) -> pd.DataFrame:
    """Cache key is the full assumption vector (call with ``**assumptions``).

    SCF microdata is loaded once via ``cache_resource``; only valuation is redone
    when assumptions change.
    """
    assumptions = ModelAssumptions(
        discount_rate=discount_rate,
        wage_growth=wage_growth,
        inflation_rate=inflation_rate,
        retirement_age=retirement_age,
        employment_probability=employment_probability,
        reentry_probability=reentry_probability,
        tax_rate=tax_rate,
        payable_benefit_factor=payable_benefit_factor,
        income_security_floor_monthly=income_security_floor_monthly,
        inheritance_horizon_years=inheritance_horizon_years,
    )
    # Touch the resource cache so SCF load is paid once per app session.
    _cached_scf_bundle("data/raw")
    return load_comprehensive_household_data(assumptions)
