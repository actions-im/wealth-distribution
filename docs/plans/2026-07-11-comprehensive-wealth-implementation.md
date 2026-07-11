# Comprehensive Household Resources Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the stylized wage-only “full wealth” report with reproducible conventional, defensive accrued, and continuation household-resource measures that add survival-adjusted labor earnings, Social Security, and defined-benefit pensions without double counting.

**Architecture:** Keep the Streamlit pages thin and move source acquisition, actuarial primitives, benefit models, SCF normalization, uncertainty, and reporting into tested `src/` modules. Raw official artifacts remain untracked; a committed source registry and generated manifest make every calculation reproducible. Each distribution is ranked under its own metric, while fixed-conventional-rank tables remain available as explicitly labeled decompositions.

**Tech Stack:** Python 3.12, pandas, NumPy, requests, Streamlit, Plotly, pytest, uv, Federal Reserve SCF/Financial Accounts data, SSA actuarial data.

---

### Task 1: Release metadata and neutral terminology

**Files:**
- Create: `LICENSE`
- Create: `CITATION.cff`
- Create: `CONTRIBUTING.md`
- Create: `SECURITY.md`
- Create: `CODE_OF_CONDUCT.md`
- Modify: `pyproject.toml`
- Modify: `README.md`
- Test: `tests/test_release_metadata.py`

**Step 1: Write the failing metadata test**

```python
from pathlib import Path


def test_open_source_release_files_exist():
    for name in ["LICENSE", "CITATION.cff", "CONTRIBUTING.md", "SECURITY.md", "CODE_OF_CONDUCT.md"]:
        assert Path(name).is_file()


def test_readme_uses_neutral_measure_names():
    readme = Path("README.md").read_text()
    assert "modeled comprehensive resources" in readme.lower()
    assert "the trick" not in readme.lower()
```

**Step 2: Run the test and verify RED**

Run: `uv run pytest tests/test_release_metadata.py -q`
Expected: FAIL because release files do not exist and terminology is unchanged.

**Step 3: Add minimal release files and metadata**

Use Apache-2.0, add package license/authors/repository metadata, and rewrite README definitions without changing calculations yet.

**Step 4: Run the test and verify GREEN**

Run: `uv run pytest tests/test_release_metadata.py -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add LICENSE CITATION.cff CONTRIBUTING.md SECURITY.md CODE_OF_CONDUCT.md pyproject.toml README.md tests/test_release_metadata.py
git commit -m "docs: prepare project for open source release"
```

### Task 2: Versioned official-source registry and manifest

**Files:**
- Create: `data/sources.json`
- Create: `src/source_manifest.py`
- Modify: `src/data_sources.py`
- Modify: `src/scf_loader.py`
- Test: `tests/test_source_manifest.py`

**Step 1: Write failing tests for registered sources and integrity**

```python
def test_registry_contains_required_official_sources(source_registry):
    assert {"scf_summary", "scf_full", "scf_replicate_weights", "ssa_life_male", "ssa_life_female"} <= set(source_registry)


def test_verify_download_rejects_wrong_hash(tmp_path):
    path = tmp_path / "source.bin"
    path.write_bytes(b"wrong")
    with pytest.raises(SourceIntegrityError):
        verify_artifact(path, expected_sha256="0" * 64)
```

**Step 2: Verify RED**

Run: `uv run pytest tests/test_source_manifest.py -q`
Expected: FAIL because registry/manifest APIs do not exist.

**Step 3: Implement registry, atomic downloads, and generated manifest**

Implement `SourceSpec`, SHA-256 verification, exact archive-member selection, streamed temporary downloads followed by atomic rename, and manifest fields for URL, vintage, retrieval time, bytes, ETag, Last-Modified, hash, and Git revision.

**Step 4: Verify GREEN**

Run: `uv run pytest tests/test_source_manifest.py -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add data/sources.json src/source_manifest.py src/data_sources.py src/scf_loader.py tests/test_source_manifest.py
git commit -m "feat: add verified official source manifests"
```

### Task 3: Preserve SCF implicates and detailed household inputs

**Files:**
- Create: `src/scf_detailed.py`
- Modify: `src/real_data.py`
- Test: `tests/test_scf_detailed.py`

**Step 1: Write failing normalization tests**

```python
def test_normalization_preserves_family_and_implicate_ids():
    data = normalize_scf_rows(pd.DataFrame([{"y1": 12341, "yy1": 1234, "wgt": 2, "age": 40, "wageinc": 10, "networth": 20}]))
    assert data.loc[0, "family_id"] == 1234
    assert data.loc[0, "implicate"] == 1


def test_household_inputs_keep_respondent_and_spouse_separate():
    household = build_detailed_household_input(detailed_fixture())
    assert household.respondent.age != household.spouse.age
```

**Step 2: Verify RED**

Run: `uv run pytest tests/test_scf_detailed.py -q`
Expected: FAIL because IDs and person-level input types do not exist.

**Step 3: Implement detailed SCF mapping**

Preserve `Y1`/`YY1`; map respondent/spouse age, sex, work status, wage inputs, Social Security receipts, DB plan type, expected/current benefit flows, claiming ages, and survivor information where available. Record field-level exclusions when detailed inputs are absent.

**Step 4: Verify GREEN**

Run: `uv run pytest tests/test_scf_detailed.py -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/scf_detailed.py src/real_data.py tests/test_scf_detailed.py
git commit -m "feat: preserve SCF implicates and person inputs"
```

### Task 4: Actuarial survival and present-value primitives

**Files:**
- Create: `src/actuarial.py`
- Create: `src/ssa_loader.py`
- Test: `tests/test_actuarial.py`
- Test: `tests/test_ssa_loader.py`

**Step 1: Write failing actuarial tests**

```python
def test_future_payment_starts_one_period_ahead():
    assert present_value_stream([100], discount_rate=0.05) == pytest.approx(100 / 1.05)


def test_survival_curve_is_conditional_on_current_age():
    curve = conditional_survival({40: 90_000, 41: 89_000, 42: 88_000}, current_age=40)
    assert curve == pytest.approx([1.0, 89 / 90, 88 / 90])
```

**Step 2: Verify RED**

Run: `uv run pytest tests/test_actuarial.py tests/test_ssa_loader.py -q`
Expected: FAIL because modules do not exist.

**Step 3: Implement loaders and primitives**

Load SSA male/female projected period-life-table CSVs, select survey-year mortality, build conditional survival curves, and implement finite survival-weighted real present values with validated rates and ages.

**Step 4: Verify GREEN**

Run: `uv run pytest tests/test_actuarial.py tests/test_ssa_loader.py -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/actuarial.py src/ssa_loader.py tests/test_actuarial.py tests/test_ssa_loader.py
git commit -m "feat: add SSA survival and actuarial primitives"
```

### Task 5: Defensive and continuation labor wealth

**Files:**
- Rewrite: `src/human_capital.py`
- Modify: `src/config.py`
- Test: `tests/test_human_capital.py`

**Step 1: Write failing person-level earnings tests**

```python
def test_non_earner_can_reenter_employment():
    value = estimate_labor_wealth(current_income=0, reentry_income=40_000, reentry_probability=0.25, age=30, retirement_age=67, survival=[1] * 38)
    assert value > 0


def test_household_labor_wealth_sums_people_after_separate_projection():
    result = estimate_household_labor_wealth(respondent=person(age=64), spouse=person(age=40))
    assert result.total == pytest.approx(result.respondent + result.spouse)
```

**Step 2: Verify RED**

Run: `uv run pytest tests/test_human_capital.py -q`
Expected: FAIL on the new APIs.

**Step 3: Implement minimal defensive and continuation models**

Project each adult separately with age-specific survival, employment/re-entry, real wage growth, after-tax income, and first-future-period timing. Accrued labor capacity stops additional human-capital accrual at survey date; continuation includes modeled future work through retirement. Preserve a compatibility wrapper only where required by existing callers.

**Step 4: Verify GREEN**

Run: `uv run pytest tests/test_human_capital.py -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/human_capital.py src/config.py tests/test_human_capital.py
git commit -m "feat: model defensive and continuation labor wealth"
```

### Task 6: Social Security accrued and continuation wealth

**Files:**
- Create: `src/social_security.py`
- Create: `src/ssa_parameters.py`
- Test: `tests/test_social_security.py`

**Step 1: Write failing official-formula tests**

```python
def test_2022_pia_formula_uses_official_bend_points():
    assert primary_insurance_amount(1_024, year=2022) == pytest.approx(921.60)


def test_defensive_social_security_subtracts_future_contributions_and_haircut():
    value = social_security_wealth(person_fixture(), mode="accrued", payable_factor=0.80)
    assert value.net == pytest.approx(value.gross_benefits * 0.80 - value.future_employee_contributions)
```

**Step 2: Verify RED**

Run: `uv run pytest tests/test_social_security.py -q`
Expected: FAIL because Social Security APIs do not exist.

**Step 3: Implement Social Security valuation**

Implement 2022 AIME/PIA parameters, covered-earnings caps, claiming-age adjustments, contribution offsets, survival-weighted benefits, current-recipient reported-benefit handling, accrued and continuation earnings histories, and explicit policy-payability scenarios. Expose component diagnostics and unsupported-spousal-benefit flags.

**Step 4: Verify GREEN**

Run: `uv run pytest tests/test_social_security.py -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/social_security.py src/ssa_parameters.py tests/test_social_security.py
git commit -m "feat: value accrued and continuation Social Security"
```

### Task 7: Defined-benefit pension valuation and double-count prevention

**Files:**
- Create: `src/pensions.py`
- Test: `tests/test_pensions.py`

**Step 1: Write failing DB tests**

```python
def test_db_annuity_is_survival_weighted_from_claiming_age():
    value = defined_benefit_wealth(annual_benefit=24_000, current_age=55, claiming_age=65, survival=fixture_curve(), discount_rate=0.03)
    assert 0 < value < 24_000 * 40


def test_account_type_pension_balance_is_not_added_again():
    result = pension_components(networth_includes_dc=True, dc_balance=100_000, db_wealth=250_000)
    assert result.incremental_pension_wealth == 250_000
```

**Step 2: Verify RED**

Run: `uv run pytest tests/test_pensions.py -q`
Expected: FAIL because pension APIs do not exist.

**Step 3: Implement DB valuation**

Value current and expected DB payment flows from reported claim age, COLA convention, survivor fraction, and person-level survival. Produce accrued and continuation values plus exclusions. Never add `RETQLIQ`, `FUTPEN`, `CURRPEN`, or other account balances already inside `networth` as incremental DB wealth.

**Step 4: Verify GREEN**

Run: `uv run pytest tests/test_pensions.py -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/pensions.py tests/test_pensions.py
git commit -m "feat: add defensive defined benefit pension wealth"
```

### Task 8: Build comprehensive household resource records

**Files:**
- Modify: `src/real_data.py`
- Modify: `src/config.py`
- Test: `tests/test_real_data.py`

**Step 1: Write failing component and validation tests**

```python
def test_comprehensive_resources_equal_documented_components():
    row = build_comprehensive_household(fixture_household())
    assert row.defensive_resources == pytest.approx(row.net_worth + row.accrued_labor + row.accrued_social_security + row.accrued_db_pension)


def test_invalid_probability_is_rejected():
    with pytest.raises(ValueError):
        ModelAssumptions(employment_probability=1.2)
```

**Step 2: Verify RED**

Run: `uv run pytest tests/test_real_data.py -q`
Expected: FAIL on new components and validation.

**Step 3: Implement resource construction and diagnostics**

Add explicit component columns, defensive and continuation totals, exclusions, source/assumption version, and parameter-domain validation. Report dropped-row counts and weighted shares instead of silently dropping malformed records.

**Step 4: Verify GREEN**

Run: `uv run pytest tests/test_real_data.py -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/real_data.py src/config.py tests/test_real_data.py
git commit -m "feat: build comprehensive household resources"
```

### Task 9: Metric-specific ranking and fixed-rank decomposition

**Files:**
- Modify: `src/weighted_stats.py`
- Modify: `src/real_data.py`
- Modify: `src/reporting.py`
- Test: `tests/test_weighted_stats.py`
- Test: `tests/test_reporting.py`

**Step 1: Write failing ranking tests**

```python
def test_each_distribution_ranks_by_its_own_metric():
    result = build_ranked_distributions(rank_changing_fixture())
    assert result["defensive"].top_household_id != result["conventional"].top_household_id


def test_fixed_rank_view_is_labeled_as_decomposition():
    table = build_fixed_rank_decomposition(distribution_fixture())
    assert "conventional-net-worth rank" in table.attrs["definition"]
```

**Step 2: Verify RED**

Run: `uv run pytest tests/test_weighted_stats.py tests/test_reporting.py -q`
Expected: FAIL because metric-specific distribution APIs do not exist.

**Step 3: Implement ranking views**

Re-rank conventional, defensive, and continuation metrics independently. Add tie/boundary policy, rank transitions, fixed-rank decompositions, and correct household-share labels.

**Step 4: Verify GREEN**

Run: `uv run pytest tests/test_weighted_stats.py tests/test_reporting.py -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/weighted_stats.py src/real_data.py src/reporting.py tests/test_weighted_stats.py tests/test_reporting.py
git commit -m "fix: rank distributions by their reported measure"
```

### Task 10: SCF implicate and replicate-weight uncertainty

**Files:**
- Create: `src/scf_uncertainty.py`
- Test: `tests/test_scf_uncertainty.py`

**Step 1: Write failing combination tests**

```python
def test_implicate_point_estimate_is_mean_of_five_estimates():
    assert combine_implicates([1, 2, 3, 4, 5]).estimate == 3


def test_total_variance_combines_sampling_and_imputation_variance():
    result = combine_scf_variance(estimates=[1, 2, 3, 4, 5], sampling_variances=[4] * 5)
    assert result.standard_error > 2
```

**Step 2: Verify RED**

Run: `uv run pytest tests/test_scf_uncertainty.py -q`
Expected: FAIL because uncertainty module does not exist.

**Step 3: Implement Fed-compatible combination**

Calculate statistics separately by implicate and bootstrap replicate, combine within-imputation sampling variance with between-imputation variance, and return confidence intervals and effective unweighted counts.

**Step 4: Verify GREEN**

Run: `uv run pytest tests/test_scf_uncertainty.py -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/scf_uncertainty.py tests/test_scf_uncertainty.py
git commit -m "feat: add SCF uncertainty intervals"
```

### Task 11: Reconciliation and one-command reproduction

**Files:**
- Create: `src/reconciliation.py`
- Create: `scripts/reproduce_report.py`
- Modify: `src/fed_dfa.py`
- Test: `tests/test_reconciliation.py`
- Test: `tests/test_reproduce_report.py`

**Step 1: Write failing output tests**

```python
def test_reproduction_writes_tables_and_manifest(tmp_path):
    reproduce(output_dir=tmp_path, use_fixture=True)
    assert (tmp_path / "headline.csv").is_file()
    assert (tmp_path / "manifest.json").is_file()


def test_reconciliation_reports_difference_without_rescaling():
    result = reconcile(micro_total=90, official_total=100)
    assert result.ratio == pytest.approx(0.9)
    assert result.adjusted_micro_total == 90
```

**Step 2: Verify RED**

Run: `uv run pytest tests/test_reconciliation.py tests/test_reproduce_report.py -q`
Expected: FAIL because APIs and script do not exist.

**Step 3: Implement reproducible outputs**

Pull the Financial Accounts DB aggregate, report reconciliation ratios without forced scaling, and write headline/detail/sensitivity CSVs plus assumptions, source hashes, exclusions, uncertainty, and Git revision to JSON.

**Step 4: Verify GREEN**

Run: `uv run pytest tests/test_reconciliation.py tests/test_reproduce_report.py -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/reconciliation.py scripts/reproduce_report.py src/fed_dfa.py tests/test_reconciliation.py tests/test_reproduce_report.py
git commit -m "feat: add reproducible report pipeline"
```

### Task 12: Streamlit report redesign and bounded caching

**Files:**
- Modify: `Home.py`
- Modify: `pages/02_Wealth_by_Quantile.py`
- Modify: `pages/03_Wealth_by_Age.py`
- Modify: `pages/04_Age_Quantile_Matrix.py`
- Modify: `pages/05_Assumptions_Lab.py`
- Modify: `pages/06_Source_Data.py`
- Modify: `src/app_data.py`
- Modify: `src/charts.py`
- Modify: `src/ui.py`
- Modify: `src/provenance.py`
- Test: `tests/test_streamlit_app.py`

**Step 1: Write failing AppTest assertions**

```python
def test_home_uses_defensible_headline_labels():
    app = AppTest.from_file("Home.py").run()
    assert not app.exception
    assert any("Defensive accrued resources" in metric.label for metric in app.metric)
    assert all("full wealth" not in metric.label.lower() for metric in app.metric)
```

**Step 2: Verify RED**

Run: `uv run pytest tests/test_streamlit_app.py -q`
Expected: FAIL on current labels and views.

**Step 3: Implement UI and cache changes**

Show assumptions/data vintage beside headlines, conventional/defensive/continuation estimates with metric-specific ranks, confidence intervals, fixed-rank decomposition, lifecycle diagnostics, computed sensitivity scenarios, real provenance, and downloadable manifest bundles. Cache raw immutable data separately; bound derived caches with `max_entries`.

**Step 4: Verify GREEN**

Run: `uv run pytest tests/test_streamlit_app.py -q`
Expected: PASS with no app exceptions.

**Step 5: Commit**

```bash
git add Home.py pages src/app_data.py src/charts.py src/ui.py src/provenance.py tests/test_streamlit_app.py
git commit -m "feat: present defensive comprehensive resources"
```

### Task 13: CI, methodology, and final verification

**Files:**
- Create: `.github/workflows/ci.yml`
- Create: `docs/methodology.md`
- Modify: `README.md`
- Modify: `data/raw/README.md`
- Modify: `data/processed/README.md`

**Step 1: Add documentation validation where practical**

Extend `tests/test_release_metadata.py` to require methodology sections for scope, unit, components, exclusions, lifecycle, uncertainty, and source vintage.

**Step 2: Verify RED**

Run: `uv run pytest tests/test_release_metadata.py -q`
Expected: FAIL until methodology documentation exists.

**Step 3: Add CI and complete documentation**

CI runs `uv sync --locked`, pytest, Ruff, compileall, source-registry validation, the fixture reproduction command, and Streamlit AppTest. Document exact formulas, survey treatment, lifecycle interpretation, limitations, and reproduction commands.

**Step 4: Run full verification**

Run:

```bash
uv sync --locked
uv run pytest -q
uvx ruff check Home.py pages src scripts tests
uv run python -m compileall -q Home.py pages src scripts tests
uv run python scripts/reproduce_report.py --fixture --output-dir /tmp/wealth-report-verification
git diff --check
git status --short
```

Expected: all commands exit 0; tests report zero failures; worktree contains only intentional changes before final commit.

**Step 5: Commit**

```bash
git add .github/workflows/ci.yml docs/methodology.md README.md data/raw/README.md data/processed/README.md tests/test_release_metadata.py
git commit -m "ci: verify comprehensive wealth report"
```
