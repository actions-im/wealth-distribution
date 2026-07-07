from __future__ import annotations

import streamlit as st

from src.config import DEFAULT_ASSUMPTIONS, SOURCE_NOTE


def render_assumption_sidebar(include_wealth_definition: bool = False) -> dict[str, float | int]:
    st.sidebar.header("Assumptions")
    st.sidebar.caption(
        "Prototype data: charts currently use a generated sample calibrated to demonstrate the methodology. "
        "Fed DFA/SCF source loaders are present, but official data is not wired into the interactive views yet."
    )
    if include_wealth_definition:
        wealth_definition = st.sidebar.selectbox(
            "Wealth definition",
            [
                "Traditional net worth only",
                "Human capital only",
                "Traditional + human capital",
                "Liquidity-adjusted real wealth",
            ],
        )
    else:
        wealth_definition = "Traditional + human capital"
    discount_rate = st.sidebar.slider(
        "Discount rate",
        min_value=0.0,
        max_value=0.08,
        value=DEFAULT_ASSUMPTIONS["discount_rate"],
        step=0.0025,
        format="%.3f",
    )
    wage_growth = st.sidebar.slider(
        "Real wage growth",
        min_value=-0.01,
        max_value=0.04,
        value=DEFAULT_ASSUMPTIONS["wage_growth"],
        step=0.0025,
        format="%.3f",
    )
    retirement_age = st.sidebar.slider("Retirement age", 55, 75, DEFAULT_ASSUMPTIONS["retirement_age"])
    employment_probability = st.sidebar.slider(
        "Employment probability",
        min_value=0.5,
        max_value=1.0,
        value=DEFAULT_ASSUMPTIONS["employment_probability"],
        step=0.01,
    )
    tax_rate = st.sidebar.slider("Flat tax haircut", 0.0, 0.5, DEFAULT_ASSUMPTIONS["tax_rate"], step=0.01)
    liquidity_weight = st.sidebar.slider(
        "Human-capital liquidity weight",
        0.0,
        1.0,
        DEFAULT_ASSUMPTIONS["liquidity_weight"],
        step=0.05,
    )
    st.sidebar.caption(SOURCE_NOTE)
    return {
        "wealth_definition": wealth_definition,
        "discount_rate": discount_rate,
        "wage_growth": wage_growth,
        "retirement_age": retirement_age,
        "employment_probability": employment_probability,
        "tax_rate": tax_rate,
        "liquidity_weight": liquidity_weight,
    }


def selected_metric(wealth_definition: str) -> str:
    return {
        "Traditional net worth only": "traditional_net_worth",
        "Human capital only": "human_capital",
        "Traditional + human capital": "combined_real_wealth",
        "Liquidity-adjusted real wealth": "liquidity_adjusted_real_wealth",
    }[wealth_definition]


def methodology_expander() -> None:
    with st.expander("Methodology and limits"):
        st.write(
            "The central issue is a metric mismatch. Marketable assets such as equities and business "
            "interests are priced using expectations about future cash flows. Standard wealth statistics "
            "then compare those capitalized asset values with a household ledger where future labor earnings "
            "are implicitly valued at zero."
        )
        st.write(
            "This report adds the present value of expected future labor income as nonmarketable human "
            "capital. Human capital is not liquid, transferable, borrowable, or inheritable in the way "
            "financial assets are. The point is to compare valuation frameworks more consistently, not to "
            "deny measured asset inequality in standard Federal Reserve wealth statistics."
        )
        st.markdown(
            "Federal Reserve research has used related human-wealth or comprehensive-wealth concepts, "
            "including present-value treatment of future income. See the Source Data page for links."
        )
