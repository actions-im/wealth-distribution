# Inheritance Reallocation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a conservative, nationally conserved expected-inheritance reallocation to continuation resources while leaving conventional net worth unchanged.

**Architecture:** Load SCF inheritance expectations and estate-intent answers into household records. A pure allocator discounts reported recipient claims, derives mortality-weighted donor capacity, and writes equal weighted credits and reserves subject to a funding cap. Apply its two components only after all SCF families are loaded, then disclose their sources and limitations in the report.

**Tech Stack:** Python 3.12, pandas, Streamlit, pytest, Ruff; Federal Reserve 2022 SCF full and summary files; existing SSA life-table loader.

---

### Task 1: Add the scenario control

**Files:**
- Modify: src/config.py lines 21-66
- Modify: src/ui.py lines 60-98
- Modify: src/app_data.py lines 34-54
- Modify: Home.py
- Modify: pages/07_Methodology.py
- Modify: pages/08_Age_Distribution_Shift.py
- Test: tests/test_real_data.py
- Test: tests/test_streamlit_app.py

**Step 1: Write the failing test**

Add a test that a 15-year inheritance horizon is accepted and values outside 5 through 30 raise a ValueError naming inheritance_horizon_years.

~~~python
def test_inheritance_horizon_is_validated():
    assert ModelAssumptions(inheritance_horizon_years=15).inheritance_horizon_years == 15
    with pytest.raises(ValueError, match="inheritance_horizon_years"):
        ModelAssumptions(inheritance_horizon_years=4)
~~~

**Step 2: Run it to verify it fails**

Run: uv run pytest tests/test_real_data.py::test_inheritance_horizon_is_validated -v

Expected: FAIL because the assumption does not yet exist.

**Step 3: Implement the minimum control**

Add inheritance_horizon_years: int = 15 to DEFAULT_ASSUMPTIONS and ModelAssumptions; validate it as an integer from 5 to 30. Add a sidebar slider labeled Expected inheritance horizon (years) with the same range and help text stating it is a timing scenario, not observed parent-child timing. Thread the value through load_comprehensive_report_data and all page callers so it participates in the cache key.

**Step 4: Run focused tests**

Run: uv run pytest tests/test_real_data.py::test_inheritance_horizon_is_validated tests/test_streamlit_app.py -v

Expected: PASS.

**Step 5: Commit**

~~~bash
git add src/config.py src/ui.py src/app_data.py Home.py pages/07_Methodology.py pages/08_Age_Distribution_Shift.py tests/test_real_data.py tests/test_streamlit_app.py
git commit -m "feat: add inheritance horizon scenario control"
~~~

### Task 2: Load the observed inheritance responses

**Files:**
- Modify: src/scf_detailed.py lines 22-110
- Test: tests/test_scf_detailed.py

**Step 1: Write the failing tests**

Extend the detailed-SCF fixture with x5819, x5821, and x5825. Test that X5819 = 1 plus a positive amount yields expected_inheritance_amount, while a non-affirmative response yields zero. Test that only direct X5825 = 1 yields expects_sizable_estate=True.

**Step 2: Run them to verify they fail**

Run: uv run pytest tests/test_scf_detailed.py -k inheritance -v

Expected: FAIL because the fields are neither loaded nor represented.

**Step 3: Implement the minimum extraction**

Add x5819, x5821, and x5825 to DETAILED_COLUMNS. Extend DetailedHouseholdInput:

~~~python
expected_inheritance_amount: float
expects_sizable_estate: bool
~~~

In build_detailed_household_input, retain a positive amount only when X5819 == 1; set the donor flag only when X5825 == 1. Treat missing, possibly, no, zero, past inheritances, trusts, and gifts as no current future-inheritance input.

**Step 4: Run focused tests**

Run: uv run pytest tests/test_scf_detailed.py -v

Expected: PASS.

**Step 5: Commit**

~~~bash
git add src/scf_detailed.py tests/test_scf_detailed.py
git commit -m "feat: load reported inheritance expectations"
~~~

### Task 3: Implement a pure conservation-safe allocator

**Files:**
- Create: src/inheritance.py
- Test: tests/test_inheritance.py

**Step 1: Write failing unit tests**

Write tests for a discounted claim helper and a dataframe allocator:

~~~python
def discounted_inheritance_claim(amount: float, years: int, discount_rate: float) -> float: ...

def allocate_inheritance_reallocation(
    households: pd.DataFrame,
    *,
    life_table: dict[str, dict[int, float]],
    horizon_years: int,
    discount_rate: float,
) -> tuple[pd.DataFrame, InheritanceDiagnostics]: ...
~~~

Cover:

- $1,000 in ten years at 10% equals 1000 / 1.1**10.
- Weighted credits equal weighted reserves when capacity exists.
- An otherwise identical donor with greater mortality gets a larger reserve.
- A reserve never exceeds positive net worth or mortality-weighted capacity.
- Zero capacity produces no credit and an explicit unallocated claim.
- Claims larger than capacity are pro-rated.
- Negative wealth, no affirmative estate intent, or missing donor sex/age make no donor capacity or reserve; invalid inheritance amounts make no recipient claim or credit. Recipient sex and age are not required because timing uses the global scenario horizon.

**Step 2: Run them to verify they fail**

Run: uv run pytest tests/test_inheritance.py -v

Expected: FAIL because the module does not exist.

**Step 3: Implement the minimum allocator**

Create immutable diagnostics:

~~~python
@dataclass(frozen=True)
class InheritanceDiagnostics:
    reported_claim_total: float
    discounted_claim_total: float
    donor_capacity_total: float
    reallocated_total: float
    unallocated_claim_total: float
    funding_ratio: float
~~~

Validate finite amounts and weights, a positive integer horizon, and a valid real discount factor. Copy the input frame and add inheritance_claim, inheritance_credit, estate_donor_capacity, estate_donor_reserve, and inheritance_reallocation.

For a recipient, calculate amount / (1 + rate) ** horizon. For an eligible donor, calculate max(net_worth, 0) times P(death within horizon | respondent age, sex), using conditional_survival from src.actuarial.

With C as weighted claims and D as weighted capacity:

~~~python
reallocated = min(C, D)
recipient_scale = reallocated / C if C else 0.0
donor_scale = reallocated / D if D else 0.0
~~~

Credit each recipient claim times recipient_scale; reserve each donor capacity times donor_scale; store their difference as inheritance_reallocation. Do not rescale net worth, create future asset yields, or model taxes, medical spending, gifts, charity, or unobserved heirs.

**Step 4: Run focused tests**

Run: uv run pytest tests/test_inheritance.py -v

Expected: PASS.

**Step 5: Commit**

~~~bash
git add src/inheritance.py tests/test_inheritance.py
git commit -m "feat: allocate expected inheritances conservatively"
~~~

### Task 4: Integrate the components into comprehensive resources

**Files:**
- Modify: src/real_data.py lines 55-305 and 426-484
- Test: tests/test_real_data.py

**Step 1: Write failing integration tests**

Build a small recipient/donor dataframe test around apply_inheritance_reallocation. Assert that the weighted credit equals the weighted reserve and that net_worth remains unchanged. Also assert continuation_resources includes the positive credit and negative reserve, while defensive resources do not.

~~~python
credits = (data.continuation_expected_inheritance * data.household_weight).sum()
reserves = (data.continuation_estate_donor_reserve * data.household_weight).sum()
assert credits == pytest.approx(reserves)
assert data.net_worth.equals(original_net_worth)
~~~

**Step 2: Run it to verify it fails**

Run: uv run pytest tests/test_real_data.py -k inheritance -v

Expected: FAIL because the record has no inheritance components.

**Step 3: Implement the minimum integration**

Extend ComprehensiveHouseholdInput and ComprehensiveHouseholdRecord:

~~~python
continuation_expected_inheritance: float = 0.0
continuation_estate_donor_reserve: float = 0.0
~~~

Add credit and subtract reserve in continuation_resources; leave defensive_resources unchanged. When loading detailed records, retain the raw expected amount, estate flag, respondent age, sex, and weight. After all families are valued, call the pure allocator once with the existing life table and model assumptions; write its results to the two named columns and recompute continuation_resources. Keep conventional net_worth untouched.

Expose diagnostics through an explicit function or stable dataframe metadata only if Streamlit caching preserves it; do not rely on implicit global state.

**Step 4: Run focused tests**

Run: uv run pytest tests/test_real_data.py -v

Expected: PASS.

**Step 5: Commit**

~~~bash
git add src/real_data.py tests/test_real_data.py
git commit -m "feat: integrate inheritance reallocation into resources"
~~~

### Task 5: Add provenance and limitations

**Files:**
- Modify: src/provenance.py
- Modify: pages/07_Methodology.py
- Modify: docs/methodology.md
- Modify: README.md
- Test: tests/test_provenance.py
- Test: tests/test_methodology_page.py

**Step 1: Write failing disclosure tests**

Require a methodology-table component named Expected inheritance reallocation that lists X5819, X5821, X5825, SSA mortality, the active horizon, and the absence of parent-child links. Require visible methodology-page text including constrained aggregate reallocation and not a legal claim.

**Step 2: Run them to verify they fail**

Run: uv run pytest tests/test_provenance.py tests/test_methodology_page.py -v

Expected: FAIL because the component is not disclosed.

**Step 3: Implement the minimum disclosure**

Add the claim, donor-capacity, and funding-cap formulas to provenance and audit tables. Add plain-language limitations:

- credits and reserves conserve the modeled national total;
- public SCF does not link recipients to donors;
- the measure is neither a legal claim nor present ownership;
- estate taxes, care costs, consumption, gifts, charity, siblings, and unobserved heirs are excluded;
- conventional net worth remains unchanged; and
- no future return is added to an inherited asset already valued on the donor balance sheet.

Add the same limits to README and docs/methodology.md.

**Step 4: Run focused tests**

Run: uv run pytest tests/test_provenance.py tests/test_methodology_page.py -v

Expected: PASS.

**Step 5: Commit**

~~~bash
git add src/provenance.py pages/07_Methodology.py docs/methodology.md README.md tests/test_provenance.py tests/test_methodology_page.py
git commit -m "docs: disclose inheritance reallocation methodology"
~~~

### Task 6: Surface the reallocation without changing the conventional chart

**Files:**
- Modify: Home.py
- Modify: pages/08_Age_Distribution_Shift.py
- Modify: src/reporting.py
- Test: tests/test_streamlit_app.py
- Test: tests/test_reporting.py

**Step 1: Write failing report tests**

Require home and age-page copy to call inheritance a reallocation, not added wealth. Add a report-level assertion that the weighted net of the two inheritance components is zero to tolerance.

**Step 2: Run them to verify they fail**

Run: uv run pytest tests/test_streamlit_app.py tests/test_reporting.py -v

Expected: FAIL until the report copy and audit contract are updated.

**Step 3: Implement the minimum report changes**

Update explanatory copy on Home and the age-shift page. Add credit, reserve, and net reallocation to an existing component or audit table if one already presents components; do not create a new chart solely for this one component. Keep the conventional chart exactly as it is.

**Step 4: Run focused tests**

Run: uv run pytest tests/test_streamlit_app.py tests/test_reporting.py -v

Expected: PASS.

**Step 5: Commit**

~~~bash
git add Home.py pages/08_Age_Distribution_Shift.py src/reporting.py tests/test_streamlit_app.py tests/test_reporting.py
git commit -m "feat: disclose inheritance reallocation in report"
~~~

### Task 7: Verify the full feature and its live pages

**Files:**
- Verify only unless a failure identifies a defect.

**Step 1: Run the complete test suite**

Run: uv run pytest -q

Expected: all tests pass.

**Step 2: Run static and syntax checks**

Run: uv run ruff check .
Expected: All checks passed!

Run: python3 -m compileall -q Home.py src pages tests
Expected: exit code 0.

Run: git diff --check
Expected: exit code 0.

**Step 3: Perform Streamlit smoke checks**

Run the application on an unused local port. Verify Home, Methodology, and Age_Distribution_Shift render without exceptions; confirm the horizon control, constrained-reallocation disclosure, and all charts are present.

**Step 4: Commit only final corrections, if any**

~~~bash
git add <only-files-fixed-during-verification>
git commit -m "fix: finalize inheritance reallocation report"
~~~
