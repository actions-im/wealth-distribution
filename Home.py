from __future__ import annotations

import streamlit as st

from src.charts import single_distribution_share_bar
from src.formatting import percent
from src.reporting import build_detail_wealth_table, build_executive_share_table
from src.sample_data import (
    PLACEHOLDER_HOUSEHOLD_COUNT,
    aggregate_country_distribution_by_quantile,
    build_sample_household_data,
)
from src.ui import methodology_expander, render_assumption_sidebar


st.set_page_config(page_title="Real Wealth Distribution", layout="wide", initial_sidebar_state="collapsed")

assumptions = render_assumption_sidebar()
data = build_sample_household_data(
    discount_rate=assumptions["discount_rate"],
    wage_growth=assumptions["wage_growth"],
    retirement_age=assumptions["retirement_age"],
    employment_probability=assumptions["employment_probability"],
    tax_rate=assumptions["tax_rate"],
    liquidity_weight=assumptions["liquidity_weight"],
)
country_distribution = aggregate_country_distribution_by_quantile(data)

st.title("The Standard Wealth Debate Compares Mismatched Ledgers")
st.caption("Stock wealth already prices future cash flows. Labor wealth is usually counted as zero.")

st.markdown(
    "The usual wealth inequality argument compares **future money embedded in asset prices** with "
    "**only present balance-sheet wealth** for everyone else. A share of stock wealth is valuable because "
    "markets capitalize expected future corporate cash flows. Future wages are also economically valuable, "
    "but standard wealth statistics implicitly assign them a value of **$0**. This report applies the same "
    "present-value logic to future earnings so the comparison is closer to apples to apples."
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

st.subheader("The Apples-to-Apples Adjustment")
left, right = st.columns(2)
with left:
    st.plotly_chart(
        single_distribution_share_bar(
            country_distribution,
            "traditional_net_worth_share",
            "Standard ledger: future labor earnings = $0",
            "#8f1d14",
        ),
        use_container_width=True,
    )
with right:
    st.plotly_chart(
        single_distribution_share_bar(
            country_distribution,
            "combined_real_wealth_share",
            "Adjusted ledger: future labor earnings discounted to today",
            "#0f766e",
        ),
        use_container_width=True,
    )

st.dataframe(
    build_executive_share_table(country_distribution),
    use_container_width=True,
    hide_index=True,
)

st.markdown(
    "The adjusted view does **not** say human capital is liquid, tradable, or inheritable like stocks. "
    "It says that if one side of the comparison capitalizes future cash flows, the other side should not "
    "be forced into a present-only ledger."
)

with st.expander("Data note and detailed totals"):
    st.write(
        f"This prototype uses a generated sample with {PLACEHOLDER_HOUSEHOLD_COUNT:,} households. "
        "It is calibrated to demonstrate the valuation methodology, not to make an empirical claim. "
        "Dollar totals are shown in trillions. Replace the sample with processed Fed SCF/DFA data before "
        "publishing empirical claims."
    )
    st.dataframe(
        build_detail_wealth_table(country_distribution),
        use_container_width=True,
        hide_index=True,
    )

methodology_expander()
