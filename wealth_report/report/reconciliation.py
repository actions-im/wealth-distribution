from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from wealth_report.providers.sources import load_source_registry, verify_artifact

DEFAULT_DB_REFERENCE = Path("data/reference/fed_z1_defined_benefit_2022.csv")


@dataclass(frozen=True)
class OfficialPensionTotal:
    year: int
    series_code: str
    description: str
    value_dollars: float
    release_url: str


@dataclass(frozen=True)
class ReconciliationResult:
    micro_total: float
    official_total: float
    difference: float
    ratio: float
    adjusted_micro_total: float


def load_official_db_total(
    *, year: int, path: str | Path = DEFAULT_DB_REFERENCE
) -> OfficialPensionTotal:
    resolved_path = Path(path)
    if resolved_path.resolve() == DEFAULT_DB_REFERENCE.resolve():
        specification = load_source_registry()["fed_z1_db_pensions"]
        verify_artifact(resolved_path, specification.snapshot_sha256)
    data = pd.read_csv(path)
    row = data.loc[data["year"] == year]
    if len(row) != 1:
        raise ValueError(f"expected one official DB total for {year}, found {len(row)}")
    item = row.iloc[0]
    if item["unit"] != "billions of dollars end of period":
        raise ValueError("unsupported official pension unit")
    return OfficialPensionTotal(
        year=int(item["year"]),
        series_code=str(item["series_code"]),
        description=str(item["description"]),
        value_dollars=float(item["value_billions"]) * 1e9,
        release_url=str(item["release_url"]),
    )


def reconcile(*, micro_total: float, official_total: float) -> ReconciliationResult:
    if official_total <= 0:
        raise ValueError("official_total must be positive")
    difference = float(micro_total - official_total)
    return ReconciliationResult(
        micro_total=float(micro_total),
        official_total=float(official_total),
        difference=difference,
        ratio=float(micro_total / official_total),
        adjusted_micro_total=float(micro_total),
    )
