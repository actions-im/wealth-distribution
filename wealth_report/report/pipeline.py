"""Load pinned SCF inputs and produce valued household tables."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from functools import lru_cache
import logging
import math
import multiprocessing as mp
import os
from pathlib import Path
from typing import Iterable, Sequence

import pandas as pd

from wealth_report.model.assumptions import ModelAssumptions
from wealth_report.model.statistics import weighted_median
from wealth_report.providers.scf.detailed import (
    DetailedHouseholdInput,
    PersonInput,
    build_detailed_household_input,
    load_detailed_scf,
)
from wealth_report.providers.scf.summary import (
    download_scf_extract,
    load_scf_extract,
    normalize_scf_rows,
)
from wealth_report.providers.sources import (
    download_artifact,
    load_source_registry,
    verify_artifact,
)
from wealth_report.providers.ssa.mortality import load_ssa_period_life_table
from wealth_report.report.ranking import age_group
from wealth_report.report.valuation import (
    apply_inheritance_reallocation,
    value_detailed_household,
)

logger = logging.getLogger(__name__)
DEFAULT_MAX_WORKERS = 2


@dataclass(frozen=True)
class PreparedHousehold:
    """SCF microdata row joined to summary net worth and weight."""

    household: DetailedHouseholdInput
    net_worth: float
    household_weight: float


@dataclass(frozen=True)
class ScfHouseholdBundle:
    """Assumption-independent SCF inputs ready for repeated valuation."""

    prepared: tuple[PreparedHousehold, ...]
    life_table: dict[str, dict[int, float]]


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


def load_scf_household_bundle(raw_dir: str | Path = "data/raw") -> ScfHouseholdBundle:
    """Load and join SCF summary/full files once per process (cached)."""
    resolved = str(Path(raw_dir).expanduser().resolve())
    return _load_scf_household_bundle_cached(resolved)


@lru_cache(maxsize=4)
def _load_scf_household_bundle_cached(raw_dir: str) -> ScfHouseholdBundle:
    root = Path(raw_dir)
    summary_path = root / "scf_2022_extract.zip"
    if not summary_path.exists():
        summary_path = download_scf_extract(raw_dir=root)
    full_path = root / "scf_2022_full.zip"
    if not full_path.exists():
        full_path, _ = download_artifact(load_source_registry()["scf_full"], root)

    registry = load_source_registry()
    verify_artifact(summary_path, registry["scf_summary"].sha256)
    verify_artifact(full_path, registry["scf_full"].sha256)

    summary = normalize_scf_rows(load_scf_extract(summary_path)).set_index("scf_row_id")
    detailed = load_detailed_scf(full_path)
    life_table = load_ssa_period_life_table()

    prepared: list[PreparedHousehold] = []
    unmatched = 0
    for values in detailed.to_dict("records"):
        household = build_detailed_household_input(values)
        if household.row_id not in summary.index:
            unmatched += 1
            continue
        base = summary.loc[household.row_id]
        prepared.append(
            PreparedHousehold(
                household=household,
                net_worth=float(base["traditional_net_worth"]),
                household_weight=float(base["household_weight"]),
            )
        )
    if unmatched:
        raise ValueError(f"{unmatched} detailed SCF rows did not match the summary extract")
    if not prepared:
        raise ValueError("no comprehensive SCF household records were produced")
    return ScfHouseholdBundle(prepared=tuple(prepared), life_table=life_table)


def clear_scf_household_bundle_cache() -> None:
    """Drop the process-level SCF load cache (tests / reload)."""
    _load_scf_household_bundle_cached.cache_clear()


def load_comprehensive_household_data(
    assumptions: ModelAssumptions,
    raw_dir: Path | str = Path("data/raw"),
    *,
    workers: int | None = None,
) -> pd.DataFrame:
    """Load pinned SCF inputs and value all modeled components.

    SCF microdata load/join is cached per process. Household valuation is
    parallelized across CPU cores when ``workers`` is greater than 1.
    """
    bundle = load_scf_household_bundle(raw_dir)
    return value_scf_household_bundle(
        bundle,
        assumptions,
        workers=workers,
    )


def value_scf_household_bundle(
    bundle: ScfHouseholdBundle,
    assumptions: ModelAssumptions,
    *,
    workers: int | None = None,
) -> pd.DataFrame:
    """Value a prepared SCF bundle under the given assumptions."""
    reentry_people: list[tuple[PersonInput, float]] = []
    for item in bundle.prepared:
        reentry_people.append((item.household.respondent, item.household_weight))
        if item.household.spouse is not None:
            reentry_people.append((item.household.spouse, item.household_weight))
    reentry_wage_schedule = build_reentry_wage_schedule(
        reentry_people, retirement_age=assumptions.retirement_age
    )
    worker_count = _resolve_workers(workers, household_count=len(bundle.prepared))
    rows = _value_prepared_parallel(
        bundle.prepared,
        life_table=bundle.life_table,
        assumptions=assumptions,
        reentry_wage_schedule=reentry_wage_schedule,
        workers=worker_count,
    )
    if not rows:
        raise ValueError("no comprehensive SCF household records were produced")
    return apply_inheritance_reallocation(
        pd.DataFrame(rows),
        life_table=bundle.life_table,
        assumptions=assumptions,
    )


def _resolve_workers(workers: int | None, *, household_count: int) -> int:
    if workers is not None:
        return max(1, int(workers))
    # Keep the interactive default within the publication host's two-core ceiling.
    # Explicit worker counts remain available for larger development and CI hosts.
    cpu = os.cpu_count() or 2
    return max(
        1,
        min(
            cpu - 1 if cpu > 2 else cpu,
            DEFAULT_MAX_WORKERS,
            household_count,
        ),
    )


def _value_prepared_parallel(
    prepared: Sequence[PreparedHousehold],
    *,
    life_table: dict[str, dict[int, float]],
    assumptions: ModelAssumptions,
    reentry_wage_schedule: dict[tuple[str, str], float],
    workers: int,
) -> list[dict[str, object]]:
    """Value households in-process or across a process pool."""
    if workers <= 1 or len(prepared) < 64:
        survival_cache: dict[tuple[str, int], list[float]] = {}
        return [
            _row_from_prepared(
                item,
                life_table=life_table,
                assumptions=assumptions,
                reentry_wage_schedule=reentry_wage_schedule,
                survival_cache=survival_cache,
            )
            for item in prepared
        ]

    chunks = _split_chunks(list(prepared), workers)
    payloads = [
        (chunk, life_table, assumptions, reentry_wage_schedule)
        for chunk in chunks
        if chunk
    ]
    # Spawn is required for Streamlit/AppTest safety (fork after threads is risky).
    # Page modules must not call main() in non-MainProcess workers.
    context = mp.get_context("spawn")
    rows: list[dict[str, object]] = []
    try:
        with ProcessPoolExecutor(max_workers=workers, mp_context=context) as pool:
            for chunk_rows in pool.map(_value_prepared_chunk, payloads, chunksize=1):
                rows.extend(chunk_rows)
    except PermissionError:
        logger.warning("process pool unavailable; falling back to serial valuation")
        return _value_prepared_chunk(
            (
                list(prepared),
                life_table,
                assumptions,
                reentry_wage_schedule,
            )
        )
    return rows


def _split_chunks(
    items: list[PreparedHousehold], workers: int
) -> list[list[PreparedHousehold]]:
    if not items:
        return []
    chunk_count = min(workers, len(items))
    chunk_size = int(math.ceil(len(items) / chunk_count))
    return [items[index : index + chunk_size] for index in range(0, len(items), chunk_size)]


def _value_prepared_chunk(
    payload: tuple[
        list[PreparedHousehold],
        dict[str, dict[int, float]],
        ModelAssumptions,
        dict[tuple[str, str], float],
    ],
) -> list[dict[str, object]]:
    prepared, life_table, assumptions, reentry_wage_schedule = payload
    survival_cache: dict[tuple[str, int], list[float]] = {}
    return [
        _row_from_prepared(
            item,
            life_table=life_table,
            assumptions=assumptions,
            reentry_wage_schedule=reentry_wage_schedule,
            survival_cache=survival_cache,
        )
        for item in prepared
    ]


def _row_from_prepared(
    item: PreparedHousehold,
    *,
    life_table: dict[str, dict[int, float]],
    assumptions: ModelAssumptions,
    reentry_wage_schedule: dict[tuple[str, str], float],
    survival_cache: dict[tuple[str, int], list[float]],
) -> dict[str, object]:
    household = item.household
    record = value_detailed_household(
        net_worth=item.net_worth,
        household=household,
        life_table=life_table,
        assumptions=assumptions,
        reentry_wage_schedule=reentry_wage_schedule,
        survival_cache=survival_cache,
    )
    return {
        "household_id": household.row_id,
        "family_id": household.family_id,
        "implicate": household.implicate,
        "household_weight": item.household_weight,
        "age": household.respondent.age,
        "sex": household.respondent.sex,
        "expected_inheritance_amount": household.expected_inheritance_amount,
        "expects_sizable_estate": household.expects_sizable_estate,
        **record.__dict__,
        "exclusions": ";".join(record.exclusions),
    }
