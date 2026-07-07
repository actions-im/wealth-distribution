from __future__ import annotations

import pandas as pd
import streamlit as st

from src.app_data import load_report_household_data
from src.charts import stacked_marketable_vs_human
from src.provenance import ASSUMPTION_SOURCE, build_number_source_table, chart_source_caption
from src.real_data import aggregate_real_by_age
from src.ui import methodology_expander, render_assumption_sidebar


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
            "Source": f"{ASSUMPTION_SOURCE}; report-defined sensitivity scenario",
        },
        {
            "Scenario": "Base",
            "Discount rate": "3.5%",
            "Wage growth": "1.5%",
            "Retirement age": 67,
            "Source": f"{ASSUMPTION_SOURCE}; report-defined sensitivity scenario",
        },
        {
            "Scenario": "Optimistic",
            "Discount rate": "2.5%",
            "Wage growth": "2.0%",
            "Retirement age": 70,
            "Source": f"{ASSUMPTION_SOURCE}; report-defined sensitivity scenario",
        },
    ]
)

st.table(scenarios.set_index("Scenario"))
st.plotly_chart(
    stacked_marketable_vs_human(age_data, "age_group", "Current slider assumptions")
)
st.caption(chart_source_caption())

with st.expander("Sources for every number on this page"):
    st.table(build_number_source_table(assumptions).set_index("Number category"))

methodology_expander()
