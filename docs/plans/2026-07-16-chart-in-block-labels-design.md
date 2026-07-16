# Chart in-block labels design

## Goal

Make the distribution charts direct and static: show each segment's share and weighted total in the segment itself, without a bottom comparison strip or hover tooltips.

## Presentation

Each sufficiently wide stacked segment is labeled in the form:

```text
12.6% [$39.9T]
```

The existing lower annotations that compare states and show percentage-point changes are removed. Plotly hover content is disabled for these charts; the visible label is the chart's only per-segment value display.

## Legibility rule

The chart already suppresses labels for segments below 5.5% of the bar. That threshold remains, because a complete share-and-total label cannot fit safely in a narrow segment. Those segments stay visually present and retain their legend identity, but carry no overlaid text.

## Scope

The shared distribution-shift chart helper powers both Home and all Age slicing panels, so this single presentation change applies consistently throughout the public report. It does not alter data, calculations, ranking, provenance, or methodology tables.

## Verification

Chart tests will confirm the in-block format, absence of lower annotations, and disabled hover behavior. A live check will confirm the shared helper produces labels on Home and all age panels without reintroducing bottom adjustment text.
