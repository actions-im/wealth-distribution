from __future__ import annotations

from pathlib import Path
from zipfile import ZipFile

import pandas as pd

from wealth_report.providers.sources import (
    SCF_2022_EXTRACT_ZIP_URL,
    SourceSpec,
    download_artifact,
)


def download_scf_extract(raw_dir: Path = Path("data/raw"), url: str = SCF_2022_EXTRACT_ZIP_URL) -> Path:
    spec = SourceSpec(
        key="scf_summary",
        provider="Federal Reserve Board",
        url=url,
        vintage="2022 public summary extract",
        filename="scf_2022_extract.zip",
        sha256=(
            "3bb4d890ae2463ff6039ec7692e375f544dd98a55a37ca2cb2340354b9cc9d80"
            if url == SCF_2022_EXTRACT_ZIP_URL
            else None
        ),
        archive_member="rscfp2022.dta",
    )
    destination, _record = download_artifact(spec, raw_dir, timeout=60)
    return destination


def load_scf_extract(zip_path: Path) -> pd.DataFrame:
    with ZipFile(zip_path) as archive:
        names = archive.namelist()
        csv_names = [name for name in names if name.lower().endswith(".csv")]
        if csv_names:
            with archive.open(csv_names[0]) as csv_file:
                return _normalize_scf_columns(pd.read_csv(csv_file))

        stata_names = [name for name in names if name.lower().endswith(".dta")]
        if stata_names:
            with archive.open(stata_names[0]) as stata_file:
                return _normalize_scf_columns(pd.read_stata(stata_file))

    raise ValueError("SCF extract ZIP did not contain a supported CSV or Stata file")


def _normalize_scf_columns(data: pd.DataFrame) -> pd.DataFrame:
    normalized = data.copy()
    normalized.columns = [column.strip().lower() for column in normalized.columns]
    return normalized


def normalize_scf_rows(scf_rows: pd.DataFrame) -> pd.DataFrame:
    """Normalize the active SCF summary fields needed by the report builder."""
    data = _normalize_scf_columns(scf_rows)
    required_columns = {"wgt", "networth"}
    missing_columns = required_columns - set(data.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"SCF rows are missing required columns: {missing}")

    if "scf_row_id" not in data.columns:
        data["scf_row_id"] = data["y1"] if "y1" in data.columns else range(1, len(data) + 1)
    if "family_id" not in data.columns:
        data["family_id"] = data["yy1"] if "yy1" in data.columns else data["scf_row_id"]
    if "implicate" not in data.columns:
        data["implicate"] = (
            pd.to_numeric(data["y1"], errors="coerce") % 10
            if "y1" in data.columns
            else 1
        )

    normalized = pd.DataFrame(
        {
            "scf_row_id": data["scf_row_id"],
            "family_id": pd.to_numeric(data["family_id"], errors="coerce"),
            "implicate": pd.to_numeric(data["implicate"], errors="coerce"),
            "household_weight": pd.to_numeric(data["wgt"], errors="coerce"),
            "traditional_net_worth": pd.to_numeric(data["networth"], errors="coerce"),
        }
    ).dropna(subset=["household_weight", "traditional_net_worth"])
    normalized = normalized[normalized["household_weight"] > 0].copy()
    if normalized.empty:
        raise ValueError("SCF rows did not contain any valid positive-weight households")
    return normalized
