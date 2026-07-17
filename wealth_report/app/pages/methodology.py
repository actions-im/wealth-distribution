from __future__ import annotations

from dataclasses import asdict

import pandas as pd
import streamlit as st

from wealth_report.app.bootstrap import load_page_report
from wealth_report.app.content import load_markdown
from wealth_report.providers.sources import load_source_registry
from wealth_report.report.distribution import (
    build_age_distribution_shift_data,
    build_distribution_shift_data,
)
from wealth_report.report.provenance import (
    build_age_shift_number_audit,
    build_component_methodology_table,
    build_shift_number_audit,
)
from wealth_report.report.ranking import aggregate_ranked_resource_distributions


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


def main() -> None:
    assumptions, data = load_page_report()
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

    st.subheader("Research question: economic value, not just balance-sheet ownership")
    st.write(load_markdown("methodology/research_question"))

    st.subheader("Data basis")
    st.info(
        load_markdown("methodology/data_basis"),
        icon=":material/dataset:",
    )

    st.subheader("Scope, weighting, and ranking")
    st.write(load_markdown("methodology/scope_and_ranking"))

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
        "This table covers every Home chart value: resource shares and static bar labels, weighted totals and "
        "family shares in this audit, and each percentage-point change."
    )

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
            else (
                f"${float(value):,.0f}"
                if key == "income_security_floor_monthly"
                else f"{float(value):.1%}"
            )
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
        load_markdown("methodology/inheritance_conservation"),
        icon=":material/account_balance:",
    )

    st.subheader("Double-count protection")
    st.info(
        load_markdown("methodology/double_count_protection"),
        icon=":material/security:",
    )

    st.subheader("Exclusions and limitations")
    st.warning(
        load_markdown("methodology/limitations"),
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
                "Documentation": record["documentation_url"] or "",
                "Description": record["description"] or "",
                "Local filename": record["filename"],
                "SHA-256": record["sha256"] or "Provider page / committed snapshot",
            }
        )
    st.dataframe(
        pd.DataFrame(registry_rows),
        hide_index=True,
        width="stretch",
        column_config={
            "Canonical URL": st.column_config.LinkColumn("Canonical URL"),
            "Documentation": st.column_config.LinkColumn("Documentation"),
            "Description": st.column_config.TextColumn(width="large"),
        },
    )
    st.caption(
        "Repository references: docs/methodology.md contains the long-form limitations; "
        "data/sources.json is the machine-readable source registry."
    )

    st.subheader("Reproduction")
    st.code(
        "uv run python scripts/reproduce_report.py --real-data --output-dir build/report",
        language="bash",
    )
    st.caption(load_markdown("methodology/reproduction"))


if __name__ == "__main__":
    import multiprocessing as mp

    if mp.current_process().name == "MainProcess":
        main()
