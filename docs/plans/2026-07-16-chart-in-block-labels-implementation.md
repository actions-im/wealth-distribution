# Chart In-Block Labels Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace distribution-chart bottom adjustment annotations and hover tooltips with visible in-block percentage-and-total labels.

**Architecture:** Keep the shared Plotly stacked-bar geometry and source values unchanged. Format each label from the existing share and weighted_total values when the segment clears the existing 5.5% legibility threshold; remove chart annotations and disable hover at the trace level.

**Tech Stack:** Python 3.12, pandas, Plotly, pytest.

---

### Task 1: Render static share-and-total labels inside chart segments

**Files:**
- Modify: tests/test_charts.py
- Modify: src/charts.py

**Step 1: Write the failing test**

Replace the lower-annotation assertions with the direct static-label contract:
- the Bottom 50 trace for All modeled future resources has text exactly 10.0% [$0.1T] under the fixture;
- the Bottom 50 trace for Conventional net worth has an empty text label because its 2.0% segment is below the legibility threshold;
- all traces have hoverinfo equal to skip;
- figure.layout.annotations is empty.

Retain the tests for two states, four groups, stacked percentage geometry, and trace count.

**Step 2: Run test to verify it fails**

Run: uv run pytest tests/test_charts.py -q

Expected: FAIL because the current chart uses percentage-only trace labels, has hover templates, and still has four bottom annotations.

**Step 3: Implement the minimum shared display change**

In distribution_shift_figure:
- format eligible trace text as f"{share:.1%} [{dollars_trillions(weighted_total)}]";
- retain the existing 5.5% threshold and centered in-bar position;
- remove customdata and hovertemplate;
- set hoverinfo="skip" for every bar trace;
- remove the totals pivot and the four lower annotations;
- reduce the unused bottom layout margin after annotations are removed.

Do not change data requirements, trace ordering, colors, rank calculations, or legend behavior.

**Step 4: Run test to verify it passes**

Run: uv run pytest tests/test_charts.py -q

Expected: PASS.

**Step 5: Commit**

Run: git add src/charts.py tests/test_charts.py
Run: git commit -m "feat: simplify distribution chart labels"

### Task 2: Verify the shared chart in the public report

**Files:**
- Modify: none expected

**Step 1: Run complete verification**

Run: uv run pytest -q
Run: uv run ruff check .
Run: python3 -m compileall -q Home.py app_pages src scripts tests
Run: git diff --check

Expected: all commands exit zero.

**Step 2: Inspect the restarted local app**

Restart the Streamlit server on port 8502, inspect Home and Age slicing, and verify:
- no bottom adjustment strip;
- no hover interaction;
- visible eligible labels follow percentage [$trillions];
- smaller segments have no overlaid label rather than unreadable overflow.

