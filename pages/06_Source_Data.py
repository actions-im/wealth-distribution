from __future__ import annotations

import streamlit as st

from src.data_sources import source_table
from src.sample_data import build_sample_household_data
from src.ui import render_assumption_sidebar


st.set_page_config(page_title="Source Data", layout="wide")

assumptions = render_assumption_sidebar()
data = build_sample_household_data(
    assumptions["discount_rate"],
    assumptions["wage_growth"],
    assumptions["retirement_age"],
    assumptions["employment_probability"],
    assumptions["tax_rate"],
    assumptions["liquidity_weight"],
)

st.title("Source Data")
st.write(
    "These are the official sources the report is designed to use. The current app ships with placeholder "
    "data so the interface and formulas are reviewable before the full SCF/DFA processing pipeline is run."
)

sources = source_table()
st.dataframe(
    sources,
    use_container_width=True,
    hide_index=True,
    column_config={"URL": st.column_config.LinkColumn("URL")},
)

st.download_button(
    "Download current processed sample CSV",
    data=data.to_csv(index=False),
    file_name="real_wealth_sample_processed.csv",
    mime="text/csv",
)

with st.expander("Public limitations to keep with the report"):
    st.markdown(
        """
1. Traditional net worth and human capital are different kinds of wealth.
2. Marketable assets are liquid, transferable, borrowable, and inheritable.
3. Human capital is personal, risky, nontransferable, and partly taxable.
4. Human-capital estimates depend on employment, retirement age, wage growth, taxes, health, and discount rates.
5. The report compares valuation frameworks; it does not deny measured asset inequality.
        """
    )

