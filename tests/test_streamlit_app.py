from pathlib import Path

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


def test_home_uses_purpose_built_chart_helper():
    source = Path("Home.py").read_text()

    assert "distribution_shift_figure" in source
    assert "build_distribution_shift_data" in source
    assert "px.bar" not in source


def test_age_distribution_shift_page_renders_six_within_age_views():
    app = AppTest.from_file(
        "pages/08_Age_Distribution_Shift.py", default_timeout=40
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
