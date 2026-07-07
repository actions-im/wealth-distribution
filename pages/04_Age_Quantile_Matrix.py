from __future__ import annotations

import streamlit as st

from src.app_data import load_report_household_data
from src.charts import matrix_heatmap
from src.real_data import aggregate_real_age_quantile_matrix
from src.ui import methodology_expander, render_assumption_sidebar


st.set_page_config(page_title="Age Quantile Matrix", layout="wide")

assumptions = render_assumption_sidebar()
data = load_report_household_data(
    assumptions["discount_rate"],
    assumptions["wage_growth"],
    assumptions["retirement_age"],
    assumptions["employment_probability"],
    assumptions["tax_rate"],
    assumptions["liquidity_weight"],
)
matrix_data = aggregate_real_age_quantile_matrix(data)

st.title("Age x Quantile Matrix")
metric = st.selectbox(
    "Metric",
    [
        "traditional_net_worth",
        "human_capital",
        "combined_real_wealth",
        "liquidity_adjusted_real_wealth",
    ],
)

st.plotly_chart(matrix_heatmap(matrix_data, metric))
methodology_expander()
