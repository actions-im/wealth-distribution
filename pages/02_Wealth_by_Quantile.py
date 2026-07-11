from __future__ import annotations

import plotly.express as px
import streamlit as st

from src.app_data import load_comprehensive_report_data
from src.real_data import aggregate_ranked_resource_distributions
from src.ui import methodology_expander, render_assumption_sidebar


st.set_page_config(page_title="Resources by Weighted Rank", layout="wide")
assumptions = render_assumption_sidebar()
data = load_comprehensive_report_data(
    assumptions["discount_rate"],
    assumptions["wage_growth"],
    assumptions["retirement_age"],
    assumptions["employment_probability"],
    assumptions["reentry_probability"],
    assumptions["tax_rate"],
    assumptions["payable_benefit_factor"],
)
distribution = aggregate_ranked_resource_distributions(data)
distribution["Measure"] = distribution["measure"].map(
    {
        "conventional": "Conventional net worth",
        "defensive": "Defensive accrued resources",
        "continuation": "Continuation resources",
    }
)

st.title("Resource Shares by Measure-Specific Weighted Rank")
st.write(
    "Every distribution is re-ranked using the measure being reported. A household can therefore move "
    "between groups when nonmarketable resources are added. This avoids presenting a fixed-net-worth-rank "
    "decomposition as though it were the distribution of another measure."
)
figure = px.bar(
    distribution,
    x="rank_group",
    y="wealth_share",
    color="Measure",
    barmode="group",
    labels={"rank_group": "Weighted rank", "wealth_share": "Resource share"},
)
figure.update_yaxes(tickformat=".0%")
st.plotly_chart(figure, width="stretch")
st.dataframe(
    distribution[
        ["Measure", "rank_group", "rank_basis", "household_share", "wealth_share", "weighted_total"]
    ],
    hide_index=True,
    width="stretch",
)
st.caption(
    "Units: weighted_total is 2022 dollars summed with SCF family weights. Shares can be negative for a "
    "group if its net liabilities exceed its positive resources."
)
methodology_expander()
