# Comprehensive Household Resources

An open-source Streamlit report comparing conventional SCF family net worth with modeled comprehensive resources.

- **Conventional net worth:** SCF assets minus liabilities.
- **Defensive accrued resources:** net worth plus conservative modeled labor resources, accrued Social Security, and accrued defined-benefit pensions.
- **Continuation resources:** net worth plus projected labor earnings, retirement claims, a separately disclosed income-security floor scenario, and a nationally conserved expected-inheritance reallocation.

These measures answer different questions. Modeled labor, retirement, and income-security resources are personal, risky, nontransferable, and generally illiquid. The income-security floor is calibrated to the 2022 average SSI payment as a scenario benchmark; it is not an eligibility determination or guaranteed payment. They are not official Federal Reserve wealth statistics. The app ranks every distribution by its own measure and uses conventional-rank tables only as labeled decompositions.

The expected-inheritance reallocation uses SCF field values (including SCF imputation where applicable) and estate intent with an explicit horizon and SSA mortality. It reallocates SCF expectation field values rather than creating national wealth: recipient credits are offset by aggregate donor reserves, while conventional net worth remains unchanged. The public SCF does not link recipient to donor families, so the result is neither current legal ownership nor a guaranteed transfer or legal claim. The horizon is a visible scenario control, not observed transfer timing, and positive SCF expectation field values are used without an invented probability haircut in the base scenario. Estate taxes, care costs, consumption, gifts, charity, siblings, and unobserved heirs are not modeled. No future return is added for an inherited asset already valued on the current owner's balance sheet.

The public app has three views: **Home** for the national distribution shift, **Age slicing** for the same comparison within respondent-age buckets, and **Methodology** for the live number audit, formulas, assumptions, sources, conservation checks, limitations, and reproduction instructions.

## Run locally

```bash
uv sync
uv run streamlit run Home.py
```

On first use, the app downloads the hash-pinned Federal Reserve 2022 SCF summary and full public files. A normalized SSA mortality snapshot is committed because SSA blocks unattended downloads in some environments.

## Test and reproduce

```bash
uv run pytest -q
uvx ruff check Home.py app_pages src scripts tests
uv run python -m compileall -q Home.py app_pages src scripts tests
uv run python scripts/reproduce_report.py --real-data --output-dir build/report
```

The real-data export writes the Home comparison, Age slicing data, component totals, rank detail, reconciliation, scenario controls, and source-integrity manifest. Use `--fixture` only to check the output contract; it is not an empirical result.

## Audit trail

- [Methodology](docs/methodology.md) documents formulas, lifecycle interpretation, exclusions, uncertainty, and criticism surfaces.
- [Source registry](data/sources.json) pins providers, vintages, archive members, and hashes.
- The Methodology page and generated manifest expose provenance and assumptions.
- [Contributing](CONTRIBUTING.md), [security policy](SECURITY.md), [code of conduct](CODE_OF_CONDUCT.md), and [citation metadata](CITATION.cff) support public collaboration.

Code is Apache-2.0 licensed. Source datasets remain subject to provider terms.
