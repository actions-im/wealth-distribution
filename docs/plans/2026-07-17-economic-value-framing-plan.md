# Economic-value framing implementation plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make the Home and Methodology pages state the report's claim plainly: conventional net worth is a valid ownership-balance-sheet measure but is incomplete when used as a measure of the distribution of total economic value.

**Architecture:** Keep the calculation, chart, and ranking logic unchanged. Replace only public explanatory copy, but protect the claim with Streamlit page tests that require the two-estimand distinction, the five modeled components, and the exact description of the SCF public files and their weighting.

**Tech Stack:** Python, Streamlit, pandas, pytest with `streamlit.testing.v1`.

---

### Task 1: Lock the public thesis and data basis in page tests

**Files:**
- Modify: `tests/test_streamlit_app.py`
- Modify: `tests/test_methodology_page.py`

**Step 1: Write failing tests**

Assert that the Home page names the asymmetry between capitalized asset values and omitted non-balance-sheet cash flows, names labor, Social Security, defined-benefit pensions, the income-security scenario, and inheritance, and identifies the 2022 SCF public files as 4,595 families across five implicates (22,975 rows) weighted with `WGT`.

Assert that Methodology distinguishes the current-ownership balance sheet from the broader economic-resources estimand and repeats the survey data basis.

**Step 2: Run the focused tests and verify failure**

Run: `uv run pytest -q tests/test_streamlit_app.py tests/test_methodology_page.py`

Expected: failure because the present page copy does not state the required thesis and survey detail.

### Task 2: Replace the Home-page opening and chart context

**Files:**
- Modify: `app_pages/home.py`

**Step 1: Implement the copy**

Replace the generic opening with a concise three-part explanation:

1. Define conventional net worth as a valid current-ownership accounting measure, but not a complete population measure of economic value.
2. Explain the asymmetric treatment: market values of capital assets embed expectations of future cash flows, risk, and discounting; expected labor, retirement, and transfer streams are otherwise omitted rather than valued under explicit assumptions.
3. Name every modeled component and the 2022 SCF survey basis. State that the resulting comparison is not a claim that the components share legal status, liquidity, or transferability.

Do not call the model a national balance sheet, a complete accounting replacement, or a proof of a normative conclusion.

**Step 2: Run the Home test and verify it passes**

Run: `uv run pytest -q tests/test_streamlit_app.py::test_home_uses_two_state_distribution_shift`

Expected: PASS.

### Task 3: Add the explicit two-estimand explanation and data basis to Methodology

**Files:**
- Modify: `app_pages/methodology.py`

**Step 1: Implement the explanation**

Add a section before “Scope, weighting, and ranking” that states the research question and separates:

- conventional net worth (currently owned assets minus liabilities); and
- all modeled future resources (a broader, explicit estimate of lifetime economic resources).

Add a data-basis paragraph describing the SCF summary and detailed public files, 4,595 SCF family interviews, five implicates / 22,975 record rows, `WGT` weighting, and the SSA/Financial Accounts supplemental inputs. Explain that the survey represents weighted families rather than persons.

**Step 2: Run the Methodology test and verify it passes**

Run: `uv run pytest -q tests/test_methodology_page.py`

Expected: PASS.

### Task 4: Run full verification and inspect the live pages

**Files:**
- Verify: `app_pages/home.py`
- Verify: `app_pages/methodology.py`

**Step 1: Run static and automated checks**

Run:

```bash
uv run pytest -q
uv run ruff check Home.py app_pages src scripts tests
uv run python -m compileall -q Home.py app_pages src scripts tests
```

Expected: all commands exit successfully.

**Step 2: Check the active Streamlit server**

If a Streamlit app is listening on a local 850* port, tell the user to refresh it; do not restart it without a request.
