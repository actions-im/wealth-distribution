from __future__ import annotations

from pathlib import Path
from zipfile import ZipFile

import pandas as pd
import requests

from src.data_sources import FED_DFA_ZIP_URL


def download_fed_dfa(raw_dir: Path = Path("data/raw"), url: str = FED_DFA_ZIP_URL) -> Path:
    raw_dir.mkdir(parents=True, exist_ok=True)
    destination = raw_dir / "fed_dfa.zip"
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    destination.write_bytes(response.content)
    return destination


def extract_fed_dfa(zip_path: Path, processed_dir: Path = Path("data/processed")) -> Path:
    processed_dir.mkdir(parents=True, exist_ok=True)
    with ZipFile(zip_path) as archive:
        csv_names = [name for name in archive.namelist() if name.lower().endswith(".csv")]
        if not csv_names:
            raise ValueError("Fed DFA ZIP did not contain a CSV file")
        with archive.open(csv_names[0]) as csv_file:
            data = pd.read_csv(csv_file)

    data.columns = [column.strip().lower().replace(" ", "_") for column in data.columns]
    output = processed_dir / "fed_dfa.parquet"
    data.to_parquet(output, index=False)
    return output

