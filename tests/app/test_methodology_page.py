from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_methodology_page_renders_complete_audit_sections():
    app = AppTest.from_file("wealth_report/app/pages/methodology.py", default_timeout=40).run(timeout=40)

    assert not app.exception
    assert app.title[0].value == "Methodology and number audit"
    headings = {item.value for item in app.subheader}
    assert {
        "Scope, weighting, and ranking",
        "Measure definitions",
        "Home distribution audit",
        "Age slicing number audit",
        "Component formulas",
        "Current assumptions",
        "Inheritance conservation",
        "Double-count protection",
        "Exclusions and limitations",
        "Official sources",
        "Reproduction",
    } <= headings
    visible_text = " ".join(
        [item.value for item in app.markdown]
        + [item.value for item in app.caption]
        + [item.value for item in app.info]
        + [item.value for item in app.warning]
    )
    assert "SCF family" in visible_text
    assert "2022 dollars" in visible_text
    assert "WGT" in visible_text
    assert "independently ranked" in visible_text
    assert "min(claims, capacity)" in visible_text
    assert "weighted credits" in visible_text
    assert "weighted donor reserves" in visible_text
    assert "point estimates" in visible_text
    assert "not added again" in visible_text
    assert "model-derived" in visible_text
    assert "constrained aggregate reallocation" in visible_text
    assert "not a legal claim" in visible_text
    assert "SCF expectation field values (including SCF imputation where applicable)" in visible_text
    assert "consumption is not modeled as an estate reduction" in visible_text
    assert "does not add future returns, yields, rents, dividends, or capital gains" in visible_text
    assert "shown on hover" not in visible_text
    assert "static bar labels" in visible_text
    assert "Research question: economic value, not just balance-sheet ownership" in headings
    assert "valid current-ownership accounting measure" in visible_text
    assert "incomplete when used as a measure of total economic value" in visible_text
    assert "4,595 surveyed SCF families" in visible_text
    assert "five multiple-imputation implicates" in visible_text
    assert "22,975 record rows" in visible_text
    assert "SSA mortality" in visible_text
    assert "Financial Accounts" in visible_text


def test_methodology_page_configures_clickable_source_urls():
    source = Path("wealth_report/app/pages/methodology.py").read_text()

    assert 'st.column_config.LinkColumn("Canonical URL")' in source
    assert "build_shift_number_audit" in source
    assert "build_age_shift_number_audit" in source
    assert "build_component_methodology_table" in source
    assert "--real-data" in source
