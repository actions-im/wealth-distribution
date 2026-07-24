from __future__ import annotations

from pathlib import Path

import pandas as pd

from wealth_report.providers.sources import load_source_registry, verify_artifact

DEFAULT_LIFE_TABLE = Path("data/reference/ssa_period_life_2019_tr2022.csv")


class LifeTableError(ValueError):
    pass


def _normalize_sex(value: object) -> str:
    normalized = str(value).strip().lower()
    aliases = {"m": "male", "male": "male", "f": "female", "female": "female"}
    if normalized not in aliases:
        raise LifeTableError(f"unsupported sex value: {value!r}")
    return aliases[normalized]


def load_life_table(path: str | Path, *, year: int) -> dict[str, dict[int, float]]:
    frame = pd.read_csv(path)
    required = {"year", "age", "sex", "lives"}
    missing = required - set(frame.columns)
    if missing:
        raise LifeTableError(f"life table is missing columns: {sorted(missing)}")

    frame = frame.loc[pd.to_numeric(frame["year"], errors="coerce") == year].copy()
    if frame.empty:
        raise LifeTableError(f"life table has no rows for year {year}")
    frame["sex"] = frame["sex"].map(_normalize_sex)
    frame["age"] = pd.to_numeric(frame["age"], errors="raise").astype(int)
    frame["lives"] = pd.to_numeric(frame["lives"], errors="raise").astype(float)
    if frame.duplicated(["sex", "age"]).any():
        raise LifeTableError("life table contains duplicate sex-age rows")
    if (frame["lives"] < 0).any():
        raise LifeTableError("life-table lives cannot be negative")

    return {
        sex: dict(zip(group["age"], group["lives"], strict=True))
        for sex, group in frame.groupby("sex", sort=False)
    }


def load_ssa_period_life_table(path: str | Path = DEFAULT_LIFE_TABLE) -> dict[str, dict[int, float]]:
    """Load the 2019 period table published with the 2022 Trustees Report."""
    resolved_path = Path(path)
    if resolved_path.resolve() == DEFAULT_LIFE_TABLE.resolve():
        specification = load_source_registry()["ssa_period_life_2019_tr2022"]
        verify_artifact(resolved_path, specification.snapshot_sha256)
    table = load_life_table(path, year=2019)
    expected_ages = set(range(120))
    if set(table) != {"male", "female"}:
        raise LifeTableError("bundled SSA table must contain male and female rows")
    for sex, rows in table.items():
        if set(rows) != expected_ages:
            raise LifeTableError(f"bundled SSA table has incomplete {sex} age coverage")
    return table
