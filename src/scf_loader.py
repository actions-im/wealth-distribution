from __future__ import annotations

from pathlib import Path
from zipfile import ZipFile

import pandas as pd

from src.data_sources import SCF_2022_EXTRACT_ZIP_URL
from src.source_manifest import SourceSpec, download_artifact


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
