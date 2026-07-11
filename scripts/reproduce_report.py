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

from src.config import ModelAssumptions
from src.real_data import build_ranked_distributions
from src.reconciliation import load_official_db_total, reconcile
from src.source_manifest import load_source_registry


def _fixture_households() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "household_id": [1, 2, 3, 4, 5],
            "household_weight": [500, 400, 90, 9, 1],
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


def reproduce(*, output_dir: str | Path, use_fixture: bool = False) -> None:
    if not use_fixture:
        raise ValueError(
            "real-data reproduction requires the pinned SCF full dataset; use --fixture for CI"
        )
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    households = _fixture_households()
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
    pd.DataFrame(headline_rows).to_csv(output / "headline.csv", index=False)
    pd.DataFrame(detail_rows).to_csv(output / "detail.csv", index=False)
    pd.DataFrame(
        [
            {"scenario": "lower_discount", "discount_rate": 0.02},
            {"scenario": "baseline", "discount_rate": 0.035},
            {"scenario": "higher_discount", "discount_rate": 0.05},
        ]
    ).to_csv(output / "sensitivity.csv", index=False)

    official = load_official_db_total(year=2022)
    micro_db_total = float(
        (households["accrued_db_pension"] * households["household_weight"]).sum()
    )
    assumptions = ModelAssumptions()
    registry = load_source_registry()
    manifest = {
        "generated_at": datetime.now(UTC).isoformat(),
        "git_revision": _git_revision(),
        "fixture": True,
        "assumptions": asdict(assumptions),
        "measure_definitions": {
            "conventional": "SCF assets minus liabilities",
            "defensive_resources": "net worth plus defensive labor, accrued Social Security, and accrued DB pensions",
            "continuation_resources": "net worth plus continued labor, Social Security, and DB pension projections",
        },
        "ranking": "Each measure is ranked independently; rank_group uses weighted cumulative position.",
        "reconciliation": asdict(
            reconcile(micro_total=micro_db_total, official_total=official.value_dollars)
        ),
        "official_db_reference": asdict(official),
        "registered_sources": {key: asdict(value) for key, value in registry.items()},
        "exclusions": [
            "spousal and survivor Social Security benefits",
            "DB survivor annuities without joint survival inputs",
            "DC balances already included in net worth",
        ],
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--fixture", action="store_true")
    args = parser.parse_args()
    reproduce(output_dir=args.output_dir, use_fixture=args.fixture)
