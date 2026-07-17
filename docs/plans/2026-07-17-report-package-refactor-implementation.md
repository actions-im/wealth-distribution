# Report Package Refactor Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the `src` catch-all namespace with the lower-case `wealth_report` package, delete unused legacy code, and preserve the active three-page report and reproducible calculation pipeline.

**Architecture:** `wealth_report.app` renders Streamlit pages and shared controls; `wealth_report.report` coordinates source loading, valuation, audit tables, and charts; `wealth_report.model` contains pure valuation logic; and `wealth_report.providers` owns SCF, SSA, and source-manifest access. The dependency direction is `app → report → {providers, model}`.

**Tech Stack:** Python 3.11+, Streamlit, pandas, Plotly, pytest, Ruff, uv.

---

### Task 1: Establish the new public package contract

**Files:**
- Create: `wealth_report/__init__.py`
- Create: `wealth_report/{app,model,providers,report}/__init__.py`
- Create: `tests/test_package_layout.py`
- Delete: `src/__init__.py` (after imports move)

**Step 1: Write the failing test**

```python
from pathlib import Path


def test_public_package_uses_lowercase_layer_directories():
    root = Path("wealth_report")
    assert (root / "app").is_dir()
    assert (root / "model").is_dir()
    assert (root / "providers").is_dir()
    assert (root / "report").is_dir()
    assert not Path("src").exists()
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_package_layout.py -v`

Expected: FAIL because `wealth_report` does not exist and `src` remains.

**Step 3: Create the minimal package skeleton**

Create lower-case package directories and `__init__.py` files. Do not add aliases
from `src`.

**Step 4: Run test to verify the skeleton passes**

Run: `uv run pytest tests/test_package_layout.py -v`

Expected: PASS after the final move/removal in this task series.

### Task 2: Move pure economic-model components

**Files:**
- Create: `wealth_report/model/{assumptions,actuarial,labor,social_security,pensions,income_security,inheritance,statistics}.py`
- Modify: imports in moved modules
- Modify: model unit tests under `tests/model/`
- Delete: `src/{config,actuarial,human_capital,social_security,pensions,income_security,inheritance,weighted_stats}.py`

**Step 1: Write/adjust failing import tests**

```python
from wealth_report.model.labor import estimate_labor_wealth
from wealth_report.model.assumptions import ModelAssumptions


def test_model_public_modules_have_no_src_imports():
    assert callable(estimate_labor_wealth)
    assert ModelAssumptions().discount_rate > 0
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/model/test_labor.py -v`

Expected: FAIL with `ModuleNotFoundError: wealth_report` before migration.

**Step 3: Move active calculation modules and update internal imports**

Rename `config.py` to `assumptions.py` and `human_capital.py` to `labor.py`.
Remove the inactive `estimate_human_capital` compatibility wrapper and its tests;
retain only active projected-income and labor-wealth functions. Update imports to
relative lower-case package paths.

**Step 4: Run model tests**

Run: `uv run pytest tests/model -v`

Expected: PASS.

### Task 3: Move external-data providers

**Files:**
- Create: `wealth_report/providers/sources.py`
- Create: `wealth_report/providers/scf/{__init__,detailed,summary}.py`
- Create: `wealth_report/providers/ssa/{__init__,mortality,parameters}.py`
- Modify: provider tests under `tests/providers/`
- Delete: `src/{scf_detailed,scf_loader,ssa_loader,ssa_parameters,source_manifest,data_sources}.py`
- Delete: inactive `src/{acs_loader,cps_loader,fed_dfa,scf_uncertainty}.py`

**Step 1: Write failing provider import tests**

```python
from wealth_report.providers.scf.detailed import build_detailed_household_input
from wealth_report.providers.ssa.mortality import load_ssa_period_life_table


def test_provider_modules_expose_active_source_adapters():
    assert callable(build_detailed_household_input)
    assert callable(load_ssa_period_life_table)
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/providers/test_provider_imports.py -v`

Expected: FAIL before moving providers.

**Step 3: Move active SCF, SSA, and source registry code**

Keep the detailed SCF parser separate from the conventional SCF summary loader.
Keep source URLs and artifact validation in `providers/sources.py`. Do not retain
ACS, CPS, Federal Financial Accounts, or uncertainty helpers because no active
report or reproduction output consumes them.

**Step 4: Run provider tests**

Run: `uv run pytest tests/providers -v`

Expected: PASS.

### Task 4: Extract the report builder and presentation layer

**Files:**
- Create: `wealth_report/report/{builder,distribution,charts,provenance,reconciliation,reproduction}.py`
- Modify: `tests/report/*`
- Delete: `src/{real_data,reporting,charts,provenance,reconciliation,formatting}.py`

**Step 1: Write the failing builder-boundary test**

```python
from wealth_report.model.assumptions import ModelAssumptions
from wealth_report.report.builder import build_comprehensive_household_data


def test_builder_exposes_the_active_full_resource_pipeline():
    assert callable(build_comprehensive_household_data)
    assert ModelAssumptions().retirement_age > 0
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/report/test_builder.py -v`

Expected: FAIL before the builder is moved.

**Step 3: Split active orchestration from legacy code**

Move only the comprehensive, detailed-SCF pipeline from `real_data.py` into
`report/builder.py`. Move active aggregation/table functions into
`report/distribution.py`, chart functions into `report/charts.py`, source/audit
tables into `report/provenance.py`, and command/reconciliation support into the
corresponding report modules. Delete the old human-capital-only loader,
quantile aggregation, and chart functions.

**Step 4: Run report tests**

Run: `uv run pytest tests/report -v`

Expected: PASS.

### Task 5: Move Streamlit app code and replace the entry point

**Files:**
- Create: `wealth_report/app/{cache,ui}.py`
- Create: `wealth_report/app/pages/{__init__,home,age_slicing,methodology}.py`
- Create: `app.py`
- Modify: `tests/app/*`
- Delete: `Home.py`
- Delete: `app_pages/`

**Step 1: Write the failing entry-point test**

```python
from pathlib import Path


def test_streamlit_entry_point_and_pages_are_lowercase():
    source = Path("app.py").read_text()
    assert 'st.Page("wealth_report/app/pages/home.py"' in source
    assert 'st.Page("wealth_report/app/pages/age_slicing.py"' in source
    assert 'st.Page("wealth_report/app/pages/methodology.py"' in source
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/app/test_streamlit_app.py::test_streamlit_entry_point_and_pages_are_lowercase -v`

Expected: FAIL because `app.py` does not yet exist.

**Step 3: Move pages and update imports**

Move shared cache/UI code and all three page scripts into the new package.
Replace `Home.py` with lower-case `app.py`, retaining exactly Home, Age slicing,
and Methodology in explicit navigation. Page modules import only `app` and
`report` interfaces.

**Step 4: Run app tests**

Run: `uv run pytest tests/app -v`

Expected: PASS.

### Task 6: Make reproduction and documentation follow the new public surface

**Files:**
- Modify: `scripts/reproduce_report.py`
- Modify: `README.md`
- Modify: `CONTRIBUTING.md`
- Modify: `docs/methodology.md`
- Modify: `pyproject.toml`
- Modify: `tests/test_reproduce_report.py`

**Step 1: Write a failing reproduction import test**

```python
def test_reproduction_script_imports_only_wealth_report_modules():
    source = Path("scripts/reproduce_report.py").read_text()
    assert "from wealth_report." in source
    assert "from src." not in source
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_reproduce_report.py -v`

Expected: FAIL because the script still imports `src`.

**Step 3: Update commands and documentation**

Keep the script as a thin CLI wrapper over `wealth_report.report.reproduction`.
Point README and contributor commands to `app.py` and `wealth_report`; remove
historical implementation-plan references only where they are presented as
current commands.

**Step 4: Run reproduction test**

Run: `uv run pytest tests/test_reproduce_report.py -v`

Expected: PASS.

### Task 7: Verify deletion, results, and runtime behavior

**Files:**
- Modify: affected tests only if a public active-path assertion needs correction

**Step 1: Verify no stale names remain**

Run: `rg -n "from src|import src|Home\\.py|app_pages" README.md CONTRIBUTING.md pyproject.toml scripts wealth_report tests`

Expected: no results.

**Step 2: Run the complete suite and static checks**

Run: `uv run pytest -q && uv run ruff check app.py wealth_report scripts tests && uv run python -m compileall -q app.py wealth_report scripts tests && git diff --check`

Expected: every command exits zero.

**Step 3: Run the reproducible export**

Run: `uv run python scripts/reproduce_report.py --output-dir /tmp/wealth-report-refactor`

Expected: exit zero and write the report outputs and source metadata.

**Step 4: Smoke-test Streamlit**

Run: `uv run streamlit run app.py --server.port 8502 --server.headless true`

Expected: Streamlit starts without import or navigation errors; load each of the
three public routes once.

**Step 5: Commit**

```bash
git add app.py wealth_report scripts tests README.md CONTRIBUTING.md docs/methodology.md pyproject.toml
git commit -m "refactor: organize report into layered packages"
```
