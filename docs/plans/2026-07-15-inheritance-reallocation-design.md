# Inheritance Reallocation Design

## Decision

Add a separately labeled **intergenerational reallocation** component to the
continuation-resource measure. It assigns a present value of explicitly
reported expected inheritances to recipient families and subtracts the same
weighted present value from statistically eligible donor families. It does not
increase aggregate national resources.

This is a lifetime-resource scenario, not a measure of present legal ownership,
probate entitlement, or a prediction of any particular family transfer.

## Why this model

The existing continuation measure values a family's future labor income and
retirement cash flows. A family that reports a substantial expected inheritance
can also have additional economic security, even though the asset is currently
owned by another family. Ignoring that expectation is asymmetric in a
lifetime-resource measure.

Simply multiplying an older owner's net worth by survival probability would be
wrong: current assets remain marketable and under the owner's control until a
transfer occurs. Counting a recipient's expected inheritance without an offset
would also be wrong: it would count the same existing asset twice. The model
therefore reallocates, rather than discounts or creates, existing net worth.

## Available SCF inputs

The 2022 full public SCF supplies the following respondent-family fields:

- `X5819`: whether the family expects a substantial future inheritance or asset
  transfer;
- `X5821`: the amount the family expects; and
- `X5825`: whether the family expects to leave a sizable estate.

The public SCF does not link a recipient family to a donor family. It also does
not identify the expected transfer date, estate tax, care costs, charitable
bequests, sibling shares, or legal enforceability. Consequently, any donor
offset is an aggregate statistical allocation, not a parent-child match.

## Chosen approach: constrained aggregate reallocation

### Recipient claim

For each family reporting `X5819 = yes`, let `A_i` be the positive reported
expected amount. With a user-visible horizon `H` and the existing real discount
rate `r`, the initial claim is:

```text
claim_i = A_i / (1 + r)^H
```

The default horizon is 15 years. It is a scenario control, not an estimate of a
respondent's parent's age or a forecast of probate timing. The base model adds
no invented probability haircut: the respondent's reported expectation is the
observable input. The methodology page will make this limitation prominent.

### Eligible donor capacity

For each family with positive conventional net worth `W_j`, a direct affirmative
estate expectation (`X5825 = yes`), and available respondent age and sex, define
an age-sensitive capacity:

```text
capacity_j = W_j × P(death within H years | respondent age, sex)
```

The probability comes from the existing SSA period life table. This makes an
otherwise identical older estate-intending family supply more near-term expected
transfer capacity than a younger one. Families reporting `possibly` or `no` are
not donor candidates in the default scenario; this avoids an arbitrary partial
estate-intent weight.

### Conservation and funding cap

Let `C` be the SCF-weighted total recipient claim and `D` the SCF-weighted total
donor capacity. The reallocated amount is:

```text
R = min(C, D)
recipient credit_i = claim_i × R / C
donor reserve_j = capacity_j × R / D
```

All weighted recipient credits therefore equal all weighted donor reserves.
Neither a donor reserve nor the reallocated total can exceed the model's stated
capacity. If no donor capacity is available, no inheritance credit is granted.
The calculation retains a full audit record of the unallocated recipient claim.

At the default 15-year horizon, the 2022 SCF's approximately $17.6 trillion of
reported nominal expected inheritances has a roughly $10.5 trillion real present
value at a 3.5% discount rate. The affirmative-estate, mortality-weighted donor
capacity is roughly $42.2 trillion, so the funding cap does not bind in the
baseline. These are diagnostic estimates, not externally validated forecasts.

## Components and accounting

The continuation resource total will add two explicit terms:

```text
inheritance recipient credit
− estate donor reserve
```

The net national effect is zero, apart from floating-point rounding. Existing
conventional net worth remains unmodified in the conventional chart. The new
component appears only in the continuation-resource scenario.

The model does not add dividend, rent, business-income, or capital-gain streams
on top of the inheritance credit. Those expected returns are already embedded in
the market value of the current asset. It also does not deduct taxes, medical
spending, consumption, charitable gifts, or unobserved heirs, because the public
SCF cannot identify them well enough for a family-level estimate.

## Alternatives considered

1. **Recipient-only expected inheritance.** Simple and useful for a private
   security score, but double-counts current donor assets in a national wealth
   total. Rejected for the headline distribution.
2. **Exact parent-child transfer links.** Economically preferable, but not
   available in the public cross-sectional SCF. Not feasible.
3. **Full cohort estate-flow simulation.** Could move all older wealth to later
   cohorts, but would require assumptions about unobserved heirs, consumption,
   care expenses, taxes, gifts, and family structure. Too speculative for the
   public baseline.

## Interface and disclosure

- Add a sidebar control: **Expected inheritance horizon**, 5–30 years,
  default 15.
- State plainly that this is a constrained aggregate reallocation and does not
  observe parent-child links or legal claims.
- Add component formulas, source-field lineage, assumptions, funding-cap
  diagnostics, and exclusions to the Methodology page.
- Include the component in the home distribution shift and the age-sliced view,
  with the recipient credit and donor reserve available in decomposition/audit
  output.

## Tests and acceptance criteria

1. Recipient claims discount reported positive `X5821` amounts by the selected
   horizon and real discount rate.
2. At positive capacity, weighted recipient credits equal weighted donor
   reserves within a tight numerical tolerance.
3. Zero donor capacity produces zero credits and an explicit unallocated-claim
   diagnostic.
4. Donor reserve never exceeds donor capacity or positive net worth.
5. For otherwise equal estate-intending donors, higher mortality produces a
   larger reserve.
6. Missing or inapplicable inheritance fields safely yield zero components.
7. The full test suite, lint, compilation, and Streamlit smoke tests pass.
