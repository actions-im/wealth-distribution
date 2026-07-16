# Distribution Shift Plot Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the home-page grouped chart with an auditable two-state four-group distribution-shift plot and add a public methodology page mapping every number to its sources and calculations.

**Architecture:** Add pure transformation and provenance helpers under `src/`, then build the Plotly figure from their tested outputs. Keep Streamlit pages thin: `Home.py` renders the shift figure and `pages/07_Methodology.py` renders calculation/source tables generated from the same live assumptions and distribution data.

**Tech Stack:** Python 3.12, pandas, Plotly graph objects, Streamlit, pytest, Streamlit AppTest.

---

### Task 1: Four-group distribution-shift transformation

**Files:**
- Modify: `src/reporting.py`
- Test: `tests/test_reporting.py`

**Step 1: Write failing aggregation tests**

Add tests proving that `build_distribution_shift_data()`:

```python
shift = build_distribution_shift_data(distribution)
assert shift["group"].unique().tolist() == ["Bottom 50%", "Next 40%", "Next 9%", "Top 1%"]
assert shift.groupby("state")["share"].sum().tolist() == pytest.approx([1, 1])
assert top_one_conventional["share"] == pytest.approx(
    conventional_99_999 + conventional_top_001
)
assert top_one_continuation["change_pp"] == pytest.approx(
    100 * (top_one_continuation["share"] - top_one_conventional["share"])
)
```

**Step 2: Run tests and verify RED**

Run: `uv run pytest tests/test_reporting.py -q`
Expected: FAIL because `build_distribution_shift_data` does not exist.

**Step 3: Implement the pure transformation**

Create a function that filters `conventional` and `continuation`, maps detailed quantiles to the four approved groups, sums shares/totals/household shares, orders categories, and attaches conventional share, continuation share, and signed percentage-point change to both state rows.

**Step 4: Run tests and verify GREEN**

Run: `uv run pytest tests/test_reporting.py -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/reporting.py tests/test_reporting.py
git commit -m "feat: aggregate two-state distribution shift"
```

### Task 2: Purpose-built shift figure

**Files:**
- Modify: `src/charts.py`
- Test: `tests/test_charts.py`

**Step 1: Write failing chart-contract tests**

Test that `distribution_shift_figure()` returns exactly eight stacked bar traces (four groups across two states), uses approved state/group labels, formats the x-axis as 0–100%, includes direct percentage labels, and contains four change annotations.

**Step 2: Run tests and verify RED**

Run: `uv run pytest tests/test_charts.py -q`
Expected: FAIL because the figure helper does not exist.

**Step 3: Implement the chart**

Use `plotly.graph_objects` to render two horizontal 100% stacked rows. Use stable colors:

```python
{
    "Bottom 50%": "#0F766E",
    "Next 40%": "#5FB3A9",
    "Next 9%": "#D6B56C",
    "Top 1%": "#B4533C",
}
```

Direct-label shares where space permits, show rich hover fields, place a compact four-column percentage-point change strip beneath the chart, remove visual clutter, and use accessible contrasting text.

**Step 4: Run tests and verify GREEN**

Run: `uv run pytest tests/test_charts.py -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/charts.py tests/test_charts.py
git commit -m "feat: visualize comprehensive resource shift"
```

### Task 3: Complete number-lineage and source registry

**Files:**
- Modify: `data/sources.json`
- Modify: `src/provenance.py`
- Test: `tests/test_provenance.py`
- Test: `tests/test_source_manifest.py`

**Step 1: Write failing provenance tests**

Require official source entries for SSA 2022 parameters, the 2022 Trustees scenario, and Federal Reserve DB pension entitlements. Require `build_shift_number_audit()` to emit one row for each state/group number with:

```python
{"Displayed number", "Value", "Unit", "Rank basis", "Formula", "Source fields", "Source keys", "Classification"}
```

Verify calculation rows cover all eight shares, four changes, and weighted totals.

**Step 2: Run tests and verify RED**

Run: `uv run pytest tests/test_provenance.py tests/test_source_manifest.py -q`
Expected: FAIL on missing registry keys and audit helper.

**Step 3: Implement the audit model**

Add canonical official URLs/vintages to the registry. Build dynamic audit rows from the actual shift data and assumptions. Add separate component-formula rows for labor, Social Security, DB pensions, discounting, survival, ranking, and double-count prevention. Never describe model-derived values as official statistics.

**Step 4: Run tests and verify GREEN**

Run: `uv run pytest tests/test_provenance.py tests/test_source_manifest.py -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add data/sources.json src/provenance.py tests/test_provenance.py tests/test_source_manifest.py
git commit -m "docs: trace every chart number to sources"
```

### Task 4: Home-page integration

**Files:**
- Modify: `Home.py`
- Modify: `tests/test_streamlit_app.py`

**Step 1: Write failing AppTest assertions**

Require the new title, exactly two state labels, all four group labels, “All modeled future resources” wording, no old grouped-chart axis title, and no Streamlit exceptions.

**Step 2: Run test and verify RED**

Run: `uv run pytest tests/test_streamlit_app.py -q`
Expected: FAIL because the current grouped five-quantile chart remains.

**Step 3: Integrate the shift figure**

Replace the existing `px.bar` block with the tested transformation and chart helper. Add one sentence enumerating included future labor earnings, Social Security, and DB pensions. Retain assumptions, source caption, lifecycle warning, and detailed page link.

**Step 4: Run test and verify GREEN**

Run: `uv run pytest tests/test_streamlit_app.py -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add Home.py tests/test_streamlit_app.py
git commit -m "feat: showcase the resource distribution shift"
```

### Task 5: Dedicated methodology page

**Files:**
- Create: `pages/07_Methodology.py`
- Modify: `pages/06_Source_Data.py`
- Test: `tests/test_methodology_page.py`

**Step 1: Write failing methodology-page tests**

Use `AppTest` to require sections for measure definitions, every displayed number, formulas, assumptions, double-count protection, exclusions, limitations, and official sources. Assert source URLs render as link columns and no exception occurs.

**Step 2: Run test and verify RED**

Run: `uv run pytest tests/test_methodology_page.py -q`
Expected: FAIL because the page does not exist.

**Step 3: Implement the page**

Load the same live scenario data as Home, derive the same shift table, and render:

- live chart-number audit table;
- component formula table;
- current assumption table;
- official source registry with clickable URLs;
- explicit DC double-count guard and unsupported-benefit exclusions;
- concise links to `docs/methodology.md` and the source registry.

Update Source Data copy so it no longer claims only the legacy summary extract drives the charts.

**Step 4: Run test and verify GREEN**

Run: `uv run pytest tests/test_methodology_page.py -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add pages/07_Methodology.py pages/06_Source_Data.py tests/test_methodology_page.py
git commit -m "feat: add auditable methodology page"
```

### Task 6: Visual and full verification

**Files:**
- Modify as needed based on visual review.

**Step 1: Run automated verification**

```bash
uv run pytest -q
uvx ruff check Home.py pages src scripts tests
uv run python -m compileall -q Home.py pages src scripts tests
git diff --check
```

Expected: all commands exit 0.

**Step 2: Inspect the running app**

Refresh `http://localhost:8501`, verify desktop layout, direct labels, change strip, hover text, methodology navigation, and absence of clipping or console errors.

**Step 3: Apply only evidence-backed polish**

Adjust spacing, label contrast, height, or annotation placement if the visual inspection exposes a concrete issue. Do not change calculated values.

**Step 4: Re-run affected tests**

Run the full verification commands again and verify a clean worktree except intentional changes.

**Step 5: Commit**

```bash
git add Home.py pages src tests
git commit -m "style: polish distribution shift report"
```
