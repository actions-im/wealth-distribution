from __future__ import annotations

import streamlit as st

from wealth_report.model.assumptions import DEFAULT_ASSUMPTIONS, SOURCE_NOTE
from wealth_report.report.provenance import assumption_source_caption


def render_assumption_sidebar() -> dict[str, float | int]:
    st.sidebar.header("Assumptions")
    st.sidebar.caption(
        "Data: Federal Reserve 2022 SCF summary and full public files, SSA mortality and 2022 program "
        "parameters, and Federal Reserve Financial Accounts pension benchmarks."
    )
    st.sidebar.caption(assumption_source_caption())
    discount_rate = st.sidebar.slider(
        "Discount rate",
        min_value=0.0,
        max_value=0.08,
        value=float(DEFAULT_ASSUMPTIONS["discount_rate"]),
        step=0.0025,
        format="%.3f",
    )
    wage_growth = st.sidebar.slider(
        "Real wage growth",
        min_value=-0.01,
        max_value=0.04,
        value=float(DEFAULT_ASSUMPTIONS["wage_growth"]),
        step=0.0025,
        format="%.3f",
    )
    retirement_age = st.sidebar.slider(
        "Retirement age",
        55,
        75,
        int(DEFAULT_ASSUMPTIONS["retirement_age"]),
    )
    employment_probability = st.sidebar.slider(
        "Employment probability",
        min_value=0.5,
        max_value=1.0,
        value=float(DEFAULT_ASSUMPTIONS["employment_probability"]),
        step=0.01,
    )
    tax_rate = st.sidebar.slider(
        "Flat tax haircut",
        0.0,
        0.5,
        float(DEFAULT_ASSUMPTIONS["tax_rate"]),
        step=0.01,
    )
    reentry_probability = st.sidebar.slider(
        "Non-earner re-entry probability",
        0.0,
        1.0,
        float(DEFAULT_ASSUMPTIONS["reentry_probability"]),
        step=0.05,
    )
    payable_benefit_factor = st.sidebar.slider(
        "Social Security payable factor",
        0.0,
        1.0,
        float(DEFAULT_ASSUMPTIONS["payable_benefit_factor"]),
        step=0.05,
    )
    income_security_floor_monthly = st.sidebar.slider(
        "Income-security floor benchmark (monthly 2022 dollars)",
        min_value=0,
        max_value=841,
        value=int(DEFAULT_ASSUMPTIONS["income_security_floor_monthly"]),
        step=1,
        format="$%d",
        help=(
            "Scenario benchmark calibrated to the December 2022 average SSI payment ($622). "
            "It is a modeled income top-up, not a universal entitlement or an SSI eligibility estimate."
        ),
    )
    inheritance_horizon_years = st.sidebar.slider(
        "Expected inheritance horizon (years)",
        min_value=5,
        max_value=30,
        value=int(DEFAULT_ASSUMPTIONS["inheritance_horizon_years"]),
        step=1,
        help=(
            "Timing scenario for discounting expected inheritances; it is not observed parent-child timing."
        ),
    )
    st.sidebar.caption(SOURCE_NOTE)
    return {
        "discount_rate": discount_rate,
        "wage_growth": wage_growth,
        "retirement_age": retirement_age,
        "employment_probability": employment_probability,
        "tax_rate": tax_rate,
        "reentry_probability": reentry_probability,
        "payable_benefit_factor": payable_benefit_factor,
        "income_security_floor_monthly": income_security_floor_monthly,
        "inheritance_horizon_years": inheritance_horizon_years,
    }


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
            "summary net worth and weights plus detailed respondent/spouse wage, work-schedule, retirement, "
            "and pension fields. See Methodology for source links."
        )
