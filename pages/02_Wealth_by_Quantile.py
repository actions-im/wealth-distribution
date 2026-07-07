from __future__ import annotations

import streamlit as st

from src.app_data import load_report_household_data
from src.charts import current_vs_adjusted_share_bar
from src.formatting import percent
from src.provenance import build_number_source_table, chart_source_caption, table_source_note
from src.real_data import SCF_2022_DATA_NOTE, aggregate_real_country_distribution_by_quantile
from src.reporting import build_detail_wealth_table, build_executive_share_table
from src.ui import methodology_expander, render_assumption_sidebar


st.set_page_config(page_title="Wealth by Quantile", layout="wide", initial_sidebar_state="collapsed")

assumptions = render_assumption_sidebar()
data = load_report_household_data(
    assumptions["discount_rate"],
    assumptions["wage_growth"],
    assumptions["retirement_age"],
    assumptions["employment_probability"],
    assumptions["tax_rate"],
    assumptions["liquidity_weight"],
)
country_distribution = aggregate_real_country_distribution_by_quantile(data)

st.title("Total Country Wealth by Quantile")
st.write(
    "This page is about the total wealth of the country, not the average household inside each group. "
    "It separates the standard ledger from the apples-to-apples adjustment: stock and business wealth "
    "already reflect expected future cash flows, while future labor earnings are normally counted as zero. "
    "The household counts and dollar totals come from weighted 2022 SCF household microdata. "
    "Dollar totals are shown in trillions of dollars."
)
st.info(
    "Standard ledger = marketable assets minus debts, with future labor earnings implicitly valued at $0. "
    "Adjusted ledger = standard ledger plus discounted future wage income. "
    f"{SCF_2022_DATA_NOTE}"
)

top_one = country_distribution[
    country_distribution["wealth_quantile"].isin(["99-99.9%", "Top 0.1%"])
]
bottom_ninety = country_distribution[
    country_distribution["wealth_quantile"].isin(["Bottom 50%", "50-90%"])
]
col1, col2, col3, col4 = st.columns(4)
col1.metric("Top 1% marketable share", percent(top_one["traditional_net_worth_share"].sum()))
col2.metric("Top 1% adjusted share", percent(top_one["combined_real_wealth_share"].sum()))
col3.metric("Bottom 90% marketable share", percent(bottom_ninety["traditional_net_worth_share"].sum()))
col4.metric("Bottom 90% adjusted share", percent(bottom_ninety["combined_real_wealth_share"].sum()))
st.caption(chart_source_caption())

st.plotly_chart(
    current_vs_adjusted_share_bar(country_distribution, "Current vs adjusted total country wealth")
)
st.caption(chart_source_caption())

st.subheader("Share of Total Country Wealth")
st.table(
    build_executive_share_table(country_distribution).set_index("Quantile"),
)
st.caption(table_source_note())

st.subheader("Dollar Totals")
st.table(
    build_detail_wealth_table(country_distribution).set_index("Quantile"),
)
st.caption(table_source_note())

with st.expander("Sources for every number on this page"):
    st.table(build_number_source_table(assumptions).set_index("Number category"))

methodology_expander()
