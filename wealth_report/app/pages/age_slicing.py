from __future__ import annotations

import streamlit as st

from wealth_report.app.bootstrap import load_page_report
from wealth_report.app.ui import methodology_expander
from wealth_report.report.charts import (
    distribution_shift_accessible_table,
    distribution_shift_figure,
)
from wealth_report.report.distribution import (
    AGE_SHIFT_BUCKETS,
    build_age_distribution_shift_data,
)
from wealth_report.report.formatting import dollars_trillions
from wealth_report.report.provenance import chart_source_caption

AGE_LABELS = {
    "<25": "<25",
    "25-34": "25–34",
    "35-44": "35–44",
    "45-54": "45–54",
    "55-64": "55–64",
    "65+": "65+",
}


def main() -> None:
    _assumptions, data = load_page_report()
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
    st.warning(
        "These age panels are model-based point estimates. SCF sampling and imputation uncertainty are "
        "not shown; smaller age groups are especially sensitive to sampling variation.",
        icon=":material/warning:",
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
                st.dataframe(
                    distribution_shift_accessible_table(panel_data),
                    hide_index=True,
                    width="stretch",
                    column_config={
                        "Conventional share": st.column_config.NumberColumn(
                            format="percent"
                        ),
                        "Conventional weighted resources": st.column_config.NumberColumn(
                            format="dollar"
                        ),
                        "All modeled resources share": st.column_config.NumberColumn(
                            format="percent"
                        ),
                        "All modeled weighted resources": st.column_config.NumberColumn(
                            format="dollar"
                        ),
                    },
                )

    st.caption(chart_source_caption())
    methodology_expander()


if __name__ == "__main__":
    import multiprocessing as mp

    if mp.current_process().name == "MainProcess":
        main()
