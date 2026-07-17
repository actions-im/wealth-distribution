"""Performance and caching tests for the SCF valuation pipeline."""

from __future__ import annotations

import time

import pytest

from wealth_report.model.assumptions import ModelAssumptions
from wealth_report.report.pipeline import (
    clear_scf_household_bundle_cache,
    load_comprehensive_household_data,
    load_scf_household_bundle,
    value_scf_household_bundle,
)

RAW_DIR = "data/raw"

# Absolute ceilings leave headroom for shared CI runners; relative checks
# catch regressions even when machines are faster or slower.
MAX_WARM_PIPELINE_SECONDS = 8.0
MAX_CACHED_LOAD_SECONDS = 0.25
MIN_PARALLEL_SPEEDUP = 1.15


@pytest.fixture(scope="module")
def warm_bundle():
    clear_scf_household_bundle_cache()
    bundle = load_scf_household_bundle(RAW_DIR)
    assert len(bundle.prepared) > 20_000
    return bundle


def test_scf_bundle_cache_returns_same_object_and_is_fast(warm_bundle):
    first = warm_bundle
    start = time.perf_counter()
    second = load_scf_household_bundle(RAW_DIR)
    elapsed = time.perf_counter() - start

    assert second is first
    assert elapsed < MAX_CACHED_LOAD_SECONDS


def test_parallel_valuation_matches_serial_on_sample(warm_bundle):
    sample = type(warm_bundle)(
        prepared=warm_bundle.prepared[:400],
        life_table=warm_bundle.life_table,
    )
    assumptions = ModelAssumptions(discount_rate=0.04)
    serial = value_scf_household_bundle(sample, assumptions, workers=1)
    parallel = value_scf_household_bundle(sample, assumptions, workers=4)

    assert list(serial.columns) == list(parallel.columns)
    assert serial["household_id"].tolist() == parallel["household_id"].tolist()
    for column in (
        "continuation_resources",
        "defensive_resources",
        "continuation_labor",
        "continuation_social_security",
        "continuation_db_pension",
        "continuation_income_security_floor",
    ):
        assert serial[column].to_numpy() == pytest.approx(
            parallel[column].to_numpy(), rel=1e-9, abs=1e-6
        )


def test_warm_pipeline_revaluation_is_under_budget(warm_bundle):
    """Assumption changes should revalue without reloading SCF microdata."""
    # Ensure cache is warm.
    load_scf_household_bundle(RAW_DIR)
    assumptions = ModelAssumptions(discount_rate=0.0375, wage_growth=0.012)

    start = time.perf_counter()
    frame = load_comprehensive_household_data(assumptions, raw_dir=RAW_DIR)
    elapsed = time.perf_counter() - start

    assert len(frame) == len(warm_bundle.prepared)
    assert elapsed < MAX_WARM_PIPELINE_SECONDS


def test_parallel_workers_speed_up_full_valuation(warm_bundle):
    assumptions = ModelAssumptions()
    # Warm any one-time imports inside workers by doing a tiny parallel call first.
    tiny = type(warm_bundle)(
        prepared=warm_bundle.prepared[:80],
        life_table=warm_bundle.life_table,
    )
    value_scf_household_bundle(tiny, assumptions, workers=2)

    start = time.perf_counter()
    value_scf_household_bundle(warm_bundle, assumptions, workers=1)
    serial_seconds = time.perf_counter() - start

    start = time.perf_counter()
    value_scf_household_bundle(warm_bundle, assumptions, workers=4)
    parallel_seconds = time.perf_counter() - start

    speedup = serial_seconds / max(parallel_seconds, 1e-6)
    assert speedup >= MIN_PARALLEL_SPEEDUP, (
        f"expected parallel speedup >= {MIN_PARALLEL_SPEEDUP}, "
        f"got {speedup:.2f}x (serial={serial_seconds:.2f}s parallel={parallel_seconds:.2f}s)"
    )
