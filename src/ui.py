from __future__ import annotations

import streamlit as st

from src.config import DEFAULT_ASSUMPTIONS, SOURCE_NOTE
from src.provenance import assumption_source_caption


def render_assumption_sidebar(include_wealth_definition: bool = False) -> dict[str, float | int]:
    st.sidebar.header("Assumptions")
    st.sidebar.caption(
        "Data: Federal Reserve 2022 SCF summary and full public files, SSA mortality and 2022 program "
        "parameters, and Federal Reserve Financial Accounts pension benchmarks."
    )
    st.sidebar.caption(assumption_source_caption())
    if include_wealth_definition:
        wealth_definition = st.sidebar.selectbox(
            "Wealth definition",
            [
                "Traditional net worth only",
                "Human capital only",
                "Traditional + human capital",
                "Liquidity-adjusted labor-resource view",
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
    reentry_probability = st.sidebar.slider(
        "Non-earner re-entry probability",
        0.0,
        1.0,
        DEFAULT_ASSUMPTIONS["reentry_probability"],
        step=0.05,
    )
    payable_benefit_factor = st.sidebar.slider(
        "Social Security payable factor",
        0.0,
        1.0,
        DEFAULT_ASSUMPTIONS["payable_benefit_factor"],
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
        "reentry_probability": reentry_probability,
        "payable_benefit_factor": payable_benefit_factor,
    }


def selected_metric(wealth_definition: str) -> str:
    return {
        "Traditional net worth only": "traditional_net_worth",
        "Human capital only": "human_capital",
        "Traditional + human capital": "combined_real_wealth",
        "Liquidity-adjusted labor-resource view": "liquidity_adjusted_real_wealth",
    }[wealth_definition]


def methodology_expander() -> None:
    with st.expander("Methodology and limits"):
        st.write(
            "Conventional net worth and modeled comprehensive resources answer different questions. "
            "The former is an asset-minus-liability balance sheet; the latter adds nontransferable expected "
            "labor resources and modeled retirement claims. Neither should be presented as the uniquely "
            "correct definition of wealth."
        )
        st.write(
            "Defensive accrued resources apply zero real wage growth, a policy-payability factor to Social "
            "Security, subtract modeled future employee OASDI contributions, and value accrued DB benefits. "
            "Continuation resources assume current earnings and pension accrual continue to retirement."
        )
        st.markdown(
            "Federal Reserve research has used related human-wealth or comprehensive-wealth concepts, "
            "including present-value treatment of future income. The interactive estimates use SCF 2022 "
            "net worth, wage income, age, and household weights. See the Source Data page for links."
        )
