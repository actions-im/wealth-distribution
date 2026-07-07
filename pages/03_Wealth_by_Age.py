from __future__ import annotations

import streamlit as st

from src.charts import money_bar, stacked_marketable_vs_human
from src.sample_data import aggregate_by_age, build_sample_household_data
from src.ui import methodology_expander, render_assumption_sidebar


st.set_page_config(page_title="Wealth by Age", layout="wide")

assumptions = render_assumption_sidebar()
data = build_sample_household_data(
    assumptions["discount_rate"],
    assumptions["wage_growth"],
    assumptions["retirement_age"],
    assumptions["employment_probability"],
    assumptions["tax_rate"],
    assumptions["liquidity_weight"],
)
age_data = aggregate_by_age(data)

st.title("Wealth by Age")
st.write(
    "Younger households tend to have less accumulated marketable wealth but more remaining labor-earnings "
    "capacity. Older households tend to have more accumulated assets and less remaining labor income."
)

col1, col2, col3 = st.columns(3)
with col1:
    st.plotly_chart(money_bar(age_data, "age_group", "traditional_net_worth", "Marketable net worth"), use_container_width=True)
with col2:
    st.plotly_chart(money_bar(age_data, "age_group", "human_capital", "Human capital"), use_container_width=True)
with col3:
    st.plotly_chart(money_bar(age_data, "age_group", "combined_real_wealth", "Combined real wealth"), use_container_width=True)

st.plotly_chart(
    stacked_marketable_vs_human(age_data, "age_group", "Marketable wealth vs human capital by age"),
    use_container_width=True,
)

methodology_expander()

