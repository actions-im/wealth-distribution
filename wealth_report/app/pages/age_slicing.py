from __future__ import annotations

import streamlit as st

from wealth_report.app.cache import load_comprehensive_report_data
from wealth_report.report.charts import distribution_shift_figure
from wealth_report.report.formatting import dollars_trillions
from wealth_report.report.provenance import chart_source_caption
from wealth_report.report.distribution import (
    AGE_SHIFT_BUCKETS,
    build_age_distribution_shift_data,
    validate_inheritance_reallocation_conservation,
)
from wealth_report.app.ui import methodology_expander, render_assumption_sidebar

AGE_LABELS = {
    "<25": "<25",
    "25-34": "25–34",
    "35-44": "35–44",
    "45-54": "45–54",
    "55-64": "55–64",
    "65+": "65+",
}


assumptions = render_assumption_sidebar()
data = load_comprehensive_report_data(
    assumptions["discount_rate"],
    assumptions["wage_growth"],
    assumptions["retirement_age"],
    assumptions["employment_probability"],
    assumptions["reentry_probability"],
    assumptions["tax_rate"],
    assumptions["payable_benefit_factor"],
    assumptions["income_security_floor_monthly"],
    assumptions["inheritance_horizon_years"],
)
validate_inheritance_reallocation_conservation(data)
age_shift_data = build_age_distribution_shift_data(data)

st.title("Distribution shifts by age")
st.write(
    "The distribution shift looks different across the life cycle. Each panel compares conventional "
    "net worth with all modeled future resources for SCF families in one respondent-age bucket."
)
st.info(
    "All modeled future resources include a constrained aggregate inheritance reallocation: discounted "
    "positive credits are assigned only to families with affirmative SCF inheritance-expectation responses "
    "and positive field values (including SCF imputation where applicable), then offset by the same weighted "
    "aggregate of mortality-weighted reserves for estate-intending owners. It does not add or create national "
    "wealth. Conventional net "
    "worth remains the current-ownership measure and is not changed by the reallocation.",
    icon=":material/account_balance:",
)
st.info(
    "Every bar is ranked independently within that age bucket. For example, Bottom 50% means the "
    "bottom half of families of that age under the measure shown—not a nationally fixed group of people.",
    icon=":material/info:",
)
st.info(
    "Negative conventional shares represent aggregate debt in a ranked interval. They are drawn to the "
    "left of zero rather than omitted from the age-panel bars.",
    icon=":material/account_balance:",
)
st.caption(
    "Unit: SCF family; age: survey respondent's age. Modeled future resources include estimated future "
    "labor earnings, Social Security, defined-benefit pensions, and a modeled income-security floor, subject "
    "to the active assumptions, plus the constrained aggregate inheritance reallocation described above."
)

age_columns = st.columns(2)
for index, age_bucket in enumerate(AGE_SHIFT_BUCKETS):
    panel_data = age_shift_data.loc[age_shift_data["age_group"] == age_bucket]
    if panel_data.empty:
        continue
    first_row = panel_data.iloc[0]
    with age_columns[index % 2]:
        with st.container(border=True):
            st.subheader(AGE_LABELS[age_bucket])
            st.caption(
                f"{float(first_row['weighted_family_count']) / 1_000_000:,.1f}M weighted SCF families · "
                f"{dollars_trillions(float(first_row['all_resources_total']))} all modeled resources"
            )
            st.plotly_chart(distribution_shift_figure(panel_data), width="stretch")

st.caption(chart_source_caption())
methodology_expander()
