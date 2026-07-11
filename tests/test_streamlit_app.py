from streamlit.testing.v1 import AppTest


def test_home_uses_defensible_headline_labels():
    app = AppTest.from_file("Home.py", default_timeout=20).run(timeout=20)

    assert not app.exception
    labels = [metric.label for metric in app.metric]
    assert any("Defensive accrued resources" in label for label in labels)
    assert all("full wealth" not in label.lower() for label in labels)
    assert any("Lifecycle composition matters" in warning.value for warning in app.warning)
