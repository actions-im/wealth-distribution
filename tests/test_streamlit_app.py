from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest


def test_home_uses_two_state_distribution_shift():
    app = AppTest.from_file("Home.py", default_timeout=20).run(timeout=20)

    assert not app.exception
    labels = [metric.label for metric in app.metric]
    assert labels == ["Bottom 50%", "Next 40%", "Next 9%", "Top 1%"]
    assert all("full wealth" not in label.lower() for label in labels)
    assert any("Lifecycle composition matters" in warning.value for warning in app.warning)
    assert any(
        "How including future resources changes the distribution" in item.value
        for item in app.subheader
    )
    visible_copy = " ".join(
        [item.value for item in app.markdown] + [item.value for item in app.info]
    )
    assert "future labor earnings" in visible_copy
    assert "Social Security" in visible_copy
    assert "defined-benefit pensions" in visible_copy
    assert "income-security floor" in visible_copy
    assert "constrained aggregate inheritance reallocation" in visible_copy
    assert "affirmative SCF inheritance-expectation" in visible_copy
    assert "including SCF imputation where applicable" in visible_copy
    assert "does not add or create national wealth" in visible_copy
    assert "newly created wealth" not in visible_copy.lower()
    assert "Expected inheritance horizon (years)" in [slider.label for slider in app.slider]


def test_home_uses_purpose_built_chart_helper():
    source = Path("app_pages/home.py").read_text()

    assert "distribution_shift_figure" in source
    assert "build_distribution_shift_data" in source
    assert "validate_inheritance_reallocation_conservation(data)" in source
    assert "px.bar" not in source


def test_age_distribution_shift_page_renders_six_within_age_views():
    app = AppTest.from_file(
        "app_pages/age_slicing.py", default_timeout=40
    ).run(timeout=40)

    assert not app.exception
    assert app.title[0].value == "Distribution shifts by age"
    visible_copy = " ".join(
        [item.value for item in app.markdown] + [item.value for item in app.info]
    )
    assert "within that age bucket" in visible_copy
    headings = [item.value for item in app.subheader]
    assert set(headings) == {"<25", "25–34", "35–44", "45–54", "55–64", "65+"}
    assert len(headings) == 6
    assert len(app.get("plotly_chart")) == 6
    assert "constrained aggregate inheritance reallocation" in visible_copy
    assert "affirmative SCF inheritance-expectation" in visible_copy
    assert "including SCF imputation where applicable" in visible_copy
    assert "does not add or create national wealth" in visible_copy
    assert "newly created wealth" not in visible_copy.lower()
    assert (
        "validate_inheritance_reallocation_conservation(data)"
        in Path("app_pages/age_slicing.py").read_text()
    )


def test_explicit_public_navigation_has_only_three_pages():
    source = Path("Home.py").read_text()

    assert "st.navigation" in source
    assert source.count("st.Page(") == 3
    assert 'st.Page("app_pages/home.py", title="Home"' in source
    assert 'st.Page("app_pages/age_slicing.py", title="Age slicing"' in source
    assert 'st.Page("app_pages/methodology.py", title="Methodology"' in source
    assert not Path("pages").exists()


@pytest.mark.parametrize(
    "page_path",
    [
        "app_pages/home.py",
        "app_pages/methodology.py",
        "app_pages/age_slicing.py",
    ],
)
def test_distribution_pages_block_unconserved_inheritance_data(monkeypatch, page_path):
    monkeypatch.setattr(
        "src.app_data.load_comprehensive_report_data",
        lambda *args, **kwargs: pd.DataFrame(
            {
                "household_weight": [1.0],
                "continuation_expected_inheritance": [10.0],
                "continuation_estate_donor_reserve": [9.0],
            }
        ),
    )

    app = AppTest.from_file(page_path, default_timeout=20).run(timeout=20)

    assert app.exception
    assert "inheritance reallocation conservation failed" in app.exception[0].value
