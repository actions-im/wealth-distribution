# Total Country Distribution Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Show national total wealth shares by quantile under marketable net worth, human capital, and combined real wealth.

**Architecture:** Extend the sample data model with age and wealth-quantile population shares, then aggregate per-household values into national totals and shares. Reuse existing Streamlit pages and Plotly helpers rather than adding new framework code.

**Tech Stack:** Python, pandas, Plotly, Streamlit, pytest.

---

### Task 1: Aggregate Share Tests

**Files:**
- Modify: `tests/test_data_schema.py`
- Modify: `src/sample_data.py`

**Steps:**
1. Write failing tests for quantile population shares summing to 1, share columns summing to 1, and top 1% combined share being lower than top 1% traditional share.
2. Run `uv run pytest tests/test_data_schema.py -q` and verify failure.
3. Implement national total/share aggregation.
4. Run `uv run pytest tests/test_data_schema.py -q`.

### Task 2: Charts and Pages

**Files:**
- Modify: `src/charts.py`
- Modify: `Home.py`
- Modify: `pages/02_Wealth_by_Quantile.py`

**Steps:**
1. Add a grouped percentage-share bar chart helper.
2. Make the home page lead with total country distribution.
3. Update executive summary and quantile page tables/charts to show national shares.
4. Run `uv run python -m compileall -q Home.py src pages tests`.

### Task 3: Verification

**Files:**
- Modify: `README.md`

**Steps:**
1. Update README to explain total-share framing.
2. Run `uv run pytest -q`.
3. Run a Streamlit HTTP check.
