# Income-security floor design

## Decision

Replace the implicit zero-resource treatment of non-earning families with two
separate, auditable model components:

1. A probability-weighted re-entry wage for working-age adults with no reported
   current wage.
2. A modeled income-security floor, calibrated to the 2022 average SSI payment,
   that tops up projected annual income only when it falls below the selected
   benchmark.

The model will not call the floor SSI, welfare, or a guaranteed entitlement.
It is a scenario-calibrated, nonmarketable income-resource floor.

## Cash-flow treatment

For every future year, the household's floor top-up is:

```
max(0, floor benchmark - expected labor income - Social Security cash benefit - DB pension cash benefit)
```

The yearly top-ups are survival-weighted and discounted with the active real
discount rate. This prevents double counting a modeled Social Security or DB
pension flow. Current net worth is not treated as spendable income in the
top-up formula.

The default 2022 monthly benchmark is $622, the reported average SSI payment
in December 2022. A two-adult SCF family receives 1.5 times the individual
benchmark, consistent with the ratio of the official 2022 SSI federal benefit
rates. The benchmark is user-adjustable from zero through the 2022 federal
maximum of $841 per month.

## Re-entry earnings

For a non-retired respondent or spouse with zero reported wage income, use a
weighted median positive wage from SCF peers in the same sex and age bucket as
the re-entry wage. Apply the existing non-earner re-entry probability to that
wage stream. This is an SCF-calibrated proxy, not an observed wage or a claim
that every person returns to work.

Adults at or above the model retirement age remain at zero labor income; their
Social Security, DB pension, and income-security floor streams are considered
separately.

## Reporting and limits

The comprehensive-resource total will include a separately visible
`income_security_floor` component. The Methodology page will publish the
benchmark, formula, source, adult-count scaling, cash-flow exclusions, and
warnings that the model lacks direct disability, transfer-recipient, child, and
state-program eligibility data.

The sidebar exposes a monthly floor benchmark: $0 for the no-floor sensitivity,
$622 for the recommended average-payment baseline, and $841 for the federal
maximum sensitivity. The home and age pages retain the two-state comparison,
but clarify that the broad state includes the scenario-based floor.
