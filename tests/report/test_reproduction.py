import json

import pytest

import scripts.reproduce_report as report
from scripts.reproduce_report import reproduce
from wealth_report.providers.sources import sha256_file


EXPECTED_OUTPUT_FILES = {
    "age_distribution.csv",
    "component_totals.csv",
    "detail.csv",
    "headline.csv",
    "reconciliation.csv",
    "scenario_controls.csv",
    "top_shares.csv",
}


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
    assert manifest["artifact_type"] == "wealth-report-publication-bundle"
    assert manifest["manifest_schema_version"] == 1
    assert manifest["measure_definitions"]["defensive_resources"]
    assert isinstance(manifest["git_worktree_dirty"], bool)
    assert "git_worktree_status" not in manifest
    assert set(manifest["output_files"]) == EXPECTED_OUTPUT_FILES
    for name, record in manifest["output_files"].items():
        path = tmp_path / name
        assert record == {
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
    assert manifest["active_sources"]["scf_summary"]["integrity_status"] in {
        "verified",
        "hash-unpinned",
        "not-present",
    }
    for record in manifest["active_sources"].values():
        local_path = record.get("local_path")
        assert local_path is None or not local_path.startswith("/")


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


def test_reproduction_fails_integrity_preflight_before_writing(monkeypatch, tmp_path):
    output = tmp_path / "report"
    monkeypatch.setattr(
        report,
        "_active_source_records",
        lambda registry: {
            "scf_summary": {"integrity_status": "mismatch", "local_path": "data/raw/bad.zip"}
        },
    )

    with pytest.raises(ValueError, match="source integrity preflight"):
        reproduce(output_dir=output, use_fixture=True)

    assert not output.exists()


def test_fixture_requires_verified_financial_accounts_snapshot(monkeypatch, tmp_path):
    output = tmp_path / "report"
    monkeypatch.setattr(
        report,
        "_active_source_records",
        lambda registry: {
            "fed_z1_db_pensions": {
                "integrity_status": "not-present",
                "local_path": None,
            }
        },
    )

    with pytest.raises(ValueError, match="required source preflight"):
        reproduce(output_dir=output, use_fixture=True)

    assert not output.exists()


def test_reproduction_replaces_existing_bundle_without_stale_files(tmp_path):
    output = tmp_path / "report"
    reproduce(output_dir=output, use_fixture=True)
    (output / "stale.csv").write_text("old")

    reproduce(output_dir=output, use_fixture=True)

    assert not (output / "stale.csv").exists()
    assert set(path.name for path in output.iterdir()) == {
        *EXPECTED_OUTPUT_FILES,
        "manifest.json",
    }


def test_reproduction_refuses_existing_non_report_directory(tmp_path):
    output = tmp_path / "not-a-report"
    output.mkdir()
    sentinel = output / "keep-me.txt"
    sentinel.write_text("user data")

    with pytest.raises(ValueError, match="not a recognized report bundle"):
        reproduce(output_dir=output, use_fixture=True)

    assert sentinel.read_text() == "user data"
    assert set(path.name for path in output.iterdir()) == {"keep-me.txt"}


def test_reproduction_refuses_symlink_output_directory(tmp_path):
    target = tmp_path / "report"
    reproduce(output_dir=target, use_fixture=True)
    link = tmp_path / "report-link"
    link.symlink_to(target, target_is_directory=True)

    with pytest.raises(ValueError, match="symbolic link"):
        reproduce(output_dir=link, use_fixture=True)

    assert link.is_symlink()
    assert (target / "manifest.json").is_file()


def test_reproduction_refuses_broken_symlink_output_directory(tmp_path):
    link = tmp_path / "broken-report-link"
    link.symlink_to(tmp_path / "missing-report", target_is_directory=True)

    with pytest.raises(ValueError, match="symbolic link"):
        reproduce(output_dir=link, use_fixture=True)

    assert link.is_symlink()
    assert not (tmp_path / "missing-report").exists()


def test_reproduction_refuses_tampered_existing_bundle(tmp_path):
    output = tmp_path / "report"
    reproduce(output_dir=output, use_fixture=True)
    headline = output / "headline.csv"
    headline.write_text(headline.read_text() + "tampered\n")

    with pytest.raises(ValueError, match="not a recognized report bundle"):
        reproduce(output_dir=output, use_fixture=True)

    assert headline.read_text().endswith("tampered\n")


def test_reproduction_aborts_if_absent_destination_appears_during_render(
    monkeypatch, tmp_path
):
    output = tmp_path / "report"
    real_write = report._write_report_bundle

    def create_destination_during_write(**kwargs):
        real_write(**kwargs)
        output.mkdir()
        (output / "sentinel.txt").write_text("appeared during render")

    monkeypatch.setattr(report, "_write_report_bundle", create_destination_during_write)

    with pytest.raises(RuntimeError, match="changed during report generation"):
        reproduce(output_dir=output, use_fixture=True)

    assert (output / "sentinel.txt").read_text() == "appeared during render"
    assert set(path.name for path in output.iterdir()) == {"sentinel.txt"}
    assert not list(tmp_path.glob(".report.*"))


def test_reproduction_restores_destination_that_appears_after_revalidation(
    monkeypatch, tmp_path
):
    output = tmp_path / "report"
    real_revalidate = report._revalidate_output_target

    def create_destination_after_revalidation(target):
        real_revalidate(target)
        output.mkdir()
        (output / "sentinel.txt").write_text("appeared after revalidation")

    monkeypatch.setattr(
        report,
        "_revalidate_output_target",
        create_destination_after_revalidation,
    )

    with pytest.raises(RuntimeError, match="changed during report generation"):
        reproduce(output_dir=output, use_fixture=True)

    assert (output / "sentinel.txt").read_text() == "appeared after revalidation"
    assert set(path.name for path in output.iterdir()) == {"sentinel.txt"}
    assert not list(tmp_path.glob(".report.*"))


def test_reproduction_restores_broken_symlink_that_appears_after_revalidation(
    monkeypatch, tmp_path
):
    output = tmp_path / "report"
    missing_target = tmp_path / "missing-report"
    real_revalidate = report._revalidate_output_target

    def create_symlink_after_revalidation(target):
        real_revalidate(target)
        output.symlink_to(missing_target, target_is_directory=True)

    monkeypatch.setattr(
        report,
        "_revalidate_output_target",
        create_symlink_after_revalidation,
    )

    with pytest.raises(RuntimeError, match="changed during report generation"):
        reproduce(output_dir=output, use_fixture=True)

    assert output.is_symlink()
    assert output.readlink() == missing_target
    assert not missing_target.exists()
    assert not list(tmp_path.glob(".report.*"))


def test_reproduction_refuses_invalid_staged_bundle(monkeypatch, tmp_path):
    output = tmp_path / "report"
    real_write = report._write_report_bundle

    def remove_staged_output(**kwargs):
        real_write(**kwargs)
        (kwargs["output"] / "headline.csv").unlink()

    monkeypatch.setattr(report, "_write_report_bundle", remove_staged_output)

    with pytest.raises(ValueError, match="not a recognized report bundle"):
        reproduce(output_dir=output, use_fixture=True)

    assert not output.exists()
    assert not list(tmp_path.glob(".report.*"))


def test_reproduction_failure_preserves_existing_bundle(monkeypatch, tmp_path):
    output = tmp_path / "report"
    reproduce(output_dir=output, use_fixture=True)
    previous_manifest = (output / "manifest.json").read_text()
    (output / "sentinel.txt").write_text("previous")

    def fail_component_totals(_households):
        raise RuntimeError("simulated export failure")

    monkeypatch.setattr(report, "_component_totals", fail_component_totals)

    with pytest.raises(RuntimeError, match="simulated export failure"):
        reproduce(output_dir=output, use_fixture=True)

    assert (output / "manifest.json").read_text() == previous_manifest
    assert (output / "sentinel.txt").read_text() == "previous"
    assert set(path.name for path in output.iterdir()) == {
        *EXPECTED_OUTPUT_FILES,
        "manifest.json",
        "sentinel.txt",
    }
    assert not list(tmp_path.glob(".report.*"))


def test_first_publish_rename_failure_preserves_bundle_and_cleans_up(
    monkeypatch, tmp_path
):
    output = tmp_path / "report"
    reproduce(output_dir=output, use_fixture=True)
    previous_manifest = (output / "manifest.json").read_text()

    def fail_existing_bundle_rename(source, destination):
        raise OSError("simulated first rename failure")

    monkeypatch.setattr(report.os, "replace", fail_existing_bundle_rename)

    with pytest.raises(OSError, match="simulated first rename failure"):
        reproduce(output_dir=output, use_fixture=True)

    assert (output / "manifest.json").read_text() == previous_manifest
    assert not list(tmp_path.glob(".report.*"))


def test_publish_swap_failure_restores_existing_bundle(monkeypatch, tmp_path):
    output = tmp_path / "report"
    reproduce(output_dir=output, use_fixture=True)
    (output / "sentinel.txt").write_text("previous")
    real_replace = report.os.replace
    calls = 0

    def fail_staging_swap(source, destination):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("simulated rename failure")
        return real_replace(source, destination)

    monkeypatch.setattr(report.os, "replace", fail_staging_swap)

    with pytest.raises(OSError, match="simulated rename failure"):
        reproduce(output_dir=output, use_fixture=True)

    assert (output / "sentinel.txt").read_text() == "previous"
    assert set(path.name for path in output.iterdir()) == {
        *EXPECTED_OUTPUT_FILES,
        "manifest.json",
        "sentinel.txt",
    }
    assert not list(tmp_path.glob(".report.*"))


def test_manifest_discloses_all_documented_exclusion_categories(tmp_path):
    reproduce(output_dir=tmp_path / "report", use_fixture=True)
    manifest = json.loads((tmp_path / "report" / "manifest.json").read_text())
    exclusions = " ".join(manifest["exclusions"]).lower()

    for phrase in (
        "mixed self-employment",
        "child benefits",
        "state and local programs",
        "asset tests",
        "donor-recipient",
        "estate taxes",
        "care costs",
        "charitable transfers",
        "unobserved heirs",
        "future yields",
        "liquidity",
        "collateral value",
        "taxation",
    ):
        assert phrase in exclusions
