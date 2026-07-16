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
    visible_copy = " ".join(item.value for item in app.markdown)
    assert "future labor earnings" in visible_copy
    assert "Social Security" in visible_copy
    assert "defined-benefit pensions" in visible_copy


def test_home_uses_purpose_built_chart_helper():
    source = Path("Home.py").read_text()

    assert "distribution_shift_figure" in source
    assert "build_distribution_shift_data" in source
    assert "px.bar" not in source
