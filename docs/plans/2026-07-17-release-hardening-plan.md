# Release hardening implementation plan

> **For Codex:** Execute the tasks test-first, one behavior at a time.

**Goal:** Correct the report's wage inputs and signed displays, remove inactive controls, classify current Social Security benefits, and make live results reproducible.

**Architecture:** Preserve the SCF-to-household pipeline and extend detailed inputs only where the codebook supplies required wage and benefit metadata. Keep methodology-sensitive policy choices out of this change.

**Tech stack:** Python 3.12, pandas, pytest, Streamlit, Plotly.

---

### Task 1: Correct documented SCF wage annualization

**Files:** `src/scf_detailed.py`, `tests/test_scf_detailed.py`.

Write failing tests for hourly, twice-monthly, weekly-with-weeks, and biweekly-with-weeks wage records. Load the hours and weeks fields and use them in wage annualization. Run focused then full tests.

### Task 2: Preserve Social Security benefit types

**Files:** `src/scf_detailed.py`, `src/social_security.py`, `src/real_data.py`, and their tests.

Write failing classification tests. Add benefit type to detailed person input, load `X5304/X5309`, and allow only reported retired-worker payments in the retired-worker valuation. Record non-retirement payments as explicit exclusions.

### Task 3: Render signed distributions truthfully

**Files:** `src/charts.py`, `app_pages/age_slicing.py`, and chart tests.

Write a failing test for a negative Bottom-50 share. Derive a signed x-axis range and label nonzero negative segments. Update page copy. Run focused and full tests.

### Task 4: Remove inactive UI and stale audit copy

**Files:** `src/ui.py`, `app_pages/methodology.py`, `src/provenance.py`, and tests.

Remove the unused liquidity control, replace hover claims with static-label language, and name Social Security/DB inputs in chart provenance.

### Task 5: Add a real-data reproducibility export

**Files:** `scripts/reproduce_report.py`, `app_pages/methodology.py`, `tests/test_reproduce_report.py`, and source-manifest helpers if needed.

Write a failing real-data export test using a patched loader. Add `--real-data` that emits actual headline/component/reconciliation files, assumptions, source hashes, and Git revision. Preserve fixture mode for fast contract tests. Run a real-data smoke export.

### Task 6: Recalculate and verify

Run the full suite, generate a real-data report, compare its output with the app loader, and inspect the running Streamlit process without restarting it.
