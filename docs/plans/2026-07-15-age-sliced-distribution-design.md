# Age-sliced distribution design

## Decision

Add a Streamlit page that repeats the report's two-state distribution view for
six respondent-age buckets: `<25`, `25–34`, `35–44`, `45–54`, `55–64`, and
`65+`.

Each age bucket is ranked independently for each state:

- **Conventional net worth** is ranked by net worth within that age bucket.
- **All modeled future resources** is ranked by continuation resources within
  that age bucket.

The four displayed groups remain Bottom 50%, Next 40%, Next 9%, and Top 1%.
The two upper-tail SCF groups are combined for Top 1%, exactly as on the
headline distribution-shift view.

## User experience

The page opens with a concise explanation that this is a family-level,
respondent-age view. It explicitly warns that Bottom 50% refers to families
within the selected age bucket, rather than a nationally fixed set of families.

Each age bucket is rendered as a bordered panel containing its label, a concise
weighted-family-count and all-resource-total caption, and the existing paired,
100%-stacked distribution-shift visualization. Six panels are arranged in a
two-column grid for direct cross-age comparison.

## Data and safeguards

The aggregation helper will call the existing measure-specific ranking logic
after filtering to one age bucket. This prevents national ranks from leaking
into the age view. It will return both the four-group share table used by the
chart and age-bucket context statistics.

The page reuses the cached comprehensive SCF loader and visible model
assumptions. Its source caption directs readers to the Methodology and Source
Data pages, rather than presenting modeled values as official Federal Reserve
statistics.

## Testing

Unit tests verify that every age bucket produces two states, four display
groups, and 100% shares within each state. A Streamlit AppTest verifies the
page title, warning, six age panels, and rendered Plotly charts.
