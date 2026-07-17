import json

import scripts.reproduce_report as report
from scripts.reproduce_report import reproduce


def test_reproduction_writes_tables_and_manifest(tmp_path):
    reproduce(output_dir=tmp_path, use_fixture=True)

    assert (tmp_path / "headline.csv").is_file()
    assert (tmp_path / "detail.csv").is_file()
    assert (tmp_path / "top_shares.csv").is_file()
    assert (tmp_path / "component_totals.csv").is_file()
    assert (tmp_path / "age_distribution.csv").is_file()
    assert (tmp_path / "reconciliation.csv").is_file()
    assert (tmp_path / "scenario_controls.csv").is_file()
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    assert manifest["fixture"] is True
    assert manifest["measure_definitions"]["defensive_resources"]
    assert isinstance(manifest["git_worktree_dirty"], bool)
    assert isinstance(manifest["git_worktree_status"], list)
    assert manifest["active_sources"]["scf_summary"]["integrity_status"] in {
        "verified",
        "hash-unpinned",
        "not-present",
    }


def test_real_data_reproduction_exports_live_results(monkeypatch, tmp_path):
    households = report._fixture_households().assign(
        continuation_income_security_floor=0.0,
        continuation_expected_inheritance=0.0,
        continuation_estate_donor_reserve=0.0,
    )
    monkeypatch.setattr(
        report,
        "load_comprehensive_household_data",
        lambda assumptions: households,
        raising=False,
    )

    reproduce(output_dir=tmp_path, use_fixture=False)

    headline = (tmp_path / "headline.csv").read_text()
    components = (tmp_path / "component_totals.csv").read_text()
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    assert "Bottom 50%" in headline
    assert "continuation_labor" in components
    assert "Bottom 50%" in (tmp_path / "age_distribution.csv").read_text()
    assert manifest["fixture"] is False
    assert manifest["active_sources"]
