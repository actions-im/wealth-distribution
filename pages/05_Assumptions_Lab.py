from __future__ import annotations

import pandas as pd
import streamlit as st

from src.app_data import load_report_household_data
from src.charts import stacked_marketable_vs_human
from src.real_data import aggregate_real_by_age
from src.ui import methodology_expander, render_assumption_sidebar
from src.validation import national_human_capital_sanity_check


st.set_page_config(page_title="Assumptions Lab", layout="wide")

assumptions = render_assumption_sidebar()
data = load_report_household_data(
    assumptions["discount_rate"],
    assumptions["wage_growth"],
    assumptions["retirement_age"],
    assumptions["employment_probability"],
    assumptions["tax_rate"],
    assumptions["liquidity_weight"],
)
age_data = aggregate_real_by_age(data)

st.title("Assumptions Lab")
st.write("Use the sidebar sliders to stress-test the present-value model.")

scenarios = pd.DataFrame(
    [
        {
            "Scenario": "Conservative",
            "Discount rate": "4.5%",
            "Wage growth": "0.5%",
            "Retirement age": 65,
            "National human-capital estimate": national_human_capital_sanity_check(
                discount_rate=0.045, wage_growth=0.005, horizon_years=35
            ),
        },
        {
            "Scenario": "Base",
            "Discount rate": "3.5%",
            "Wage growth": "1.5%",
            "Retirement age": 67,
            "National human-capital estimate": national_human_capital_sanity_check(
                discount_rate=0.035, wage_growth=0.015, horizon_years=40
            ),
        },
        {
            "Scenario": "Optimistic",
            "Discount rate": "2.5%",
            "Wage growth": "2.0%",
            "Retirement age": 70,
            "National human-capital estimate": national_human_capital_sanity_check(
                discount_rate=0.025, wage_growth=0.02, horizon_years=45
            ),
        },
    ]
)
scenarios["National human-capital estimate"] = scenarios["National human-capital estimate"].map(lambda x: f"${x / 1e12:,.0f}T")

st.dataframe(scenarios, hide_index=True)
st.plotly_chart(
    stacked_marketable_vs_human(age_data, "age_group", "Current slider assumptions")
)

methodology_expander()
