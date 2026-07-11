from __future__ import annotations

import plotly.express as px
import streamlit as st

from src.app_data import load_comprehensive_report_data
from src.formatting import percent
from src.real_data import aggregate_ranked_resource_distributions
from src.ui import methodology_expander, render_assumption_sidebar


st.set_page_config(
    page_title="Comprehensive Household Resources",
    layout="wide",
    initial_sidebar_state="collapsed",
)

assumptions = render_assumption_sidebar()
data = load_comprehensive_report_data(
    discount_rate=assumptions["discount_rate"],
    wage_growth=assumptions["wage_growth"],
    retirement_age=assumptions["retirement_age"],
    employment_probability=assumptions["employment_probability"],
    reentry_probability=assumptions["reentry_probability"],
    tax_rate=assumptions["tax_rate"],
    payable_benefit_factor=assumptions["payable_benefit_factor"],
)
distribution = aggregate_ranked_resource_distributions(data)

st.title("Conventional Wealth and Comprehensive Household Resources")
st.caption(
    "2022 Survey of Consumer Finances families · each measure ranked independently · "
    "modeled values are nonmarketable resources, not official Federal Reserve wealth statistics"
)
st.markdown(
    "Conventional net worth measures owned assets minus liabilities. This report also asks a different "
    "question: how are modeled lifetime economic resources distributed when expected labor earnings, "
    "Social Security, and defined-benefit pensions are valued explicitly? The measures are shown together, "
    "with their differences and limitations visible."
)


def share(measure: str, groups: list[str]) -> float:
    selected = distribution[
        (distribution["measure"] == measure) & distribution["rank_group"].isin(groups)
    ]
    return float(selected["wealth_share"].sum())


top_groups = ["99-99.9%", "Top 0.1%"]
bottom_groups = ["Bottom 50%", "50-90%"]
columns = st.columns(3)
columns[0].metric("Top 1% · conventional net worth", percent(share("conventional", top_groups)))
columns[1].metric("Top 1% · Defensive accrued resources", percent(share("defensive", top_groups)))
columns[2].metric("Top 1% · continuation resources", percent(share("continuation", top_groups)))
columns = st.columns(3)
columns[0].metric("Bottom 90% · conventional net worth", percent(share("conventional", bottom_groups)))
columns[1].metric(
    "Bottom 90% · Defensive accrued resources", percent(share("defensive", bottom_groups))
)
columns[2].metric("Bottom 90% · continuation resources", percent(share("continuation", bottom_groups)))

st.caption(
    f"Baseline: {assumptions['discount_rate']:.1%} real discount rate; "
    f"{assumptions['retirement_age']} retirement age; "
    f"{assumptions['payable_benefit_factor']:.0%} Social Security payable factor."
)

chart_data = distribution.copy()
chart_data["Measure"] = chart_data["measure"].map(
    {
        "conventional": "Conventional net worth",
        "defensive": "Defensive accrued resources",
        "continuation": "Continuation resources",
    }
)
figure = px.bar(
    chart_data,
    x="rank_group",
    y="wealth_share",
    color="Measure",
    barmode="group",
    labels={"rank_group": "Measure-specific weighted rank", "wealth_share": "Share"},
    category_orders={
        "rank_group": ["Bottom 50%", "50-90%", "90-99%", "99-99.9%", "Top 0.1%"]
    },
)
figure.update_yaxes(tickformat=".0%")
st.plotly_chart(figure, width="stretch")
st.caption(
    "Source: Federal Reserve 2022 SCF summary and full public files; SSA 2019 period life table "
    "published with the 2022 Trustees Report; model calculations in this repository."
)

with st.expander("Definitions, components, and exclusions"):
    st.markdown(
        "- **Conventional net worth:** SCF assets minus liabilities. Retirement account balances are already included.\n"
        "- **Defensive accrued resources:** conventional net worth plus zero-real-growth labor resources, "
        "accrued Social Security, and accrued DB benefits. Social Security is net of modeled future employee "
        "contributions and the selected payable factor.\n"
        "- **Continuation resources:** conventional net worth plus labor earnings and retirement claims under "
        "continued earnings and pension accrual through retirement.\n"
        "- **Excluded:** unsupported Social Security spousal/survivor benefits and DB survivor annuities without "
        "joint-life inputs. Defined-contribution balances are never added twice."
    )

st.warning(
    "Lifecycle composition matters. Younger families generally have more remaining labor resources and less "
    "accumulated balance-sheet wealth. This is a cross-sectional comparison under the same lifecycle framework, "
    "not a claim that labor resources are liquid, transferable, collateralizable, or inheritable."
)

with st.expander("Normative argument (separate from the estimates)"):
    st.write(
        "Claims about equality of rights versus equality of outcomes are political or philosophical claims. "
        "They do not follow mechanically from these estimates, and the empirical calculations do not depend on them."
    )

methodology_expander()
