# Distribution shift plot and methodology page design

## Objective

Replace the home-page grouped five-quantile chart with a clearer two-state visualization showing how the distribution changes when modeled future labor earnings, Social Security, and defined-benefit pensions are added to conventional net worth. Add a public methodology page that gives the source and calculation lineage for every displayed number.

## Primary visual

The main chart will compare:

1. **Conventional net worth** — SCF assets minus liabilities.
2. **All modeled future resources** — conventional net worth plus continuation labor earnings, continuation Social Security, and continuation defined-benefit pension wealth.

Both sides are independently ranked under their own measure. The chart will not use flows or Sankey ribbons because independently ranked groups do not contain identical households.

The distribution will be collapsed into four readable groups:

- Bottom 50%
- Next 40% (50th–90th percentiles)
- Next 9% (90th–99th percentiles)
- Top 1% (99th–100th percentiles)

Two horizontal 100% stacked bars will use stable colors across states. Each sufficiently large segment will contain its share as a direct label. A change strip below the bars will show the before value, after value, and percentage-point change for every group. Hover content will identify the measure, rank definition, resource share, weighted total, and household share.

The title will be “How including future resources changes the distribution.” Supporting copy will state exactly which future resources are included and will preserve the lifecycle/nonmarketability warning.

## Data transformation

The chart will derive four-group rows from the existing metric-specific distribution output:

- Bottom 50% remains unchanged.
- 50–90% becomes Next 40%.
- 90–99% becomes Next 9%.
- 99–99.9% and Top 0.1% are summed into Top 1%.

No headline values will be hard-coded. Shares, weighted totals, and changes will be calculated from the active sidebar assumptions on each scenario refresh.

## Methodology page

The app will gain a dedicated `Methodology` page organized around an auditable number lineage:

- Measure definitions
- Displayed-number calculation table
- Component formulas
- Source field map
- Assumptions and scenario controls
- Double-count protections
- Exclusions and limitations
- Source registry with canonical URLs and vintages

The number calculation table will cover every home-page output: the four conventional shares, four comprehensive shares, percentage-point changes, and weighted totals. Each row will identify the source columns, formula, rank basis, unit, and whether the number is official or model-derived.

The page will use the existing source registry and methodology text rather than duplicating unmaintainable prose. Source URLs will be clickable. Formula and provenance helpers will live in `src/` so they can be tested independently of Streamlit.

## Visual language

- Bottom 50%: deep teal
- Next 40%: light teal
- Next 9%: muted sand
- Top 1%: warm rust
- Conventional state: restrained neutral framing
- Comprehensive state: stronger framing without implying it is the uniquely correct definition

The chart will use sentence case, direct labels, minimal grid decoration, and generous whitespace. It will remain legible at common laptop widths and degrade safely on narrower layouts.

## Testing

Tests will verify:

- four-group aggregation arithmetic;
- both states sum to 100%;
- Top 1% combines the upper two detailed quantiles;
- change labels are calculated rather than hard-coded;
- chart traces and labels use the approved two states and four groups;
- methodology coverage includes every number category and required provenance fields;
- the Streamlit app and methodology page render without exceptions;
- prohibited misleading flow terminology is absent.

Visual verification will inspect the running app at desktop width and confirm labels, hierarchy, hover behavior, and absence of overlap or clipping.
