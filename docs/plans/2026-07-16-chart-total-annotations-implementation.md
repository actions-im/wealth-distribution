# Chart Total Annotations Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Show each conventional and all-modeled-resources segment's weighted total in trillions directly beside its percentage in every distribution-shift annotation.

**Architecture:** Keep percentage bars, source data, tooltip payloads, and rankings unchanged. Extend the shared Plotly annotation string in distribution_shift_figure so Home and all Age slicing panels inherit the identical display format.

**Tech Stack:** Python 3.12, pandas, Plotly, pytest.

---

### Task 1: Add bracketed weighted totals to shared distribution annotations

**Files:**
- Modify: tests/test_charts.py
- Modify: src/charts.py

**Step 1: Write the failing test**

In test_distribution_shift_figure, preserve the current assertions and add assertions that the rendered annotation text contains both conventional and modeled totals in one-decimal trillions. With the existing fixture, assert the Bottom 50 annotation contains:
- 2.0% [$0.0T]
- 10.0% [$0.1T]
- +8.0 pp

Use the fixture's actual weighted_total values rather than adding a chart-only data path.

**Step 2: Run test to verify it fails**

Run: uv run pytest tests/test_charts.py::test_distribution_shift_figure_uses_share_labels_and_pp_changes -q

Expected: FAIL because annotations currently contain percentages and percentage-point changes but no bracketed trillion totals.

**Step 3: Implement the minimum shared formatter**

In src/charts.py, retrieve the conventional and all-modeled-resources rows for each group from the existing changes table. Format their current weighted_total values as dollar trillions with one decimal. Update only the existing annotation text to render:

Bottom 50%
2.0% [$0.0T] → 10.0% [$0.1T]
+8.0 pp

Do not alter trace x-values, customdata, hovertemplate, colors, rank logic, or data loading. Increase the annotation margin only if screenshot verification proves clipping.

**Step 4: Run test to verify it passes**

Run: uv run pytest tests/test_charts.py -q

Expected: PASS.

**Step 5: Commit**

Run: git add src/charts.py tests/test_charts.py
Run: git commit -m "feat: show chart totals in annotations"

### Task 2: Verify both report surfaces

**Files:**
- Modify: none expected

**Step 1: Run complete verification**

Run: uv run pytest -q
Run: uv run ruff check .
Run: python3 -m compileall -q Home.py app_pages src scripts tests
Run: git diff --check

Expected: all commands exit zero.

**Step 2: Check the live report**

Open Home and Age slicing on the existing local server. Confirm every bottom annotation follows percentage [$trillions] → percentage [$trillions], retains the percentage-point change, and is not clipped.

