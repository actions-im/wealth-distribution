from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import UTC, datetime
import json
from pathlib import Path
import subprocess
import sys

import pandas as pd

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from wealth_report.model.assumptions import ModelAssumptions  # noqa: E402
from wealth_report.report.builder import (  # noqa: E402
    aggregate_ranked_resource_distributions,
    build_ranked_distributions,
    load_comprehensive_household_data,
)
from wealth_report.report.reconciliation import load_official_db_total, reconcile  # noqa: E402
from wealth_report.report.distribution import (  # noqa: E402
    build_age_distribution_shift_data,
    build_distribution_shift_data,
)
from wealth_report.providers.sources import load_source_registry, sha256_file  # noqa: E402


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


def _git_worktree_status() -> list[str]:
    """Record whether the export was produced from a clean, committed worktree."""
    result = subprocess.run(
        ["git", "status", "--porcelain"], capture_output=True, text=True, check=False
    )
    return result.stdout.splitlines() if result.returncode == 0 else []


def reproduce(*, output_dir: str | Path, use_fixture: bool = False) -> None:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    assumptions = ModelAssumptions()
    households = (
        _fixture_households()
        if use_fixture
        else load_comprehensive_household_data(assumptions)
    )
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

    official = load_official_db_total(year=2022)
    micro_db_total = float(
        (households["accrued_db_pension"] * households["household_weight"]).sum()
    )
    reconciliation = reconcile(micro_total=micro_db_total, official_total=official.value_dollars)
    pd.DataFrame([asdict(reconciliation)]).to_csv(
        output / "reconciliation.csv", index=False
    )
    registry = load_source_registry()
    worktree_status = _git_worktree_status()
    manifest = {
        "generated_at": datetime.now(UTC).isoformat(),
        "git_revision": _git_revision(),
        "git_worktree_dirty": bool(worktree_status),
        "git_worktree_status": worktree_status,
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
        "active_sources": _active_source_records(registry),
        "exclusions": [
            "unsupported Social Security spousal and survivor benefits",
            "reported SSI, disability, survivor/dependent, and unclassified payments are not used as retired-worker benefits",
            "DB survivor annuities without joint survival inputs",
            "DC balances already included in net worth",
        ],
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


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
        record["local_path"] = str(path) if path and path.exists() else None
        record["local_sha256"] = sha256_file(path) if path and path.exists() else None
        if record["local_sha256"] is None:
            record["integrity_status"] = "not-present"
        elif specification.sha256 is None:
            record["integrity_status"] = "hash-unpinned"
        elif record["local_sha256"].lower() == specification.sha256.lower():
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
