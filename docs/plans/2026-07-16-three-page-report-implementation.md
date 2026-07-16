# Three-page public report implementation plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Expose only Home, Age slicing, and Methodology in the public Streamlit report, while making Methodology the complete audit surface for national and age-sliced values, calculations, assumptions, and official sources.

**Architecture:** Replace automatic discovery of pages/ with root-level explicit st.navigation and three direct scripts in app_pages/. Reuse the existing data loading, calculation, conservation-validation, chart, and provenance helpers. Extend provenance with an age-slicing audit built from the same live age-shift data, then render that audit on Methodology.

**Tech Stack:** Python 3.12, Streamlit, pandas, Plotly, pytest with Streamlit AppTest, Ruff.

---

### Task 1: Lock down the three-page public surface

**Files:**
- Modify: tests/test_streamlit_app.py
- Create: app_pages/__init__.py
- Create: app_pages/home.py
- Create: app_pages/age_slicing.py
- Create: app_pages/methodology.py
- Modify: Home.py
- Delete: pages/02_Wealth_by_Quantile.py
- Delete: pages/03_Wealth_by_Age.py
- Delete: pages/04_Age_Quantile_Matrix.py
- Delete: pages/05_Assumptions_Lab.py
- Delete: pages/06_Source_Data.py
- Delete: pages/07_Methodology.py
- Delete: pages/08_Age_Distribution_Shift.py

**Step 1: Write the failing navigation and page-rendering tests**

Replace paths in the remaining AppTest cases with app_pages/home.py, app_pages/age_slicing.py, and app_pages/methodology.py. Remove the obsolete quantile-page test. Add an exact public-surface test that reads Home.py and asserts:
- st.navigation is present;
- source.count("st.Page(") == 3;
- the exact pages are app_pages/home.py titled Home, app_pages/age_slicing.py titled Age slicing, and app_pages/methodology.py titled Methodology;
- pathlib.Path("pages").exists() is false.

Keep the conservation parametrization, but point it to exactly these three scripts.

**Step 2: Run test to verify it fails**

Run: uv run pytest tests/test_streamlit_app.py::test_explicit_public_navigation_has_only_three_pages -q

Expected: FAIL because Home.py does not use explicit navigation and app_pages/ does not exist.

**Step 3: Implement the minimum explicit routing and page migration**

Create app_pages/home.py by moving the current report body from Home.py, excluding st.set_page_config. Create app_pages/age_slicing.py from the current age-distribution body and app_pages/methodology.py from the current methodology body, likewise excluding each page-level configuration call. Add a minimal app_pages/__init__.py.

Replace root Home.py with:
- one st.set_page_config call using wide layout and a collapsed sidebar;
- st.navigation with exactly three st.Page definitions:
  - st.Page("app_pages/home.py", title="Home", icon=":material/home:")
  - st.Page("app_pages/age_slicing.py", title="Age slicing", icon=":material/stacks:")
  - st.Page("app_pages/methodology.py", title="Methodology", icon=":material/menu_book:")
- position="top";
- page.run().

Update the Home methodology link to app_pages/methodology.py. Delete every legacy script in pages/; do not leave a directory that Streamlit can auto-discover.

**Step 4: Run test to verify it passes**

Run: uv run pytest tests/test_streamlit_app.py -q

Expected: PASS, including the Home and Age slicing rendering tests and the unconserved-inheritance guard for all three public pages.

**Step 5: Commit**

Run: git add Home.py app_pages tests/test_streamlit_app.py pages
Run: git commit -m "feat: reduce report to three public pages"

### Task 2: Audit every visible age-slicing number

**Files:**
- Modify: tests/test_provenance.py
- Modify: src/provenance.py
- Modify: app_pages/methodology.py

**Step 1: Write the failing age-audit provenance test**

Import build_age_shift_number_audit. Build a six-age-bucket fixture by copying _shift_data() once per bucket and setting age_group, weighted_family_count, and all_resources_total. Assert:
- the audit has one Age bucket column covering all six AGE_SHIFT_BUCKETS;
- six rows have Displayed number equal to Weighted SCF family count;
- six rows have Displayed number equal to All modeled resources total;
- every Formula, Source fields, Source keys, and Classification value is nonempty;
- every age-panel plot share, weighted total, household share, and percentage-point change receives the existing audit lineage.

**Step 2: Run test to verify it fails**

Run: uv run pytest tests/test_provenance.py::test_age_shift_number_audit_covers_chart_and_panel_summary_values -q

Expected: FAIL because build_age_shift_number_audit is not defined.

**Step 3: Implement the pure age-slicing audit helper**

Add build_age_shift_number_audit(age_shift_data, assumptions) to src/provenance.py. Validate that age_group and all columns required by build_shift_number_audit exist. For each nonempty age bucket:
1. Call build_shift_number_audit on its rows so every bar value and percentage-point comparison receives the established formulas and source lineage.
2. Insert Age bucket and Report view = Age slicing into those rows.
3. Add exactly one Weighted SCF family count row. Its value is the live weighted_family_count; its unit is weighted SCF families; its formula is sum(SCF WGT for SCF families in this respondent-age bucket); its source fields are Summary SCF rscfp2022.dta: AGE, WGT; its source key is scf_summary.
4. Add exactly one All modeled resources total row. Its value is the live all_resources_total; its unit is 2022 dollars; its formula is sum(continuation_resources × SCF WGT for this respondent-age bucket); its source lineage is the existing comprehensive-resource lineage.

Never recalculate or hard-code a displayed value; trace the output of build_age_distribution_shift_data.

In app_pages/methodology.py, compute age_shift_data with build_age_distribution_shift_data(data), then display this audit under a new Age slicing number audit section. Use a formatter that renders weighted-family counts in millions and totals in trillions. Keep the existing Home audit, label it Home distribution audit, and add Report view = Home to distinguish the two tables.

**Step 4: Run tests to verify it passes**

Run: uv run pytest tests/test_provenance.py tests/test_methodology_page.py -q

Expected: PASS. The page-surface expectations will be expanded in Task 3.

**Step 5: Commit**

Run: git add src/provenance.py app_pages/methodology.py tests/test_provenance.py
Run: git commit -m "feat: audit age slicing calculations"

### Task 3: Make Methodology the complete public calculation and source audit

**Files:**
- Modify: tests/test_methodology_page.py
- Modify: app_pages/methodology.py
- Modify: docs/methodology.md
- Modify: src/ui.py
- Modify: README.md

**Step 1: Write the failing Methodology-surface tests**

Update the page path to app_pages/methodology.py. Require these headings:
- Scope, weighting, and ranking
- Measure definitions
- Home distribution audit
- Age slicing number audit
- Component formulas
- Current assumptions
- Inheritance conservation
- Double-count protection
- Exclusions and limitations
- Official sources
- Reproduction

Assert visible copy includes SCF family, 2022 dollars, WGT, ranked independently, min(claims, capacity), weighted credits, weighted donor reserves, and point estimates. Keep inheritance source-lineage assertions and the clickable-source-column assertion.

**Step 2: Run test to verify it fails**

Run: uv run pytest tests/test_methodology_page.py -q

Expected: FAIL because the page lacks the required scope, age-audit, conservation, and reproduction sections.

**Step 3: Implement the Methodology additions and remove stale public references**

Add Scope, weighting, and ranking before measure definitions. State that SCF family is the unit, values are 2022 dollars, WGT produces weighted national totals, and conventional/full-resource states are separately ranked.

Add Age slicing number audit from Task 2. Add Inheritance conservation as a distinct section that explains sum(WGT × recipient credit) = sum(WGT × donor reserve) within the reported floating-point tolerance and the funding cap min(weighted claims, weighted capacity). Add Reproduction with: uv run python scripts/reproduce_report.py --fixture --output-dir build/report. State that the fixture validates code paths and the Streamlit report loads pinned real SCF inputs for point estimates.

Update docs/methodology.md with the three-view public structure and identical audit/reproduction language. Update src/ui.py from See the Source Data page for links. to See Methodology for source links. Update README's audit-trail source-page reference to Methodology page and replace validation paths from pages to app_pages.

**Step 4: Run tests to verify it passes**

Run: uv run pytest tests/test_methodology_page.py tests/test_provenance.py -q

Expected: PASS.

**Step 5: Commit**

Run: git add app_pages/methodology.py docs/methodology.md src/ui.py README.md tests/test_methodology_page.py
Run: git commit -m "docs: make methodology the report audit"

### Task 4: Verify the reduced public report end to end

**Files:**
- Modify: none expected

**Step 1: Run the complete automated suite**

Run: uv run pytest -q

Expected: PASS with no skipped legacy-page tests or stale-route failures.

**Step 2: Run static checks**

Run: uv run ruff check .
Run: python3 -m compileall -q Home.py app_pages src scripts tests
Run: git diff --check

Expected: all commands exit zero.

**Step 3: Run the app and inspect each public route**

Run: uv run streamlit run Home.py --server.port 8502 --server.headless true

Open:
- http://localhost:8502/
- http://localhost:8502/Age_slicing
- http://localhost:8502/Methodology

Verify top navigation contains exactly Home, Age slicing, and Methodology; Home and Age slicing retain their inheritance conservation text; and Methodology displays source URLs, component formulas, Home audit, age-slicing audit, assumptions, and conservation explanation.

**Step 4: Commit verification-only fixes if needed**

If verification uncovers a defect, return to a new failing test before changing production code. Otherwise, no additional commit is required.

