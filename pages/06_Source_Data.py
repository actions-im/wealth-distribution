from __future__ import annotations

import streamlit as st

from src.app_data import load_report_household_data
from src.data_sources import source_table
from src.provenance import build_number_source_table
from src.real_data import SCF_2022_DATA_NOTE
from src.ui import render_assumption_sidebar


st.set_page_config(page_title="Source Data", layout="wide")

assumptions = render_assumption_sidebar()
data = load_report_household_data(
    assumptions["discount_rate"],
    assumptions["wage_growth"],
    assumptions["retirement_age"],
    assumptions["employment_probability"],
    assumptions["tax_rate"],
    assumptions["liquidity_weight"],
)

st.title("Source Data")
st.write(
    "The comprehensive-resource charts use the Federal Reserve 2022 SCF summary and full public files, "
    "SSA mortality and 2022 program parameters, and Federal Reserve Financial Accounts pension benchmarks. "
    "The Methodology page maps every headline number to its fields, formulas, and registered sources."
)
st.page_link(
    "pages/07_Methodology.py",
    label="Open the methodology and number audit",
    icon=":material/menu_book:",
)
st.info(SCF_2022_DATA_NOTE)

st.subheader("Number Source Audit")
st.write(
    "Every displayed number in the report should fall into one of these categories: Fed SCF input data, "
    "a calculation from Fed SCF fields, a visible sidebar assumption, or a report-defined grouping."
)
st.table(build_number_source_table(assumptions).set_index("Number category"))

sources = source_table()
st.subheader("Official Sources and Methodology Links")
st.dataframe(
    sources,
    hide_index=True,
    column_config={"URL": st.column_config.LinkColumn("URL")},
)

st.download_button(
    "Download current processed SCF CSV",
    data=data.to_csv(index=False),
    file_name="real_wealth_scf_2022_processed.csv",
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
