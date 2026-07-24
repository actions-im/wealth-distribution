from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

import pandas as pd

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
REPORT_ARTIFACT_TYPE = "wealth-report-publication-bundle"
REPORT_MANIFEST_SCHEMA_VERSION = 1
REPORT_OUTPUT_FILES = frozenset(
    {
        "age_distribution.csv",
        "component_totals.csv",
        "detail.csv",
        "headline.csv",
        "reconciliation.csv",
        "scenario_controls.csv",
        "top_shares.csv",
    }
)
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from wealth_report.model.assumptions import ModelAssumptions  # noqa: E402
from wealth_report.report.builder import (  # noqa: E402
    aggregate_ranked_resource_distributions,
    build_ranked_distributions,
    load_comprehensive_household_data,
)
from wealth_report.report.reconciliation import (  # noqa: E402
    OfficialPensionTotal,
    load_official_db_total,
    reconcile,
)
from wealth_report.report.distribution import (  # noqa: E402
    build_age_distribution_shift_data,
    build_distribution_shift_data,
)
from wealth_report.providers.sources import load_source_registry, sha256_file  # noqa: E402


@dataclass(frozen=True)
class _OutputTarget:
    path: Path
    state: str
    device: int | None = None
    inode: int | None = None
    manifest_sha256: str | None = None


def _fixture_households() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "household_id": [1, 2, 3, 4, 5],
            "household_weight": [500, 400, 90, 9, 1],
            "age": [28, 38, 49, 61, 72],
            "net_worth": [30_000, 200_000, 2_000_000, 15_000_000, 200_000_000],
            "accrued_labor": [800_000, 900_000, 700_000, 400_000, 200_000],
            "continuation_labor": [1_100_000, 1_300_000, 1_100_000, 650_000, 350_000],
            "accrued_social_security": [180_000, 230_000, 250_000, 220_000, 180_000],
            "continuation_social_security": [260_000, 320_000, 330_000, 280_000, 220_000],
            "accrued_db_pension": [0, 80_000, 200_000, 250_000, 300_000],
            "continuation_db_pension": [0, 140_000, 300_000, 350_000, 400_000],
        }
    ).assign(
        defensive_resources=lambda frame: frame[
            ["net_worth", "accrued_labor", "accrued_social_security", "accrued_db_pension"]
        ].sum(axis=1),
        continuation_resources=lambda frame: frame[
            [
                "net_worth",
                "continuation_labor",
                "continuation_social_security",
                "continuation_db_pension",
            ]
        ].sum(axis=1),
    )


def _git_revision() -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=False
    )
    return result.stdout.strip() if result.returncode == 0 else None


def _git_worktree_dirty() -> bool:
    """Record cleanliness without leaking local filenames into public metadata."""
    result = subprocess.run(
        ["git", "status", "--porcelain"], capture_output=True, text=True, check=False
    )
    return bool(result.stdout.strip()) if result.returncode == 0 else False


def reproduce(*, output_dir: str | Path, use_fixture: bool = False) -> None:
    target = _validated_output_target(output_dir)
    destination = target.path
    assumptions = ModelAssumptions()
    households = (
        _fixture_households()
        if use_fixture
        else load_comprehensive_household_data(assumptions)
    )
    registry = load_source_registry()
    active_sources = _active_source_records(registry)
    mismatches = [
        key
        for key, record in active_sources.items()
        if record["integrity_status"] == "mismatch"
    ]
    if mismatches:
        raise ValueError(
            "source integrity preflight failed for: " + ", ".join(sorted(mismatches))
        )
    required_verified = {"fed_z1_db_pensions"}
    if not use_fixture:
        required_verified.update(
            {"scf_summary", "scf_full", "ssa_period_life_2019_tr2022"}
        )
    unavailable = [
        key
        for key in sorted(required_verified)
        if active_sources.get(key, {}).get("integrity_status") != "verified"
    ]
    if unavailable:
        raise ValueError(
            "required source preflight failed for: " + ", ".join(unavailable)
        )
    official = load_official_db_total(year=2022)
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(
            prefix=f".{destination.name}.staging-",
            dir=destination.parent,
        )
    )
    try:
        _write_report_bundle(
            output=staging,
            households=households,
            assumptions=assumptions,
            official=official,
            active_sources=active_sources,
            use_fixture=use_fixture,
        )
        _validate_report_bundle(staging)
        _publish_staged_output(staging=staging, target=target)
    except BaseException:
        if staging.exists():
            shutil.rmtree(staging)
        raise


def _write_report_bundle(
    *,
    output: Path,
    households: pd.DataFrame,
    assumptions: ModelAssumptions,
    official: OfficialPensionTotal,
    active_sources: dict[str, dict[str, object]],
    use_fixture: bool,
) -> None:
    ranked = build_ranked_distributions(households)

    headline_rows = []
    detail_rows = []
    metric_columns = {
        "conventional": "net_worth",
        "defensive": "defensive_resources",
        "continuation": "continuation_resources",
    }
    for measure, frame in ranked.items():
        metric = metric_columns[measure]
        weighted_value = frame[metric] * frame["household_weight"]
        total = weighted_value.sum()
        top = frame["rank_group"].isin(["99-99.9%", "Top 0.1%"])
        bottom = frame["rank_group"].isin(["Bottom 50%", "50-90%"])
        headline_rows.append(
            {
                "measure": measure,
                "weighted_total_dollars": total,
                "top_1_share": weighted_value[top].sum() / total,
                "bottom_90_share": weighted_value[bottom].sum() / total,
            }
        )
        for group, group_frame in frame.groupby("rank_group", sort=False):
            detail_rows.append(
                {
                    "measure": measure,
                    "rank_group": group,
                    "rank_basis": metric,
                    "weighted_total_dollars": (
                        group_frame[metric] * group_frame["household_weight"]
                    ).sum(),
                }
            )
    pd.DataFrame(headline_rows).to_csv(output / "top_shares.csv", index=False)
    pd.DataFrame(detail_rows).to_csv(output / "detail.csv", index=False)
    pd.DataFrame(
        [
            {"control": name, "baseline_value": value}
            for name, value in asdict(assumptions).items()
        ]
    ).to_csv(output / "scenario_controls.csv", index=False)

    distribution = aggregate_ranked_resource_distributions(households)
    build_distribution_shift_data(distribution).to_csv(
        output / "headline.csv", index=False
    )
    _component_totals(households).to_csv(output / "component_totals.csv", index=False)
    build_age_distribution_shift_data(households).to_csv(
        output / "age_distribution.csv", index=False
    )

    micro_db_total = float(
        (households["accrued_db_pension"] * households["household_weight"]).sum()
    )
    reconciliation = reconcile(micro_total=micro_db_total, official_total=official.value_dollars)
    pd.DataFrame([asdict(reconciliation)]).to_csv(
        output / "reconciliation.csv", index=False
    )
    manifest = {
        "artifact_type": REPORT_ARTIFACT_TYPE,
        "manifest_schema_version": REPORT_MANIFEST_SCHEMA_VERSION,
        "generated_at": datetime.now(UTC).isoformat(),
        "git_revision": _git_revision(),
        "git_worktree_dirty": _git_worktree_dirty(),
        "fixture": use_fixture,
        "assumptions": asdict(assumptions),
        "measure_definitions": {
            "conventional": "SCF assets minus liabilities",
            "defensive_resources": "net worth plus defensive labor, accrued Social Security, and accrued DB pensions",
            "continuation_resources": (
                "net worth plus continuation labor, Social Security, DB pensions, the income-security "
                "scenario, and the conserved inheritance reallocation"
            ),
        },
        "ranking": "Each measure is ranked independently; rank_group uses weighted cumulative position.",
        "reconciliation": asdict(reconciliation),
        "official_db_reference": asdict(official),
        "active_sources": active_sources,
        "output_files": _output_file_records(output),
        "exclusions": [
            "unsupported Social Security spousal and survivor benefits",
            "reported SSI, disability, survivor/dependent, and unclassified payments are not used as retired-worker benefits",
            "DB survivor annuities without joint survival inputs",
            "DC balances already included in net worth",
            "current non-earners without usable reported former-job earnings history",
            "unreported pension COLA status is treated as fixed nominal",
            "mixed self-employment and business income is not added wholesale",
            "child benefits, state and local programs, asset tests, and program-specific eligibility are not modeled",
            "public SCF data do not identify actual inheritance donor-recipient relationships",
            "estate taxes, care costs, consumption, gifts, charitable transfers, sibling shares, and unobserved heirs are not modeled",
            "expected inheritances do not add future yields, rents, dividends, or capital gains to already valued assets",
            "liquidity, transferability, collateral value, bequest value, and taxation are not assumed equal across components",
        ],
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


def _validated_output_target(output_dir: str | Path) -> _OutputTarget:
    raw_output = Path(output_dir).expanduser()
    if raw_output.is_symlink():
        raise ValueError("output directory cannot be a symbolic link")
    output = raw_output.resolve()
    if output == output.parent:
        raise ValueError("output directory cannot be a filesystem root")
    if output == REPOSITORY_ROOT or output in REPOSITORY_ROOT.parents:
        raise ValueError(
            "output directory cannot replace the repository root or an ancestor"
        )
    if output.exists() and not output.is_dir():
        raise NotADirectoryError(f"output path is not a directory: {output}")
    if not output.exists():
        return _OutputTarget(path=output, state="absent")

    device, inode = _directory_identity(output)
    if not any(output.iterdir()):
        return _OutputTarget(
            path=output,
            state="empty",
            device=device,
            inode=inode,
        )

    manifest_sha256 = _validate_report_bundle(output)
    return _OutputTarget(
        path=output,
        state="bundle",
        device=device,
        inode=inode,
        manifest_sha256=manifest_sha256,
    )


def _directory_identity(path: Path) -> tuple[int, int]:
    metadata = path.stat()
    return metadata.st_dev, metadata.st_ino


def _validate_report_bundle(output: Path) -> str:
    def reject(reason: str) -> None:
        raise ValueError(
            f"existing output directory is not a recognized report bundle: {reason}"
        )

    manifest_path = output / "manifest.json"
    if manifest_path.is_symlink() or not manifest_path.is_file():
        reject("manifest.json is missing or is not a regular file")
    try:
        manifest_bytes = manifest_path.read_bytes()
        manifest = json.loads(manifest_bytes)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        reject(f"manifest.json cannot be read: {exc}")
    if not isinstance(manifest, dict):
        reject("manifest root must be an object")
    if manifest.get("artifact_type") != REPORT_ARTIFACT_TYPE:
        reject("artifact type marker is missing or unsupported")
    if manifest.get("manifest_schema_version") != REPORT_MANIFEST_SCHEMA_VERSION:
        reject("manifest schema version is missing or unsupported")

    output_files = manifest.get("output_files")
    if not isinstance(output_files, dict) or set(output_files) != REPORT_OUTPUT_FILES:
        reject("output file inventory does not match the report contract")
    for name in sorted(REPORT_OUTPUT_FILES):
        record = output_files[name]
        if not isinstance(record, dict):
            reject(f"invalid output record for {name}")
        byte_count = record.get("bytes")
        digest = record.get("sha256")
        if (
            not isinstance(byte_count, int)
            or isinstance(byte_count, bool)
            or byte_count < 0
        ):
            reject(f"invalid byte count for {name}")
        if (
            not isinstance(digest, str)
            or len(digest) != 64
            or any(character not in "0123456789abcdefABCDEF" for character in digest)
        ):
            reject(f"invalid SHA-256 for {name}")
        path = output / name
        if path.is_symlink() or not path.is_file():
            reject(f"{name} is missing or is not a regular file")
        if path.stat().st_size != byte_count:
            reject(f"byte count mismatch for {name}")
        if sha256_file(path).lower() != digest.lower():
            reject(f"SHA-256 mismatch for {name}")

    return hashlib.sha256(manifest_bytes).hexdigest()


def _revalidate_output_target(target: _OutputTarget) -> None:
    _validate_output_snapshot(target, target.path)


def _validate_output_snapshot(target: _OutputTarget, output: Path) -> None:
    def changed() -> None:
        raise RuntimeError(
            f"output directory changed during report generation: {target.path}"
        )

    present = output.exists() or output.is_symlink()
    if target.state == "absent":
        if present:
            changed()
        return
    if not present or output.is_symlink() or not output.is_dir():
        changed()
    if _directory_identity(output) != (target.device, target.inode):
        changed()
    if target.state == "empty":
        if any(output.iterdir()):
            changed()
        return
    if target.state != "bundle":
        changed()
    try:
        manifest_sha256 = _validate_report_bundle(output)
    except (OSError, ValueError):
        changed()
    if manifest_sha256 != target.manifest_sha256:
        changed()


def _publish_staged_output(*, staging: Path, target: _OutputTarget) -> None:
    destination = target.path
    _revalidate_output_target(target)
    backup_root: Path | None = None
    backup: Path | None = None
    remove_backup_root = True

    def restore_backup() -> None:
        nonlocal remove_backup_root
        if backup is None or (not backup.exists() and not backup.is_symlink()):
            return
        try:
            if destination.exists() or destination.is_symlink():
                raise RuntimeError(
                    "cannot restore changed output directory; "
                    f"previous contents preserved at {backup}"
                )
            os.replace(backup, destination)
        except BaseException:
            remove_backup_root = False
            raise

    try:
        if destination.exists() or destination.is_symlink():
            backup_root = Path(
                tempfile.mkdtemp(
                    prefix=f".{destination.name}.backup-",
                    dir=destination.parent,
                )
            )
            backup = backup_root / "previous"
            os.replace(destination, backup)
            try:
                _validate_output_snapshot(target, backup)
            except BaseException:
                restore_backup()
                raise
        elif target.state != "absent":
            raise RuntimeError(
                f"output directory changed during report generation: {destination}"
            )
        try:
            os.replace(staging, destination)
        except BaseException:
            restore_backup()
            raise
    finally:
        if remove_backup_root and backup_root is not None and backup_root.exists():
            shutil.rmtree(backup_root)


def _output_file_records(output: Path) -> dict[str, dict[str, object]]:
    records: dict[str, dict[str, object]] = {}
    for name in sorted(REPORT_OUTPUT_FILES):
        path = output / name
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"missing expected report output: {name}")
        records[name] = {
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
    return records


def _component_totals(households: pd.DataFrame) -> pd.DataFrame:
    components = [
        ("net_worth", "+"),
        ("continuation_labor", "+"),
        ("continuation_social_security", "+"),
        ("continuation_db_pension", "+"),
        ("continuation_income_security_floor", "+"),
        ("continuation_expected_inheritance", "+"),
        ("continuation_estate_donor_reserve", "−"),
        ("continuation_resources", "total"),
    ]
    rows = []
    for component, direction in components:
        if component not in households:
            continue
        rows.append(
            {
                "component": component,
                "direction": direction,
                "weighted_total_dollars": float(
                    (households[component] * households["household_weight"]).sum()
                ),
            }
        )
    return pd.DataFrame(rows)


def _active_source_records(registry: dict) -> dict[str, dict[str, object]]:
    local_paths = {
        "scf_summary": REPOSITORY_ROOT / "data/raw/scf_2022_extract.zip",
        "scf_full": REPOSITORY_ROOT / "data/raw/scf_2022_full.zip",
        "ssa_period_life_2019_tr2022": (
            REPOSITORY_ROOT / "data/reference/ssa_period_life_2019_tr2022.csv"
        ),
        "fed_z1_db_pensions": (
            REPOSITORY_ROOT / "data/reference/fed_z1_defined_benefit_2022.csv"
        ),
    }
    active_keys = (
        "scf_summary",
        "scf_full",
        "ssa_period_life_2019_tr2022",
        "ssa_2022_parameters",
        "ssa_2022_trustees",
        "ssa_2022_ssi",
        "fed_z1_db_pensions",
    )
    records: dict[str, dict[str, object]] = {}
    for key in active_keys:
        specification = registry[key]
        path = local_paths.get(key)
        record = asdict(specification)
        record["local_path"] = (
            path.relative_to(REPOSITORY_ROOT).as_posix()
            if path and path.exists()
            else None
        )
        record["local_sha256"] = sha256_file(path) if path and path.exists() else None
        expected_hash = specification.sha256 or specification.snapshot_sha256
        if record["local_sha256"] is None:
            record["integrity_status"] = "not-present"
        elif expected_hash is None:
            record["integrity_status"] = "hash-unpinned"
        elif record["local_sha256"].lower() == expected_hash.lower():
            record["integrity_status"] = "verified"
        else:
            record["integrity_status"] = "mismatch"
        records[key] = record
    return records


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--fixture", action="store_true")
    mode.add_argument("--real-data", action="store_true")
    args = parser.parse_args()
    reproduce(output_dir=args.output_dir, use_fixture=args.fixture)
