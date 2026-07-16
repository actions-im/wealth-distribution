# Income-security floor implementation plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Value a transparent, scenario-based income-security floor and SCF-calibrated re-entry wages in the comprehensive-resource distribution.

**Architecture:** Add reusable annual cash-flow helpers for projected labor, Social Security, DB pensions, and a floor top-up. Extend the detailed-SCF valuator with a weighted peer wage schedule and an income-floor component, then include it in continuation resources. Expose the monthly floor benchmark in the Streamlit sidebar and the methodology/provenance audit.

**Tech Stack:** Python 3.12, pandas, Streamlit, Plotly, pytest, Federal Reserve 2022 SCF, SSA 2022 SSI statistics.

---

### Task 1: Add floor cash-flow primitives

**Files:**

- Create: `src/income_security.py`
- Test: `tests/test_income_security.py`

**Steps:**

1. Write failing tests for individual/couple annual benchmarks, zero top-up above the benchmark, and survival-discounted top-up below it.
2. Run `uv run pytest tests/test_income_security.py -q`; expect an import failure.
3. Implement the annual benchmark, top-up stream, and present-value helper with input validation.
4. Re-run the focused test; expect pass.
5. Commit with `feat: value income-security floor`.

### Task 2: Add SCF-calibrated re-entry wages and annual income streams

**Files:**

- Modify: `src/human_capital.py`
- Modify: `src/social_security.py`
- Modify: `src/pensions.py`
- Modify: `src/real_data.py`
- Test: `tests/test_human_capital.py`
- Test: `tests/test_real_data.py`

**Steps:**

1. Write failing tests showing that an SCF peer wage schedule gives a non-retired zero-wage person positive, probability-weighted continuation labor, while a retiree remains at zero labor.
2. Run the focused tests; expect failure.
3. Add stream helpers that reproduce the current present-value calculations for labor, Social Security cash benefits, and DB pension payments. Build weighted median positive-wage reference cells by sex and age bucket from SCF detailed rows and summary weights.
4. Re-run the focused tests; expect pass.
5. Commit with `feat: impute conservative re-entry wage streams`.

### Task 3: Assemble the non-duplicative floor in comprehensive resources

**Files:**

- Modify: `src/config.py`
- Modify: `src/real_data.py`
- Test: `tests/test_real_data.py`

**Steps:**

1. Write failing tests proving continuation resources equal net worth plus labor, Social Security, DB pension, and the floor component; prove a high-income stream receives no floor top-up.
2. Run the focused test; expect failure.
3. Add `income_security_floor_monthly` to `ModelAssumptions`; build combined annual household income streams; value the floor; retain the component on each household record.
4. Re-run focused tests; expect pass.
5. Commit with `feat: include income-security floor in resources`.

### Task 4: Update the public report and provenance

**Files:**

- Modify: `src/ui.py`
- Modify: `src/provenance.py`
- Modify: `pages/07_Methodology.py`
- Modify: `Home.py`
- Modify: `pages/08_Age_Distribution_Shift.py`
- Modify: `README.md`
- Modify: `data/sources.json`
- Test: `tests/test_provenance.py`
- Test: `tests/test_streamlit_app.py`

**Steps:**

1. Write failing tests for the new source/audit component and visible income-security-floor explanation.
2. Run focused tests; expect failure.
3. Add the $0–$841 monthly benchmark sidebar control, source record, methodology formula, component audit, and clear scenario language on the public pages.
4. Re-run focused tests; expect pass.
5. Commit with `feat: disclose income-security floor scenario`.

### Task 5: Verify and inspect the report

**Files:**

- Verify only

**Steps:**

1. Run `uv run pytest -q`, `uv run ruff check .`, `python3 -m compileall -q Home.py src pages tests`, and `git diff --check`; expect all commands to exit zero.
2. Launch the worktree Streamlit app, inspect the Home, Methodology, and Age Distribution Shift pages, and confirm the $0/$622/$841 sensitivity is visible and source-backed.
3. Commit the design and implementation documents with `docs: design income-security floor methodology`.
