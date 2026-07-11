# Comprehensive household resources design

## Objective

Build a defensible cross-sectional comparison between conventional SCF family net worth and modeled comprehensive household resources. The expanded measures will add survival-adjusted labor earnings, Social Security, and defined-benefit pension wealth without double-counting retirement balances already included in SCF net worth.

The application will retain the same lifecycle framework for conventional and expanded wealth. Lifecycle differences will be disclosed and analyzed, but they will not be used to reject one measure while accepting the other.

## Measures

The report will distinguish three measures.

1. **Conventional SCF family net worth**: assets minus liabilities using the Federal Reserve SCF definition. Defined-contribution and account-type retirement balances already included in `networth` remain here and are not added again.
2. **Defensive accrued comprehensive resources**: conventional net worth plus the value of labor capacity and retirement claims accrued by the survey date. Social Security is net of modeled future employee payroll contributions and applies an explicit policy-payability haircut. DB pension wealth uses accrued benefits where the source data support them.
3. **Continuation comprehensive resources**: conventional net worth plus projected labor earnings and retirement benefits assuming current employment, earnings, and pension coverage continue to the modeled retirement age.

Every component will be reported separately. The application will avoid the terms “real wealth,” “priced wealth,” and unqualified “full wealth.”

## Data sources

The reproducible data pipeline will pull and pin:

- the Federal Reserve 2022 SCF summary extract for conventional net worth and established summary variables;
- the Federal Reserve 2022 full public SCF dataset for respondent, spouse, Social Security, and detailed pension inputs;
- the Federal Reserve SCF replicate-weight file for sampling uncertainty;
- SSA 2022 period life tables by age and sex;
- SSA 2022 PIA bend points, contribution-and-benefit base, payroll-tax parameters, and retirement rules;
- survey-vintage Social Security Trustees assumptions for the defensive policy-payability scenario; and
- Federal Reserve Financial Accounts 2022 defined-benefit pension entitlements for aggregate reconciliation.

Each downloaded artifact will have a manifest entry containing its provider, canonical URL, vintage, retrieval time, archive member, byte size, and SHA-256 hash. Transformation outputs will include the source-manifest version and Git revision.

## Valuation methodology

### Labor earnings

Respondent and spouse/partner earnings will be modeled separately where the full SCF provides sufficient inputs. Expected after-tax labor income will be projected by age, survival, employment, and retirement state. Current zero earnings will not automatically imply zero lifetime earnings; an explicit re-entry probability will be used.

The present value for person `i` is:

```text
PV_labor_i = sum_t(
    survival_probability_i,t
    * employment_probability_i,t
    * expected_after_tax_labor_income_i,t
    / (1 + real_discount_rate)^t
)
```

The payment timing convention begins with the first future period. Self-employment income will not be added wholesale because it mixes labor and capital returns already reflected in business equity. Any owner-labor component will be separately identified or excluded with disclosure.

### Social Security

For current recipients, reported benefits will be used when the detailed SCF allows Social Security to be separated from other retirement income. For nonrecipients, an earnings-history proxy will generate average indexed monthly earnings and apply the official SSA PIA formula.

- **Accrued value** uses earnings credited through the survey date.
- **Continuation value** includes projected covered earnings through retirement.
- Benefits are survival weighted from claiming age.
- Future employee OASDI contributions are subtracted.
- The defensive scenario applies an explicit survey-vintage payable-benefit factor after projected trust-fund depletion; scheduled benefits remain a visible alternative.

Spousal and survivor benefits will be included only where the available household data support a defensible calculation. Unsupported values will be disclosed as exclusions rather than silently imputed.

### Defined-benefit pensions

Account balances already included in `networth`, including defined-contribution retirement wealth represented by SCF `RETQLIQ`, `FUTPEN`, and `CURRPEN`, will not be added again.

DB wealth will use detailed SCF questions on current and expected benefit flows, plan type, expected claiming age, respondent/spouse characteristics, and survivor provisions where available.

- **Accrued DB wealth** values benefits earned if additional accrual stops at the survey date.
- **Continuation DB wealth** values expected benefits conditional on continued coverage through retirement.
- Payment streams are survival weighted and discounted in real terms.

Weighted DB totals will be reconciled against the Financial Accounts aggregate. Reconciliation differences will be published; the household estimates will not be silently rescaled to force agreement.

## Distribution statistics

Households will be ranked independently under conventional net worth, defensive accrued resources, and continuation resources. The current fixed-net-worth-rank calculation will remain as a separately labeled decomposition.

The report will use “SCF families” or “SCF-weighted households,” not “population” or “total country wealth.” It will publish:

- top 1%, bottom 90%, and detailed quantile shares under metric-specific rankings;
- fixed-conventional-rank component decompositions;
- weighted totals and component shares;
- rank-transition diagnostics;
- within-age and age-bucket views as lifecycle diagnostics; and
- confidence intervals from SCF implicates and replicate weights.

Each statistic will be calculated separately for each implicate. Sampling and imputation uncertainty will be combined according to Federal Reserve SCF guidance.

## Application design

The home page will lead with a neutral explanation that conventional net worth and modeled comprehensive resources answer different questions. The normative rights argument will be explicitly separated from the empirical results.

Baseline assumptions and the data vintage will appear next to headline estimates. The main comparison will show conventional net worth, defensive accrued resources, and continuation resources together. The assumptions lab will calculate its displayed scenarios rather than listing static labels.

The application will cache immutable raw source data once and bound caches for derived scenario outputs. Source download and transformation failures will produce actionable errors without substituting synthetic data.

## Reproducibility and release readiness

The repository will include:

- an Apache-2.0 code license;
- a formal methodology document and limitations section;
- `CITATION.cff`, `CONTRIBUTING.md`, `SECURITY.md`, and a code of conduct;
- a one-command, non-Streamlit reproduction entry point that emits tables and a JSON manifest;
- CI for tests, lint, compilation, source-manifest validation, and a Streamlit smoke test;
- source-integrity checks and pinned artifact hashes;
- parameter-domain validation and explicit exclusion diagnostics; and
- real-data regression tests tied to the pinned source manifest.

## Testing strategy

All behavioral changes will follow red-green-refactor test-driven development. Tests will cover:

- survival and annuity timing;
- Social Security PIA calculations, accrued and continuation values, contribution offsets, and policy haircuts;
- DB accrued and continuation payment streams;
- prevention of DC/account-balance double counting;
- respondent/spouse separation;
- non-earner re-entry and retirement edge cases;
- metric-specific re-ranking and fixed-rank decompositions;
- implicate combination and replicate-weight uncertainty;
- source downloads, hashes, archive members, and manifests;
- aggregate reconciliation diagnostics;
- scenario sensitivity and parameter validation; and
- Streamlit headline labels and absence of app exceptions.

Tests will verify arithmetic and invariants rather than encode a required political or distributional conclusion.
