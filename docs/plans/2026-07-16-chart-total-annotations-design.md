# Chart total annotations design

## Goal

Make the dollar scale of each distribution segment visible without replacing the existing percentage-based comparison.

## Presentation

Each quantile annotation beneath the paired 100% bars will show its conventional and all-modeled-resources share followed immediately by that segment's weighted dollar total in trillions:

```text
Bottom 50%
2.2% [$1.8T] → 12.6% [$30.4T]
+10.4 pp
```

This retains the existing percentage-point change. Values use one decimal trillion formatting and the same weighted totals already shown in each Plotly hover tooltip.

## Scope

The shared `distribution_shift_figure` produces both Home and Age slicing charts, so one chart-helper change applies the same format to all views. No calculation, ranking, tooltip source, or methodology audit value changes.

## Legibility safeguards

Totals remain in the chart annotations rather than inside bar segments. This avoids hiding small groups, preserves the 100%-share geometry, and maintains a direct conventional-to-modeled comparison. The existing chart height and lower annotation margin will be adjusted only if visual verification shows the added line is clipped.

## Verification

The chart unit test will assert bracketed trillion totals for both states and retain the percentage-point comparison assertion. Browser verification will inspect Home and an Age slicing panel at the active baseline assumptions.
