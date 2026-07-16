from __future__ import annotations

from dataclasses import asdict

import pandas as pd
import streamlit as st

from src.app_data import load_comprehensive_report_data
from src.provenance import (
    build_age_shift_number_audit,
    build_component_methodology_table,
    build_shift_number_audit,
)
from src.real_data import aggregate_ranked_resource_distributions
from src.reporting import (
    build_age_distribution_shift_data,
    build_distribution_shift_data,
    validate_inheritance_reallocation_conservation,
)
from src.source_manifest import load_source_registry
from src.ui import render_assumption_sidebar


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
distribution = aggregate_ranked_resource_distributions(data)
shift_data = build_distribution_shift_data(distribution)
number_audit = build_shift_number_audit(shift_data, assumptions)
age_shift_data = build_age_distribution_shift_data(data)
age_number_audit = build_age_shift_number_audit(age_shift_data, assumptions)

st.title("Methodology and number audit")
st.caption(
    "Every report value below is recalculated from the active sidebar assumptions. Official source "
    "inputs are separated from model-derived estimates."
)

st.subheader("Scope, weighting, and ranking")
st.write(
    "The observation is an SCF family. Monetary values are 2022 dollars, and the SCF family weight "
    "WGT produces weighted national totals and family counts. Conventional net worth and all modeled "
    "future resources are ranked independently, so the same rank interval does not contain a fixed set "
    "of families across the two measures. Age-slicing panels apply the same rule after restricting the "
    "data to the respondent-age bucket."
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
                "defined-benefit pension wealth, plus a scenario-based income-security floor top-up and a "
                "constrained aggregate inheritance reallocation."
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

st.subheader("Home distribution audit")
st.write(
    "This table covers every Home chart value: resource shares printed in the bars, weighted totals and "
    "family shares shown on hover, and each percentage-point change."
)


def format_audit_value(value: float, unit: str) -> str:
    if unit in {"resource share", "weighted household share"}:
        return f"{value:.1%}"
    if unit == "2022 dollars":
        return f"${value / 1e12:,.2f}T"
    if unit == "percentage points":
        return f"{value:+.1f} pp".replace("-", "−")
    if unit == "weighted SCF families":
        return f"{value / 1_000_000:,.1f}M"
    return f"{value:,.3f}"


audit_display = number_audit.copy()
audit_display.insert(0, "Report view", "Home")
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

st.subheader("Age slicing number audit")
st.write(
    "This table traces every age-panel chart value and its panel caption: weighted SCF family count "
    "and all modeled resources total. Each panel is independently ranked within its respondent-age bucket."
)
age_audit_display = age_number_audit.copy()
age_audit_display.insert(
    3,
    "Displayed value",
    [
        format_audit_value(float(value), str(unit))
        for value, unit in zip(
            age_audit_display["Value"], age_audit_display["Unit"], strict=True
        )
    ],
)
st.dataframe(
    age_audit_display.drop(columns=["Value"]),
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

st.subheader("Inheritance conservation")
st.info(
    "The continuation-resource calculation enforces weighted credits = weighted donor reserves: "
    "sum(WGT × recipient credit) = sum(WGT × donor reserve), within a one-cent or one-part-in-10^12 "
    "floating-point tolerance. Recipient claims are funded only up to min(claims, capacity), so the "
    "constrained aggregate reallocation does not create national wealth.",
    icon=":material/account_balance:",
)

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
    "two-adult families, its survival calculation assumes independent mortality. Expected inheritance is a "
    "constrained aggregate reallocation of SCF expectation field values (including SCF imputation where "
    "applicable), not a legal claim or a current ownership "
    "record: public SCF data do not link a recipient family to a donor family. It leaves conventional net worth "
    "unchanged; consumption is not modeled as an estate reduction. The model does not add future returns, yields, "
    "rents, dividends, or capital gains to an inherited asset already reflected in donor net worth. Estate taxes, "
    "care costs, gifts, charity, siblings, and unobserved heirs are also not modeled.",
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

st.subheader("Reproduction")
st.code(
    "uv run python scripts/reproduce_report.py --fixture --output-dir build/report",
    language="bash",
)
st.caption(
    "The fixture validates code paths and output contracts. The Streamlit report loads pinned real SCF "
    "inputs for point estimates."
)
