from pathlib import Path

import pandas as pd

from src.config import DEFAULT_ASSUMPTIONS
from src.provenance import (
    ASSUMPTION_SOURCE,
    COMPUTED_SCF_SOURCE,
    build_component_methodology_table,
    build_number_source_table,
    build_shift_number_audit,
    chart_source_caption,
)
from src.real_data import SCF_2022_DATASET_LABEL
from src.reporting import build_detail_wealth_table, build_executive_share_table


def test_report_tables_include_source_column(real_distribution):
    executive = build_executive_share_table(real_distribution)
    detail = build_detail_wealth_table(real_distribution)

    assert "Source" in executive.columns
    assert "Source" in detail.columns
    assert executive["Source"].str.contains("SCF").all()
    assert detail["Source"].str.contains("SCF").all()


def test_number_source_table_maps_calculated_and_assumption_numbers():
    source_table = build_number_source_table(DEFAULT_ASSUMPTIONS)

    assert {"Number category", "Source", "Method"}.issubset(source_table.columns)
    assert any(source_table["Source"].str.contains(SCF_2022_DATASET_LABEL))
    assert any(source_table["Source"].str.contains(ASSUMPTION_SOURCE))
    assert any(source_table["Method"].str.contains("discount_rate"))
    assert any(source_table["Number category"].str.contains("Income-security floor"))
    assert any(source_table["Method"].str.contains("622"))


def test_chart_source_caption_identifies_computed_scf_source():
    assert chart_source_caption().startswith("Source:")
    assert COMPUTED_SCF_SOURCE in chart_source_caption()


def test_inheritance_reallocation_provenance_discloses_conserved_allocator():
    methodology = build_component_methodology_table(DEFAULT_ASSUMPTIONS)
    row = methodology.loc[
        methodology["Component"] == "Expected inheritance reallocation"
    ].iloc[0]

    assert "X5819" in row["Source fields"]
    assert "X5821" in row["Source fields"]
    assert "X5825" in row["Source fields"]
    assert "SSA mortality" in row["Source fields"]
    assert "horizon=15" in row["Current assumptions"]
    calculation = row["Calculation"].lower()
    assert "discounted recipient claims" in calculation
    assert "mortality-weighted estate donor capacity" in calculation
    assert "min(claims, capacity)" in calculation
    assert "equal weighted credit/reserve conservation" in calculation
    assert "not a legal claim" in row["Important treatment"]

    audit = build_shift_number_audit(_shift_data(), DEFAULT_ASSUMPTIONS)
    future_rows = audit.loc[
        audit["Displayed number"].str.contains("All modeled future resources")
    ]
    assert future_rows["Source fields"].str.contains("X5819, X5821, X5825").all()
    assert "inheritance reallocation" in chart_source_caption()


def test_long_form_docs_disclose_inheritance_reallocation_limits():
    methodology = open("docs/methodology.md").read()
    readme = open("README.md").read()

    for phrase in (
        "reallocates SCF expectation field values rather than creating national wealth",
        "does not link recipient to donor families",
        "neither current legal ownership nor a guaranteed transfer",
        "Estate taxes, care costs, consumption, gifts, charity, siblings, and unobserved heirs are not modeled",
        "Conventional net worth remains unchanged",
        "No future return is added for an inherited asset already valued on the current owner's balance sheet",
        "visible scenario control, not observed transfer timing",
        "without an invented probability haircut in the base scenario",
    ):
        assert phrase in methodology

    assert "expected-inheritance reallocation" in readme
    assert "SCF field value (including SCF imputation where applicable)" in methodology
    assert "SCF field values (including SCF imputation where applicable)" in readme
    assert "reported expectation" not in methodology.lower()
    assert "observed expectation" not in methodology.lower()
    assert "reported expectation" not in readme.lower()
    assert "observed expectation" not in readme.lower()

    inheritance_row = build_component_methodology_table(DEFAULT_ASSUMPTIONS).loc[
        lambda table: table["Component"] == "Expected inheritance reallocation"
    ].iloc[0]
    inheritance_copy = " ".join(inheritance_row.astype(str)).lower()
    assert "scf expectation field value" in inheritance_copy
    assert (
        "scf expectation field values, including scf imputation where applicable"
        in inheritance_copy
    )
    assert "reported x5821" not in inheritance_copy
    assert "reported amount" not in inheritance_copy

    source_method = build_number_source_table(DEFAULT_ASSUMPTIONS).loc[
        lambda table: table["Number category"] == "Expected-inheritance reallocation",
        "Method",
    ].iloc[0].lower()
    assert (
        "scf expectation field values, including scf imputation where applicable"
        in source_method
    )

    for public_artifact in (
        "src/inheritance.py",
        "docs/plans/2026-07-15-inheritance-reallocation-design.md",
        "docs/plans/2026-07-15-inheritance-reallocation-implementation.md",
    ):
        artifact_copy = Path(public_artifact).read_text().lower()
        assert "reported expectation" not in artifact_copy
        assert "observed expectation" not in artifact_copy


def test_shift_number_audit_covers_every_share_total_and_change():
    audit = build_shift_number_audit(_shift_data(), DEFAULT_ASSUMPTIONS)

    assert {
        "Displayed number",
        "Value",
        "Unit",
        "Rank basis",
        "Formula",
        "Source fields",
        "Source keys",
        "Classification",
    } <= set(audit.columns)
    assert (audit["Unit"] == "resource share").sum() == 8
    assert (audit["Unit"] == "2022 dollars").sum() == 8
    assert (audit["Unit"] == "percentage points").sum() == 4
    assert audit["Source keys"].str.len().gt(0).all()
    assert audit["Formula"].str.len().gt(0).all()
    assert audit["Classification"].str.contains("derived|computed", case=False).all()


def test_shift_number_audit_uses_live_values_not_static_copy():
    shift = _shift_data()
    shift.loc[
        (shift["state"] == "All modeled future resources")
        & (shift["group"] == "Bottom 50%"),
        ["share", "future_resources_share", "change_pp"],
    ] = [0.12, 0.12, 10.0]
    audit = build_shift_number_audit(shift, DEFAULT_ASSUMPTIONS)
    row = audit.loc[
        audit["Displayed number"]
        == "Bottom 50% · All modeled future resources · resource share"
    ].iloc[0]

    assert row["Value"] == 0.12


def _shift_data():
    rows = []
    conventional = [0.02, 0.24, 0.39, 0.35]
    future = [0.10, 0.40, 0.31, 0.19]
    groups = ["Bottom 50%", "Next 40%", "Next 9%", "Top 1%"]
    for state, values in (
        ("Conventional net worth", conventional),
        ("All modeled future resources", future),
    ):
        for index, (group, value) in enumerate(zip(groups, values, strict=True)):
            rows.append(
                {
                    "group": group,
                    "state": state,
                    "share": value,
                    "weighted_total": value * 1e12,
                    "household_share": [0.50, 0.40, 0.09, 0.01][index],
                    "rank_basis": (
                        "net_worth"
                        if state == "Conventional net worth"
                        else "continuation_resources"
                    ),
                    "conventional_share": conventional[index],
                    "future_resources_share": future[index],
                    "change_pp": 100 * (future[index] - conventional[index]),
                }
            )
    return pd.DataFrame(rows)
