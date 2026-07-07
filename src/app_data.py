from __future__ import annotations

import pandas as pd
import streamlit as st

from src.real_data import load_real_wealth_household_data


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
