# Three-page public report design

## Goal

Reduce the public Streamlit report to three purpose-built views while retaining a complete, source-backed explanation of every calculation used by the remaining views.

## Public structure

The report exposes exactly three pages:

1. **Home** — national distribution shift between conventional net worth and all modeled future resources. It introduces the estimand, shows the main chart, and keeps the essential warnings about nonmarketability and independent ranking.
2. **Age slicing** — the same comparison within respondent-age buckets. It makes the lifecycle effect visible without adding alternate analytical views.
3. **Methodology** — the public audit surface for definitions, displayed values, formulas, source fields, scenario assumptions, source registry, conservation checks, exclusions, uncertainty, and reproduction.

The former quantile, age, age-quantile-matrix, assumptions-lab, and source-data pages are removed rather than hidden. Their only essential public content is retained where it belongs: sources and calculation lineage live on Methodology; the remaining two report pages link there.

## Navigation

Replace legacy automatic discovery of the `pages/` directory with explicit Streamlit navigation. With only three destinations, navigation appears at the top of the report. This makes the public surface auditable: no stale page can reappear simply because a Python file remains in the repository.

The three current report scripts become explicit application pages. The application entry point defines titles and icons, then runs the selected page. Shared sidebar assumptions and computational functions remain unchanged so every remaining view uses the same active scenario.

## Methodology contract

Methodology is the single on-site source-and-calculation audit. It must state, in plain language and tabular form:

- the unit of observation, dollar vintage, weighting, and independent-ranking rule;
- definitions of conventional net worth and all modeled future resources;
- each incremental component's formula, source fields, sources, assumptions, and double-count protections;
- the exact constrained aggregate inheritance procedure, including claim eligibility, mortality-weighted donor capacity, funding cap, equal weighted credit/reserve conservation, and excluded mechanisms;
- every displayed headline value's calculation and provenance;
- all active sidebar assumptions, clearly marked as scenario controls rather than official estimates;
- the official source registry, with provider, vintage, canonical URL, local filename, and hash status;
- limitations, uncertainty status, and the reproduction command.

The long-form repository methodology remains synchronized with the page and serves readers who want the detailed text outside the application.

## Data flow and safeguards

Home, Age slicing, and Methodology each obtain their data from the same `load_comprehensive_report_data` call using the active sidebar settings. Each invokes the inheritance conservation validator before reporting continuation resources. The methodology page presents the formulas and source lineage from the same provenance helpers used by captions and number-audit tables.

No source-data model, assumptions, calculations, or chart values are changed by this cleanup. It changes the public information architecture only.

## Verification

Tests must prove that explicit navigation registers exactly the three approved pages and that deleted legacy routes are absent. Existing methodology tests must continue to verify the current calculation and source lineage, including the inheritance explanation and source registry. The full test suite, lint, compilation, and a browser smoke test of all three public pages complete the change.
