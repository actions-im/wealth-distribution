from __future__ import annotations

from pathlib import Path
from zipfile import ZipFile

import pandas as pd
import requests

from src.data_sources import SCF_2022_EXTRACT_ZIP_URL


def download_scf_extract(raw_dir: Path = Path("data/raw"), url: str = SCF_2022_EXTRACT_ZIP_URL) -> Path:
    raw_dir.mkdir(parents=True, exist_ok=True)
    destination = raw_dir / "scf_2022_extract.zip"
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    destination.write_bytes(response.content)
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

