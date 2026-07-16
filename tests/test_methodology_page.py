from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_methodology_page_renders_complete_audit_sections():
    app = AppTest.from_file("pages/07_Methodology.py", default_timeout=40).run(timeout=40)

    assert not app.exception
    assert app.title[0].value == "Methodology and number audit"
    headings = {item.value for item in app.subheader}
    assert {
        "Measure definitions",
        "Every displayed number",
        "Component formulas",
        "Current assumptions",
        "Double-count protection",
        "Exclusions and limitations",
        "Official sources",
    } <= headings
    visible_text = " ".join(
        [item.value for item in app.markdown]
        + [item.value for item in app.caption]
        + [item.value for item in app.info]
        + [item.value for item in app.warning]
    )
    assert "independently ranked" in visible_text
    assert "not added again" in visible_text
    assert "model-derived" in visible_text
    assert "constrained aggregate reallocation" in visible_text
    assert "not a legal claim" in visible_text


def test_methodology_page_configures_clickable_source_urls():
    source = Path("pages/07_Methodology.py").read_text()

    assert 'st.column_config.LinkColumn("Canonical URL")' in source
    assert "build_shift_number_audit" in source
    assert "build_component_methodology_table" in source
