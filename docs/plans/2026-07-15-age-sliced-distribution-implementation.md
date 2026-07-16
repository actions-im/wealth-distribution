# Age-sliced distribution implementation plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a Streamlit page that shows conventional and comprehensive-resource distribution shifts within six respondent-age buckets.

**Architecture:** Add a reporting helper that filters comprehensive SCF family data by the existing age buckets, independently ranks each measure within each bucket, and converts the result to the existing four-group, two-state chart shape. Reuse the existing Plotly shift chart for every bordered age panel and load the same cached comprehensive data already used by the homepage and Methodology page.

**Tech Stack:** Python 3.12, pandas, Plotly, Streamlit, pytest.

---

### Task 1: Add age-bucket distribution aggregation

**Files:**

- Modify: `src/reporting.py`
- Test: `tests/test_reporting.py`

**Steps:**

1. Write a failing test calling `build_age_distribution_shift_data(data)` with a small weighted fixture spanning two age buckets. Assert two states, four display groups, and shares summing to one for every state.
2. Run `uv run pytest tests/test_reporting.py -q`; expect failure because the helper does not exist.
3. Implement the helper. Require age, household ID, weight, net worth, and continuation resources; derive existing age labels; independently aggregate each non-empty bucket with the existing ranked-resource function; convert through `build_distribution_shift_data`; append bucket context.
4. Re-run `uv run pytest tests/test_reporting.py -q`; expect pass.
5. Commit the aggregation and test with `feat: aggregate distribution shifts by age`.

### Task 2: Add the age-sliced Streamlit page

**Files:**

- Create: `pages/08_Age_Distribution_Shift.py`
- Modify: `tests/test_streamlit_app.py`

**Steps:**

1. Write a failing AppTest for the new page: title, within-age ranking note, six age headings, and six Plotly charts.
2. Run `uv run pytest tests/test_streamlit_app.py -q`; expect failure because the page does not exist.
3. Create the page as a direct Streamlit script. Load existing sidebar assumptions and cached comprehensive data; display the family/respondent-age and independent-ranking notes; render the six age buckets in a two-column grid using bordered containers; render the existing shift chart and a caption with weighted family count and all-resource total.
4. Re-run `uv run pytest tests/test_streamlit_app.py -q`; expect pass.
5. Commit the page and test with `feat: add age-sliced distribution page`.

### Task 3: Verify the full report

**Files:**

- Verify only

**Steps:**

1. Run `uv run pytest -q`, `uv run ruff check .`, `python3 -m compileall -q Home.py src pages tests`, and `git diff --check`; expect all to exit zero.
2. Open the local Streamlit page and confirm all six panels are readable, labels are unambiguous, and no panel is clipped.
3. Commit the design and implementation documents with `docs: design age-sliced distribution view`.
