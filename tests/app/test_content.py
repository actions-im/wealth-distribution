from pathlib import Path

import pytest


def test_load_markdown_reads_a_named_report_section():
    from wealth_report.app.content import load_markdown

    assert "current-ownership" in load_markdown("home/intro")


def test_load_markdown_rejects_paths_outside_the_content_directory():
    from wealth_report.app.content import load_markdown

    with pytest.raises(ValueError, match="relative path"):
        load_markdown("../README")


def test_report_content_is_not_embedded_in_page_modules():
    for page in ("home.py", "methodology.py"):
        source = (Path("wealth_report/app/pages") / page).read_text()
        assert "load_markdown(" in source


def test_limitations_describe_the_nonworker_history_branch_precisely():
    limitations = Path("content/methodology/limitations.md").read_text()
    methodology = Path("docs/methodology.md").read_text()

    assert "Current nonworking adults" in limitations
    assert "Current nonworking adults" in methodology
    assert "Zero-wage working-age adults" not in limitations
