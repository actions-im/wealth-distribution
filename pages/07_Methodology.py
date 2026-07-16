from __future__ import annotations

from dataclasses import asdict

import pandas as pd
import streamlit as st

from src.app_data import load_comprehensive_report_data
from src.provenance import build_component_methodology_table, build_shift_number_audit
from src.real_data import aggregate_ranked_resource_distributions
from src.reporting import build_distribution_shift_data
from src.source_manifest import load_source_registry
from src.ui import render_assumption_sidebar


st.set_page_config(
    page_title="Methodology and number audit",
    page_icon=":material/menu_book:",
    layout="wide",
)

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
distribution = aggregate_ranked_resource_distributions(data)
shift_data = build_distribution_shift_data(distribution)
number_audit = build_shift_number_audit(shift_data, assumptions)

st.title("Methodology and number audit")
st.caption(
    "Every home-page value below is recalculated from the active sidebar assumptions. Official source "
    "inputs are separated from model-derived estimates."
)

st.subheader("Measure definitions")
definitions = pd.DataFrame(
    [
        {
            "Measure": "Conventional net worth",
            "Definition": "Federal Reserve SCF assets minus liabilities (NETWORTH).",
            "Rank": "SCF families ranked independently by NETWORTH.",
            "Status": "Computed directly from official SCF microdata.",
        },
        {
            "Measure": "All modeled future resources",
            "Definition": (
                "Conventional net worth plus continuation labor earnings, Social Security, and "
                "defined-benefit pension wealth, plus a scenario-based income-security floor top-up."
            ),
            "Rank": "SCF families ranked independently by continuation_resources.",
            "Status": "Model-derived from official inputs and visible assumptions.",
        },
    ]
)
st.dataframe(definitions, hide_index=True, width="stretch")
st.caption(
    "The two states are independently ranked. A rank interval therefore describes a position in each "
    "distribution, not a fixed set of households flowing from one state to another."
)

st.subheader("Every displayed number")
st.write(
    "This table covers the resource shares printed in the bars, weighted totals and household shares "
    "shown on hover, and every percentage-point change printed below the plot."
)


def format_audit_value(value: float, unit: str) -> str:
    if unit in {"resource share", "weighted household share"}:
        return f"{value:.1%}"
    if unit == "2022 dollars":
        return f"${value / 1e12:,.2f}T"
    if unit == "percentage points":
        return f"{value:+.1f} pp".replace("-", "−")
    return f"{value:,.3f}"


audit_display = number_audit.copy()
audit_display.insert(
    1,
    "Displayed value",
    [
        format_audit_value(float(value), str(unit))
        for value, unit in zip(
            audit_display["Value"], audit_display["Unit"], strict=True
        )
    ],
)
st.dataframe(
    audit_display.drop(columns=["Value"]),
    hide_index=True,
    width="stretch",
    column_config={
        "Displayed number": st.column_config.TextColumn(width="large"),
        "Formula": st.column_config.TextColumn(width="large"),
        "Source fields": st.column_config.TextColumn(width="large"),
    },
)

st.subheader("Component formulas")
st.dataframe(
    build_component_methodology_table(assumptions),
    hide_index=True,
    width="stretch",
    column_config={
        "Calculation": st.column_config.TextColumn(width="large"),
        "Source fields": st.column_config.TextColumn(width="large"),
        "Important treatment": st.column_config.TextColumn(width="large"),
    },
)

st.subheader("Current assumptions")
assumption_labels = {
    "discount_rate": "Real discount rate",
    "wage_growth": "Real wage growth",
    "retirement_age": "Retirement age",
    "employment_probability": "Employment probability",
    "reentry_probability": "Non-earner re-entry probability",
    "tax_rate": "Flat tax haircut",
    "payable_benefit_factor": "Social Security payable factor",
    "income_security_floor_monthly": "Income-security floor benchmark (monthly 2022 dollars)",
    "inheritance_horizon_years": "Expected inheritance horizon (years)",
}
assumption_rows = []
for key, label in assumption_labels.items():
    value = assumptions[key]
    rendered = (
        str(value)
        if key in {"retirement_age", "inheritance_horizon_years"}
        else f"${float(value):,.0f}" if key == "income_security_floor_monthly" else f"{float(value):.1%}"
    )
    assumption_rows.append(
        {
            "Assumption": label,
            "Current value": rendered,
            "Role": "User-adjustable scenario control; not an official estimate",
        }
    )
st.dataframe(pd.DataFrame(assumption_rows), hide_index=True, width="stretch")

st.subheader("Double-count protection")
st.info(
    "Defined-contribution and account-type retirement balances are already included in SCF NETWORTH "
    "and are not added again. Only qualifying lifetime defined-benefit payment flows are incremental.",
    icon=":material/security:",
)

st.subheader("Exclusions and limitations")
st.warning(
    "Future earnings are personal, risky, nontransferable, and illiquid. The public model excludes "
    "unsupported Social Security spousal/survivor benefits, DB survivor annuities without joint-life "
    "inputs, and mixed business income that could double count returns already embedded in business equity. "
    "Zero-wage working-age adults receive a peer-based re-entry wage imputation times the visible re-entry "
    "probability; this is a scenario assumption, not observed earnings. Headline values are point estimates; "
    "replicate-weight intervals are not yet displayed. The income-security "
    "floor is a scenario benchmark, not an estimate that every family qualifies for SSI or another program; it "
    "also uses only one or two adults because child and state-program eligibility inputs are not modeled. For "
    "two-adult families, its survival calculation assumes independent mortality.",
    icon=":material/warning:",
)

st.subheader("Official sources")
registry_rows = []
for key, specification in load_source_registry().items():
    record = asdict(specification)
    registry_rows.append(
        {
            "Source key": key,
            "Provider": record["provider"],
            "Vintage": record["vintage"],
            "Canonical URL": record["url"],
            "Local filename": record["filename"],
            "SHA-256": record["sha256"] or "Provider page / committed snapshot",
        }
    )
st.dataframe(
    pd.DataFrame(registry_rows),
    hide_index=True,
    width="stretch",
    column_config={"Canonical URL": st.column_config.LinkColumn("Canonical URL")},
)
st.caption(
    "Repository references: docs/methodology.md contains the long-form limitations; "
    "data/sources.json is the machine-readable source registry."
)
