from __future__ import annotations

import streamlit as st

from wealth_report.app.bootstrap import load_page_report
from wealth_report.app.content import load_markdown
from wealth_report.app.ui import methodology_expander
from wealth_report.report.charts import distribution_shift_figure
from wealth_report.report.distribution import build_distribution_shift_data
from wealth_report.report.formatting import percent
from wealth_report.report.ranking import aggregate_ranked_resource_distributions


def main() -> None:
    assumptions, data = load_page_report()
    distribution = aggregate_ranked_resource_distributions(data)
    shift_data = build_distribution_shift_data(distribution)

    st.title("Conventional Wealth and Comprehensive Household Resources")
    st.caption(
        "2022 Survey of Consumer Finances families · two independently ranked estimands · "
        "model-derived values are not official Federal Reserve wealth statistics"
    )
    st.markdown(load_markdown("home/intro"))
    st.info(
        load_markdown("home/data_basis"),
        icon=":material/dataset:",
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
    st.markdown(load_markdown("home/distribution_context"))
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
        "wealth_report/app/pages/methodology.py",
        label="Audit every displayed number, formula, and source",
        icon=":material/menu_book:",
    )

    with st.expander("Definitions, components, and exclusions"):
        st.markdown(load_markdown("home/definitions"))

    st.warning(load_markdown("home/limitations"))

    with st.expander("Normative argument (separate from the estimates)"):
        st.markdown(load_markdown("home/normative_argument"))

    methodology_expander()


main()
