# Comprehensive Household Resources

An open-source Streamlit report comparing conventional SCF family net worth with modeled comprehensive resources.

- **Conventional net worth:** SCF assets minus liabilities.
- **Defensive accrued resources:** net worth plus conservative modeled labor resources, accrued Social Security, and accrued defined-benefit pensions.
- **Continuation resources:** net worth plus projected labor earnings, retirement claims, and a separately disclosed income-security floor scenario.

These measures answer different questions. Modeled labor, retirement, and income-security resources are personal, risky, nontransferable, and generally illiquid. The income-security floor is calibrated to the 2022 average SSI payment as a scenario benchmark; it is not an eligibility determination or guaranteed payment. They are not official Federal Reserve wealth statistics. The app ranks every distribution by its own measure and uses conventional-rank tables only as labeled decompositions.

## Run locally

```bash
uv sync
uv run streamlit run Home.py
```

On first use, the app downloads the hash-pinned Federal Reserve 2022 SCF summary and full public files. A normalized SSA mortality snapshot is committed because SSA blocks unattended downloads in some environments.

## Test and reproduce

```bash
uv run pytest -q
uvx ruff check Home.py pages src scripts tests
uv run python -m compileall -q Home.py pages src scripts tests
uv run python scripts/reproduce_report.py --fixture --output-dir build/report
```

The fixture checks the output contract; it is not an empirical result. The Streamlit app calculates real-data point estimates from pinned SCF inputs.

## Audit trail

- [Methodology](docs/methodology.md) documents formulas, lifecycle interpretation, exclusions, uncertainty, and criticism surfaces.
- [Source registry](data/sources.json) pins providers, vintages, archive members, and hashes.
- The Source Data page and generated manifest expose provenance and assumptions.
- [Contributing](CONTRIBUTING.md), [security policy](SECURITY.md), [code of conduct](CODE_OF_CONDUCT.md), and [citation metadata](CITATION.cff) support public collaboration.

Code is Apache-2.0 licensed. Source datasets remain subject to provider terms.
