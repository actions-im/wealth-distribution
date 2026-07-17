"""Load pinned SCF inputs and produce valued household tables."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd

from wealth_report.model.assumptions import ModelAssumptions
from wealth_report.model.statistics import weighted_median
from wealth_report.providers.scf.detailed import (
    PersonInput,
    build_detailed_household_input,
    load_detailed_scf,
)
from wealth_report.providers.scf.summary import (
    download_scf_extract,
    load_scf_extract,
    normalize_scf_rows,
)
from wealth_report.providers.sources import download_artifact, load_source_registry
from wealth_report.providers.ssa.mortality import load_ssa_period_life_table
from wealth_report.report.ranking import age_group
from wealth_report.report.valuation import (
    apply_inheritance_reallocation,
    value_detailed_household,
)


def build_reentry_wage_schedule(
    people: Iterable[tuple[PersonInput, float]],
    *,
    retirement_age: int,
) -> dict[tuple[str, str], float]:
    """Return SCF-weighted median positive wages by sex and respondent-age bucket."""
    rows = [
        {
            "sex": person.sex,
            "age_group": age_group(person.age),
            "annual_wage": person.annual_wage,
            "household_weight": weight,
        }
        for person, weight in people
        if person.age < retirement_age and person.annual_wage > 0 and weight > 0
    ]
    if not rows:
        return {}
    frame = pd.DataFrame(rows)
    schedule: dict[tuple[str, str], float] = {}
    for (sex, bucket), group in frame.groupby(["sex", "age_group"], sort=False):
        schedule[(str(sex), str(bucket))] = weighted_median(
            group["annual_wage"], group["household_weight"]
        )
    return schedule


def load_comprehensive_household_data(
    assumptions: ModelAssumptions,
    raw_dir: Path = Path("data/raw"),
) -> pd.DataFrame:
    """Load pinned SCF summary/full inputs and value all modeled components."""
    summary_path = raw_dir / "scf_2022_extract.zip"
    if not summary_path.exists():
        summary_path = download_scf_extract(raw_dir=raw_dir)
    full_path = raw_dir / "scf_2022_full.zip"
    if not full_path.exists():
        full_path, _ = download_artifact(load_source_registry()["scf_full"], raw_dir)

    summary = normalize_scf_rows(load_scf_extract(summary_path)).set_index("scf_row_id")
    detailed = load_detailed_scf(full_path)
    life_table = load_ssa_period_life_table()
    detailed_households = [
        build_detailed_household_input(values) for values in detailed.to_dict("records")
    ]
    reentry_people: list[tuple[PersonInput, float]] = []
    for household in detailed_households:
        if household.row_id not in summary.index:
            continue
        weight = float(summary.loc[household.row_id, "household_weight"])
        reentry_people.append((household.respondent, weight))
        if household.spouse is not None:
            reentry_people.append((household.spouse, weight))
    reentry_wage_schedule = build_reentry_wage_schedule(
        reentry_people, retirement_age=assumptions.retirement_age
    )
    rows: list[dict[str, object]] = []
    unmatched = 0
    for household in detailed_households:
        if household.row_id not in summary.index:
            unmatched += 1
            continue
        base = summary.loc[household.row_id]
        record = value_detailed_household(
            net_worth=base["traditional_net_worth"],
            household=household,
            life_table=life_table,
            assumptions=assumptions,
            reentry_wage_schedule=reentry_wage_schedule,
        )
        rows.append(
            {
                "household_id": household.row_id,
                "family_id": household.family_id,
                "implicate": household.implicate,
                "household_weight": float(base["household_weight"]),
                "age": household.respondent.age,
                "sex": household.respondent.sex,
                "expected_inheritance_amount": household.expected_inheritance_amount,
                "expects_sizable_estate": household.expects_sizable_estate,
                **record.__dict__,
                "exclusions": ";".join(record.exclusions),
            }
        )
    if unmatched:
        raise ValueError(f"{unmatched} detailed SCF rows did not match the summary extract")
    if not rows:
        raise ValueError("no comprehensive SCF household records were produced")
    return apply_inheritance_reallocation(
        pd.DataFrame(rows), life_table=life_table, assumptions=assumptions
    )
