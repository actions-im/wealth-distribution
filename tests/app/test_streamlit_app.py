from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from scripts.reproduce_report import _fixture_households


def test_home_uses_two_state_distribution_shift():
    app = AppTest.from_file("app.py", default_timeout=20).run(timeout=20)

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
    assert "expected labor earnings" in visible_copy
    assert "Social Security" in visible_copy
    assert "defined-benefit pension payments" in visible_copy
    assert "income-security scenario" in visible_copy
    assert "constrained expected-inheritance reallocation" in visible_copy
    assert "affirmative SCF inheritance-expectation" in visible_copy
    assert "including SCF imputation where applicable" in visible_copy
    assert "does not add or create national wealth" in visible_copy
    assert "newly created wealth" not in visible_copy.lower()
    assert "valid current-ownership accounting measure" in visible_copy
    assert "incomplete when used as a measure of total economic value" in visible_copy
    assert "future cash flows, risk, and discounting" in visible_copy
    assert "scheduled Social Security benefits" in visible_copy
    assert "4,595 surveyed SCF families" in visible_copy
    assert "five multiple-imputation implicates" in visible_copy
    assert "22,975 record rows" in visible_copy
    assert "WGT" in visible_copy
    assert "Expected inheritance horizon (years)" in [slider.label for slider in app.slider]
    assert "Human-capital liquidity weight" not in [slider.label for slider in app.slider]


def test_home_uses_purpose_built_chart_helper():
    source = Path("wealth_report/app/pages/home.py").read_text()
    bootstrap = Path("wealth_report/app/bootstrap.py").read_text()

    assert "distribution_shift_figure" in source
    assert "build_distribution_shift_data" in source
    assert "load_page_report" in source
    assert "validate_inheritance_reallocation_conservation" in bootstrap
    assert "px.bar" not in source


def test_age_distribution_shift_page_renders_six_within_age_views():
    app = AppTest.from_file(
        "wealth_report/app/pages/age_slicing.py", default_timeout=40
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
    assert "Negative conventional shares represent aggregate debt" in visible_copy
    assert "load_page_report" in Path("wealth_report/app/pages/age_slicing.py").read_text()
    assert (
        "validate_inheritance_reallocation_conservation"
        in Path("wealth_report/app/bootstrap.py").read_text()
    )


def test_explicit_public_navigation_has_only_three_pages():
    source = Path("app.py").read_text()

    assert "st.navigation" in source
    assert source.count("st.Page(") == 3
    assert 'st.Page("wealth_report/app/pages/home.py", title="Home"' in source
    assert 'st.Page("wealth_report/app/pages/age_slicing.py", title="Age slicing"' in source
    assert 'st.Page("wealth_report/app/pages/methodology.py", title="Methodology"' in source
    assert not Path("pages").exists()


def test_assumptions_persist_when_navigating_between_pages():
    app = AppTest.from_file("app.py", default_timeout=30).run(timeout=30)
    discount = next(slider for slider in app.slider if slider.label == "Discount rate")
    discount.set_value(0.05)
    app.run(timeout=30)

    app.switch_page("wealth_report/app/pages/age_slicing.py").run(timeout=30)

    persisted = next(slider for slider in app.slider if slider.label == "Discount rate")
    assert persisted.value == pytest.approx(0.05)


def test_direct_page_rerun_keeps_assumption_widgets_live():
    app = AppTest.from_file(
        "wealth_report/app/pages/age_slicing.py", default_timeout=30
    ).run(timeout=30)
    discount = next(slider for slider in app.slider if slider.label == "Discount rate")
    discount.set_value(0.05)
    app.run(timeout=30)

    persisted = next(slider for slider in app.slider if slider.label == "Discount rate")
    assert persisted.value == pytest.approx(0.05)


def test_direct_home_page_renders_without_navigation_registry(monkeypatch):
    households = _fixture_households().assign(
        continuation_income_security_floor=0.0,
        continuation_expected_inheritance=0.0,
        continuation_estate_donor_reserve=0.0,
    )
    monkeypatch.setattr(
        "wealth_report.app.cache.load_comprehensive_report_data",
        lambda **_assumptions: households,
    )

    app = AppTest.from_file(
        "wealth_report/app/pages/home.py",
        default_timeout=20,
    ).run(timeout=20)

    assert not app.exception
    assert app.title[0].value == (
        "Conventional Wealth and Comprehensive Household Resources"
    )


def test_point_estimate_warning_is_adjacent_on_home_and_age_pages():
    home = AppTest.from_file("app.py", default_timeout=30).run(timeout=30)
    age = AppTest.from_file(
        "wealth_report/app/pages/age_slicing.py", default_timeout=30
    ).run(timeout=30)

    assert any("point estimates" in warning.value.lower() for warning in home.warning)
    assert any("point estimates" in warning.value.lower() for warning in age.warning)


def test_home_and_age_charts_have_accessible_data_tables():
    home_source = Path("wealth_report/app/pages/home.py").read_text()
    age_source = Path("wealth_report/app/pages/age_slicing.py").read_text()

    assert "distribution_shift_accessible_table(shift_data)" in home_source
    assert "distribution_shift_accessible_table(panel_data)" in age_source


@pytest.mark.parametrize(
    "page_path",
    [
        "wealth_report/app/pages/home.py",
        "wealth_report/app/pages/methodology.py",
        "wealth_report/app/pages/age_slicing.py",
    ],
)
def test_distribution_pages_block_unconserved_inheritance_data(monkeypatch, page_path):
    monkeypatch.setattr(
        "wealth_report.app.cache.load_comprehensive_report_data",
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
