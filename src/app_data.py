from __future__ import annotations

import pandas as pd
import streamlit as st

from src.real_data import load_real_wealth_household_data
from src.config import ModelAssumptions
from src.real_data import load_comprehensive_household_data


@st.cache_data(show_spinner="Loading Federal Reserve SCF 2022 data...")
def load_report_household_data(
    discount_rate: float,
    wage_growth: float,
    retirement_age: int,
    employment_probability: float,
    tax_rate: float,
    liquidity_weight: float,
) -> pd.DataFrame:
    return load_real_wealth_household_data(
        discount_rate=discount_rate,
        wage_growth=wage_growth,
        retirement_age=retirement_age,
        employment_probability=employment_probability,
        tax_rate=tax_rate,
        liquidity_weight=liquidity_weight,
    )


@st.cache_data(
    show_spinner="Valuing Federal Reserve SCF household resources...",
    max_entries=8,
)
def load_comprehensive_report_data(
    discount_rate: float,
    wage_growth: float,
    retirement_age: int,
    employment_probability: float,
    reentry_probability: float,
    tax_rate: float,
    payable_benefit_factor: float,
    income_security_floor_monthly: float,
) -> pd.DataFrame:
    assumptions = ModelAssumptions(
        discount_rate=discount_rate,
        wage_growth=wage_growth,
        retirement_age=retirement_age,
        employment_probability=employment_probability,
        reentry_probability=reentry_probability,
        tax_rate=tax_rate,
        payable_benefit_factor=payable_benefit_factor,
        income_security_floor_monthly=income_security_floor_monthly,
    )
    return load_comprehensive_household_data(assumptions)
