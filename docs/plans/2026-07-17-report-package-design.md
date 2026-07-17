# Report Package Design

**Status:** Approved for implementation

## Goal

Replace the catch-all `src` namespace with a lower-case `wealth_report` package
whose boundaries make the public research report, economic model, and source-data
adapters easy to find and independently review.  Retain only code needed to
produce the current three-page report and its reproducible calculation outputs.

## Non-goals

- No change to the report's methodology, assumptions, calculations, or displayed
  results.
- No compatibility imports from `src`.
- No retention of inactive human-capital-only, alternate-data, or obsolete-chart
  paths merely for backward compatibility.

## Package layout

```text
app.py
wealth_report/
  app/
    cache.py
    ui.py
    pages/
      home.py
      age_slicing.py
      methodology.py
  model/
    assumptions.py
    actuarial.py
    household.py
    labor.py
    social_security.py
    pensions.py
    income_security.py
    inheritance.py
    statistics.py
  providers/
    sources.py
    scf/
      detailed.py
      summary.py
    ssa/
      mortality.py
      parameters.py
  report/
    builder.py
    distribution.py
    charts.py
    provenance.py
    reconciliation.py
    reproduction.py
```

Every directory is a Python package and every Python file is lower-case
`snake_case`. `app.py` is the Streamlit entry point and is intentionally lower
case; page labels in the navigation remain human-readable.

## Responsibilities and dependency direction

```text
Streamlit app  -->  report  -->  providers
                    |
                    +---->  model
```

- `wealth_report.app` contains only Streamlit navigation, caching, and shared
  display controls. It imports the report-facing API, not raw survey loaders or
  valuation components.
- `wealth_report.providers` retrieves, validates, and normalizes external data:
  SCF microdata/benchmark extracts, SSA mortality and benefit parameters, and
  the source manifest.
- `wealth_report.model` contains the economic calculations and typed household
  inputs. It does not download data, render charts, or depend on Streamlit.
- `wealth_report.report` is the application-facing composition layer. It loads
  provider data, applies model valuation and inheritance reallocation, produces
  ranked distributions, audit tables, charts, and reproducible export outputs.

The public calculation entry point will be
`wealth_report.report.builder.load_comprehensive_household_data`. Pages and the
reproduction command use this interface rather than importing individual
providers or model components.

## Mapping from the current code

| Current responsibility | Destination |
| --- | --- |
| `Home.py` | `app.py` |
| `app_pages/*`, `src/ui.py`, `src/app_data.py` | `wealth_report/app/*` |
| `src/config.py`, `src/actuarial.py`, `src/human_capital.py`, `src/social_security.py`, `src/pensions.py`, `src/income_security.py`, `src/inheritance.py`, `src/weighted_stats.py` | `wealth_report/model/*` |
| Active comprehensive orchestration in `src/real_data.py` | `wealth_report/report/builder.py` |
| `src/scf_detailed.py`, `src/scf_loader.py` | `wealth_report/providers/scf/*` |
| `src/ssa_loader.py`, `src/ssa_parameters.py` | `wealth_report/providers/ssa/*` |
| `src/source_manifest.py` and active source constants | `wealth_report/providers/sources.py` |
| `src/reporting.py`, `src/charts.py`, `src/provenance.py`, `src/reconciliation.py` | `wealth_report/report/*` |
| `scripts/reproduce_report.py` | Thin CLI wrapper over `wealth_report.report.reproduction` |

## Explicit removals

The refactor removes inactive code and its tests rather than giving it a new
home:

- The legacy human-capital-only report functions, metrics, selectors, charts,
  and compatibility wrapper (`estimate_human_capital`).
- Alternate data paths that do not feed the active report: ACS, CPS, Financial
  Accounts download/extract helpers, and their associated source constants.
- SCF uncertainty utilities, if no active report page or reproduction export
  consumes them.
- Old app paths and references to `Home.py`, `app_pages`, and `src` in the
  README, contribution guide, scripts, and tests.

## Verification contract

The migration is complete only when:

1. No application, script, test, documentation command, or import refers to
   `src`, `Home.py`, or `app_pages`.
2. The three Streamlit pages remain Home, Age slicing, and Methodology.
3. The report builder produces the same schema and values for a fixed source
   snapshot and assumptions as immediately before the move.
4. Unit tests are reorganized by the same layers (`model`, `providers`,
   `report`, and `app`) and cover the public calculation boundary.
5. The full test suite, Ruff, compile check, reproduction command, and
   Streamlit smoke test pass.
