# Methodology

This report compares a conventional balance-sheet measure with two modeled measures of comprehensive household resources. It does not claim that the measures are interchangeable or that one is the uniquely correct definition of wealth.

## Scope and unit

The observational unit is an SCF family in the Federal Reserve's 2022 Survey of Consumer Finances, represented by one of five implicates and its SCF family weight. Results describe weighted SCF families, not persons. Dollar totals are 2022 dollars. They are cross-sectional estimates, not a national balance sheet and not a forecast of aggregate GDP.

Each distribution is ranked independently by the measure being reported. A separately labeled fixed-conventional-rank table may be used to decompose components, but it is not called the distribution of comprehensive resources.

## Public report and number audit

The public Streamlit report has three views: **Home**, **Age slicing**, and **Methodology**. Home ranks all weighted SCF families separately under conventional net worth and all modeled future resources. Age slicing repeats that comparison after restricting the data to each respondent-age bucket, then independently ranks families within that bucket.

Methodology is the on-site audit surface. Its Home table traces every chart resource share, weighted total, family share, and percentage-point change. Its Age slicing table traces the same plotted values as well as every visible panel caption: the weighted SCF family count and all-modeled-resources total. These audit rows are produced from the same live calculation output that drives the charts; they state a formula, source fields, source keys, and whether the value is computed from SCF microdata or model-derived.

For all national totals and age-bucket counts, the SCF family weight `WGT` is applied. A chart's resource share is the weighted value in its independently ranked group divided by the corresponding measure's weighted total. An age-panel count is the sum of `WGT` in its age bucket; its all-modeled-resources total is the sum of `continuation_resources × WGT` in that bucket.

## Components

### Conventional net worth

Conventional net worth is the SCF summary variable `NETWORTH`: assets minus liabilities. It already contains defined-contribution and account-type retirement balances represented in SCF components such as `RETQLIQ`, `FUTPEN`, and `CURRPEN`. Those balances are not added again.

### Labor resources

Respondent and spouse wage income are projected separately from the detailed SCF file. For person `i`, the continuation value is:

```text
PV labor_i = sum from t=1 to retirement(
  survival_i,t * employment_i,t * after-tax earnings_i,t
  / (1 + real discount rate)^t
)
```

The first payment is one year after the survey. The defensive case assumes zero real wage growth; continuation applies the selected growth rate. A working-age adult with no reported wage can receive a positive value only through an explicit re-entry assumption: the model assigns the weighted median positive wage among SCF peers in the same sex-by-age group, then multiplies that stream by the visible re-entry probability. This is a transparent peer-based imputation, not an observed wage or a guarantee of employment. Mixed business income is excluded to avoid capitalizing returns already reflected in business equity.

“Accrued” in the UI is shorthand for the conservative composite measure. Labor capacity is not a legally accrued claim; it remains a risky, person-bound expectation.

### Social Security

Current recipients use separately reported SCF Social Security benefits. Other adults use an earnings-history proxy because the public SCF lacks SSA administrative earnings records. The proxy applies modeled credited years and the 2022 PIA formula:

```text
PIA = 90% of AIME through $1,024
    + 32% of AIME from $1,024 through $6,172
    + 15% of AIME above $6,172
```

The accrued case credits modeled earnings through the survey date; continuation adds projected covered years through retirement, capped at 35. Benefits are adjusted for claiming age, survival weighted, and discounted. Modeled future employee OASDI contributions equal 6.2% of covered wages, capped at $147,000 in 2022, and are subtracted. The defensive baseline multiplies scheduled benefits by 80%, the combined-fund amount projected payable at depletion in the 2022 Trustees Report. This is a scenario, not a prediction of legislation.

### Defined-benefit pensions

Only SCF plans reported as lifetime-income or non-account pension flows are incrementally valued. Current DB benefits are fully accrued. For a future benefit, the accrued fraction is approximated as modeled career years divided by career years plus remaining years to retirement; continuation uses the full reported benefit. Payments begin at reported claiming age, are survival weighted, and are discounted. The aggregate is compared, without rescaling, with Financial Accounts series `FL594190045`.

### Income-security floor scenario

The comprehensive continuation measure includes a nonmarketable top-up scenario for working-age and retired adults whose modeled labor, Social Security, and DB pension cash income falls below a modest benchmark. In each future year, the top-up is:

```text
max(0, monthly benchmark × 12 × adult scaling
       − expected labor cash income − Social Security cash benefit − DB pension cash benefit)
```

The stream is survival weighted and discounted using the same real discount rate. The default benchmark is $622 per month in 2022 dollars: the December 2022 average SSI payment, used only as an externally observable calibration point. Two-adult families use a 1.5× benchmark scale. The model does not determine SSI or any other program eligibility, does not count a legal entitlement, and does not model children, state programs, assets tests, housing assistance, or benefit interactions. For two-adult households, the probability that at least one adult survives is calculated under an independence approximation.

### Expected inheritance reallocation

The continuation measure includes a constrained aggregate reallocation of expected inheritances. It uses a positive SCF field value (including SCF imputation where applicable) only where `X5819` says the SCF family expects a substantial future inheritance or transfer and `X5821` has a positive amount. At the selected horizon `H` and real discount rate `r`, the recipient claim is:

```text
claim_i = SCF expectation field value_i / (1 + r)^H
```

The horizon is a visible scenario control, not observed transfer timing. Positive SCF expectation field values are used without an invented probability haircut in the base scenario; that is a transparent choice to retain the survey field value rather than fabricate a family-specific probability.

To fund recipient claims without adding a second copy of existing assets, a family can supply donor capacity only if it has positive `NETWORTH`, affirmative `X5825` sizable-estate intent, and usable respondent age and sex. Its capacity is:

```text
capacity_j = NETWORTH_j × P(death within H years | respondent age, sex)
```

The mortality probability comes from the SSA period life table. Weighted claims and capacities are summed, the funded amount is `min(claims, capacity)`, and proportional scales give equal weighted recipient credits and donor reserves. This component reallocates SCF expectation field values rather than creating national wealth. Conventional net worth remains unchanged.

Before Home, Age slicing, or Methodology reports continuation resources, the application checks the conservation identity

```text
sum(WGT × recipient credit) = sum(WGT × donor reserve)
```

within the larger of one cent and one part in 10^12. This permits only floating-point rounding noise, not a material unreserved credit.

The public SCF does not link recipient to donor families, so this is not a prediction of an actual parent-child transfer. It is neither current legal ownership nor a guaranteed transfer, and it is not a legal claim. Estate taxes, care costs, consumption, gifts, charity, siblings, and unobserved heirs are not modeled. No future return is added for an inherited asset already valued on the current owner's balance sheet.

## Exclusions

- Defined-contribution and account-type balances already present in `NETWORTH` are excluded from incremental pension wealth.
- Social Security spousal and survivor benefits are not imputed from insufficient public inputs.
- DB survivor annuities are excluded when a defensible joint-life curve is unavailable.
- Mixed self-employment and business income is not added wholesale.
- Child benefits, state and local programs, asset tests, and program-specific eligibility are not modeled in the income-security scenario.
- Expected-inheritance credits and estate donor reserves are modeled only as a nationally conserved aggregate reallocation; public SCF data do not identify actual donor-recipient relationships.
- Estate taxes, care costs, consumption, gifts, charitable transfers, sibling shares, and unobserved heirs are not modeled in the expected-inheritance scenario.
- Expected-inheritance claims do not add future yields, rents, dividends, or capital gains to an asset already priced on the current owner's balance sheet.
- Liquidity, transferability, collateral value, bequest value, and taxation are not assumed equal across components.

Exclusions are emitted on household records and in reproduction manifests rather than silently replaced without explanation.

## Lifecycle

Both conventional and expanded measures are evaluated in the same cross-sectional lifecycle framework. Younger families usually have accumulated less balance-sheet wealth and retain more working years; retirees display the reverse. Adding future resources therefore changes both age profiles and ranks. Within-age results are needed before making claims about persistent inequality or welfare.

The expanded measures do not make earnings liquid, transferable, inheritable, or available for a current emergency. They answer a lifetime-resource question; conventional net worth answers an ownership and balance-sheet question.

## Uncertainty

The code combines within-implicate sampling variance with between-implicate variance using Rubin's rule:

```text
T = mean(U_m) + (1 + 1/M) * B
```

The uncertainty API and arithmetic are tested. The current public headline pipeline does not yet load every SCF replicate weight into every scenario calculation, so headline intervals are not displayed. Until that integration is complete, the UI must be read as point estimates and sensitivity analysis, not precise population parameters.

Model uncertainty is likely larger than sampling uncertainty. The discount rate, employment, re-entry, earnings-history proxy, retirement age, payable factor, and DB accrual approximation should all be varied.

## Source vintage

- Federal Reserve 2022 SCF summary and full public files, pinned in `data/sources.json`.
- Federal Reserve 2022 SCF replicate weights, registered and hash-pinned for uncertainty integration.
- SSA 2019 observed period life table published with the 2022 Trustees Report; a source-attributed snapshot is committed for deterministic offline use.
- SSA 2022 PIA bend points, taxable maximum, OASDI rate, and Trustees payable-benefit scenario.
- Financial Accounts series `FL594190045`: 2022 DB entitlements of $15.6583 trillion in the cited release vintage.

Downloads are hash-verified where deterministic artifacts are available. Generated manifests record assumptions, Git revision, sources, exclusions, and reconciliation without forced scaling.

## Limitations

1. Future labor income is not an owned or saleable asset. Calling its present value wealth is an analytical convention, not an accounting fact.
2. Equity prices are market risk-adjusted; labor uses scenario discounting and simple employment probabilities. Equal present-value notation does not imply equal risk, optionality, or legal status.
3. The earnings-history proxy can misstate Social Security benefits for intermittent workers, immigrants, changing wages, and couples eligible for auxiliary benefits.
4. The peer-based re-entry wage imputation can overstate or understate the prospects of non-earners; the re-entry probability is a sensitivity control, not a causal estimate.
5. Future DB accrual is an approximation, not plan-specific service-cost accounting.
6. Period mortality is not cohort mortality and ignores mortality gradients correlated with wealth; the household floor also assumes independent adult mortality.
7. The income-security floor is a deliberately limited scenario, not a measure of statutory benefits or household consumption needs.
8. SCF top-tail, imputation, and sampling uncertainty remain material; public headlines are currently point estimates.
9. Cross-sectional lifecycle differences are not evidence about mobility, consumption, utility, political rights, or moral desirability.
10. Lower comprehensive-resource concentration does not invalidate conventional wealth inequality; it shows a broader estimand has a different distribution.
11. The inheritance horizon is a scenario control, and public SCF expectation and estate-intent answers are not legally enforceable transfer commitments.

## Reproduction

```bash
uv run python scripts/reproduce_report.py --fixture --output-dir build/report
```

This emits `headline.csv`, `detail.csv`, `sensitivity.csv`, and `manifest.json`. The fixture validates code paths and contracts; it is not empirical evidence. The Streamlit app loads pinned real SCF files for displayed point estimates.
