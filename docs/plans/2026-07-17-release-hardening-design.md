# Release hardening design

## Objective

Correct the report's identified data and display defects without changing the
underlying policy choices that require a separate methodology decision.

## Scope

1. Correct respondent and spouse wage annualization using the SCF's documented
   frequency, hours, and weeks fields.
2. Render negative conventional-net-worth shares truthfully in age panels.
3. Remove the inactive liquidity-weight control and stale hover documentation.
4. Produce a deterministic real-data report export with source hashes,
   assumptions, headline results, component totals, and reconciliation output.
5. Load Social Security benefit types and prevent non-retirement payments from
   being silently represented as retired-worker benefits.

## Non-goals

- Change the income-floor eligibility or financing model.
- Change the synthetic inheritance allocation design.
- Claim that modeled household resources are a national balance sheet.
- Add a new normative interpretation of the results.

## Design decisions

### Wage annualization

Use the full SCF wage frequency codebook. Hourly compensation is multiplied by
reported hours per normal week and weeks per normal year. Weekly, biweekly, and
daily compensation use the reported weeks field where available. Unsupported
piece-rate, variable, and other frequencies remain explicitly unannualized
rather than being silently treated as zero without a diagnostic.

### Signed distribution charts

Retain the paired distribution design, but derive the x-axis from the actual
minimum and maximum cumulative shares. Negative conventional-bottom shares are
shown to the left of zero with a visible signed label; the chart no longer
claims that every visible bar is a conventional positive 100-percent stack.

### Social Security benefit classification

Preserve the SCF-reported benefit type on each person. Only current retired-worker
payments are valued as retired-worker Social Security income. Disability,
survivor/dependent, SSI, and Railroad-Retirement-inclusive observations are
recorded as exclusions until a separately specified benefit model is approved.

### Reproduction

The report script gains a real-data mode that uses the same loader and
assumptions as the Streamlit pages. It emits headline distributions, component
totals, active assumptions, source hashes, Git revision, and the DB benchmark
comparison. Fixture mode remains for fast CI contract tests.

## Verification

Each defect receives a failing regression test before implementation. The full
test suite and a real-data smoke export must pass. The headline must be
recalculated after the wage correction; no previous displayed total is retained
without regeneration.
