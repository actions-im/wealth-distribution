from pathlib import Path

import pandas as pd
import pytest

from wealth_report.providers.ssa.mortality import LifeTableError, load_life_table, load_ssa_period_life_table


def test_load_life_table_selects_vintage_and_normalizes_sex(tmp_path):
    path = tmp_path / "life.csv"
    pd.DataFrame(
        [
            {"year": 2021, "age": 40, "sex": "M", "lives": 90_000},
            {"year": 2022, "age": 40, "sex": "M", "lives": 89_000},
            {"year": 2022, "age": 41, "sex": "F", "lives": 91_000},
        ]
    ).to_csv(path, index=False)

    table = load_life_table(path, year=2022)

    assert table == {"male": {40: 89_000.0}, "female": {41: 91_000.0}}


def test_load_life_table_rejects_duplicate_age_sex_rows(tmp_path):
    path = tmp_path / "life.csv"
    pd.DataFrame(
        [
            {"year": 2022, "age": 40, "sex": "male", "lives": 90_000},
            {"year": 2022, "age": 40, "sex": "male", "lives": 89_000},
        ]
    ).to_csv(path, index=False)

    with pytest.raises(LifeTableError, match="duplicate"):
        load_life_table(path, year=2022)


def test_bundled_ssa_table_has_full_age_coverage_and_source_note():
    table = load_ssa_period_life_table()

    assert set(table) == {"male", "female"}
    assert set(table["male"]) == set(range(120))
    assert set(table["female"]) == set(range(120))
    assert Path("data/reference/ssa_period_life_2019_tr2022.csv.source.txt").is_file()


def test_bundled_ssa_snapshot_is_verified_before_parse(monkeypatch):
    import wealth_report.providers.ssa.mortality as mortality

    calls = []
    monkeypatch.setattr(
        mortality,
        "verify_artifact",
        lambda path, digest: calls.append((path, digest)),
        raising=False,
    )

    load_ssa_period_life_table()

    assert calls
    assert calls[0][1]
