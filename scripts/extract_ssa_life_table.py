"""Convert SSA's published Markdown life table into the normalized project snapshot."""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path


ROW = re.compile(
    r"^\|\s*(\d+)\s*\|\s*([0-9.]+)\s*\|\s*([0-9,]+)\s*\|\s*([0-9.]+)\s*"
    r"\|\s*([0-9.]+)\s*\|\s*([0-9,]+)\s*\|\s*([0-9.]+)\s*\|$"
)


def extract(source: Path, output: Path) -> None:
    rows: list[dict[str, object]] = []
    for line in source.read_text().splitlines():
        match = ROW.match(line)
        if not match:
            continue
        age, male_qx, male_lives, male_expectancy, female_qx, female_lives, female_expectancy = match.groups()
        for sex, qx, lives, expectancy in (
            ("male", male_qx, male_lives, male_expectancy),
            ("female", female_qx, female_lives, female_expectancy),
        ):
            rows.append(
                {
                    "year": 2019,
                    "age": int(age),
                    "sex": sex,
                    "death_probability": qx,
                    "lives": lives.replace(",", ""),
                    "life_expectancy": expectancy,
                }
            )
    if len(rows) != 240:
        raise ValueError(f"expected 240 sex-age rows, found {len(rows)}")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0])
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    extract(args.source, args.output)
