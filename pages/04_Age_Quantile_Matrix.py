from __future__ import annotations

import streamlit as st

from src.charts import matrix_heatmap
from src.sample_data import build_sample_household_data
from src.ui import methodology_expander, render_assumption_sidebar


st.set_page_config(page_title="Age Quantile Matrix", layout="wide")

assumptions = render_assumption_sidebar()
data = build_sample_household_data(
    assumptions["discount_rate"],
    assumptions["wage_growth"],
    assumptions["retirement_age"],
    assumptions["employment_probability"],
    assumptions["tax_rate"],
    assumptions["liquidity_weight"],
)

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

st.plotly_chart(matrix_heatmap(data, metric), use_container_width=True)
methodology_expander()

