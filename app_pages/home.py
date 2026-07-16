from __future__ import annotations

import streamlit as st

from src.app_data import load_comprehensive_report_data
from src.charts import distribution_shift_figure
from src.formatting import percent
from src.real_data import aggregate_ranked_resource_distributions
from src.reporting import (
    build_distribution_shift_data,
    validate_inheritance_reallocation_conservation,
)
from src.ui import methodology_expander, render_assumption_sidebar


assumptions = render_assumption_sidebar()
data = load_comprehensive_report_data(
    discount_rate=assumptions["discount_rate"],
    wage_growth=assumptions["wage_growth"],
    retirement_age=assumptions["retirement_age"],
    employment_probability=assumptions["employment_probability"],
    reentry_probability=assumptions["reentry_probability"],
    tax_rate=assumptions["tax_rate"],
    payable_benefit_factor=assumptions["payable_benefit_factor"],
    income_security_floor_monthly=assumptions["income_security_floor_monthly"],
    inheritance_horizon_years=assumptions["inheritance_horizon_years"],
)
validate_inheritance_reallocation_conservation(data)
distribution = aggregate_ranked_resource_distributions(data)
shift_data = build_distribution_shift_data(distribution)

st.title("Conventional Wealth and Comprehensive Household Resources")
st.caption(
    "2022 Survey of Consumer Finances families · each measure ranked independently · "
    "modeled values are nonmarketable resources, not official Federal Reserve wealth statistics"
)
st.markdown(
    "Conventional net worth measures owned assets minus liabilities. This report also asks a different "
    "question: how are modeled lifetime economic resources distributed when expected labor earnings, "
    "Social Security, defined-benefit pensions, and a scenario-based income-security floor are valued explicitly? "
    "The all-modeled-resources state also includes a constrained aggregate inheritance reallocation. "
    "The measures are shown together, with their differences and limitations visible."
)

comparison_rows = shift_data.drop_duplicates("group")
with st.container(horizontal=True):
    for row in comparison_rows.itertuples(index=False):
        delta = f"{row.change_pp:+.1f} pp vs conventional".replace("-", "−")
        st.metric(
            str(row.group),
            percent(float(row.future_resources_share)),
            delta,
            delta_color="off",
            border=True,
        )

st.caption(
    f"Baseline: {assumptions['discount_rate']:.1%} real discount rate; "
    f"{assumptions['retirement_age']} retirement age; "
    f"{assumptions['payable_benefit_factor']:.0%} Social Security payable factor."
    f" ${assumptions['income_security_floor_monthly']:,.0f}/month income-security benchmark."
)

st.subheader("How including future resources changes the distribution")
st.markdown(
    "The second bar adds **future labor earnings, Social Security, defined-benefit pensions, and a "
    "modeled income-security floor**, plus a **constrained aggregate inheritance reallocation**, "
    "to conventional net worth. It is labeled *all modeled future resources* because these values "
    "are estimates—not liquid or transferable assets. Positive inheritance credits are assigned only to "
    "families with affirmative SCF inheritance-expectation responses and positive field values (including "
    "SCF imputation where applicable), then offset by the same weighted aggregate of mortality-weighted "
    "reserves for estate-intending owners; it does not add or create national wealth. Conventional "
    "net worth remains a current-ownership measure and is not changed by this reallocation."
)
st.plotly_chart(
    distribution_shift_figure(shift_data),
    width="stretch",
    config={"displayModeBar": False},
)
st.caption(
    "Each bar totals 100% and is independently ranked under its own measure. Percentage-point "
    "changes compare rank-group shares, not the movement of the same households. Source: Federal "
    "Reserve 2022 SCF summary and full public files; SSA mortality and 2022 program parameters; "
    "SCF inheritance-expectation and estate-intent fields; model calculations in this repository."
)
st.page_link(
    "app_pages/methodology.py",
    label="Audit every displayed number, formula, and source",
    icon=":material/menu_book:",
)

with st.expander("Definitions, components, and exclusions"):
    st.markdown(
        "- **Conventional net worth:** SCF assets minus liabilities. Retirement account balances are already included.\n"
        "- **Defensive accrued resources:** conventional net worth plus zero-real-growth labor resources, "
        "accrued Social Security, and accrued DB benefits. Social Security is net of modeled future employee "
        "contributions and the selected payable factor.\n"
        "- **Continuation resources:** conventional net worth plus labor earnings and retirement claims under "
        "continued earnings and pension accrual through retirement, plus a modeled income-security top-up "
        "when projected annual income is below the selected benchmark, and a constrained aggregate inheritance "
        "reallocation. The inheritance credit and donor reserve offset in the weighted national total.\n"
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
