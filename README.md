# Comprehensive Household Resources

Interactive Streamlit report comparing conventional family net worth with modeled comprehensive resources that can include future labor earnings and retirement claims.

## Core Concept

Conventional wealth statistics measure recognized assets minus liabilities. Modeled comprehensive resources answer a different question by adding explicitly estimated, nonmarketable future payment streams. The report keeps conventional SCF net worth intact and presents expanded measures as scenario-dependent alternatives rather than replacements for the standard balance-sheet measure.

The app does not claim that human capital is the same as stocks, bonds, real estate, or businesses. Human capital cannot be sold, transferred, borrowed against in the same way, or inherited. The purpose is to compare valuation frameworks and lifecycle effects, not to deny measured asset inequality.

## Current MVP

The app currently includes:

- A working multipage Streamlit interface.
- Real Federal Reserve 2022 SCF public summary extract data for the interactive charts.
- A total-country distribution view that groups households by SCF-weighted net-worth quantiles.
- Human-capital present-value calculations.
- Weighted-statistics utilities for SCF-style survey data.
- Fed SCF downloader/loader and Fed DFA source support.
- Source-data page with official links and a number-source audit table.
- Unit tests for formulas, weighted statistics, and real-data processing.

## Official Sources

- Federal Reserve Distributional Financial Accounts: https://www.federalreserve.gov/releases/z1/dataviz/dfa/index.html
- Federal Reserve 2022 Survey of Consumer Finances: https://www.federalreserve.gov/econres/scfindex.htm
- FRED COE, National Income: Compensation of Employees, Paid: https://fred.stlouisfed.org/series/COE
- Census CPS ASEC: https://www.census.gov/programs-surveys/cps/data/datasets.html
- Census ACS PUMS: https://www.census.gov/programs-surveys/acs/microdata.html
- BLS CPS earnings tables: https://www.bls.gov/cps/earnings.htm
- Federal Reserve IFDP, expected future income and human wealth concepts: https://www.federalreserve.gov/pubs/ifdp/2009/971/ifdp971.htm
- Federal Reserve FEDS, human wealth in a total-wealth model: https://www.federalreserve.gov/pubs/feds/2010/201056/index.html
- Federal Reserve FEDS, comprehensive wealth and PV earnings concepts: https://www.federalreserve.gov/econres/feds/files/2026007pap.pdf

## Methodology

Traditional wealth:

```text
traditional_net_worth = total_assets - total_liabilities
```

Human capital:

```text
human_capital = current_labor_income
    * employment_probability
    * (1 - tax_rate)
    * annuity_factor(years_to_retirement, wage_growth_rate, discount_rate)
```

Combined real wealth:

```text
combined_real_wealth = traditional_net_worth + human_capital
```

Country-level quantile shares:

```text
weighted_household_wealth = household_wealth * SCF_household_weight
quantile_total_wealth = sum(weighted_household_wealth for households in quantile)
quantile_wealth_share = quantile_total_wealth / sum(all_quantile_total_wealth)
```

The headline comparison is:

```text
priced wealth share owned by the top 1%
vs.
full wealth share owned by the top 1%
```

The app uses SCF `networth` for priced wealth and positive SCF `wageinc` as the labor-income proxy for discounted future earnings. The SCF public summary extract includes multiple implicates; the supplied SCF weights sum to the national household count across the extract and are used directly.

Liquidity-adjusted real wealth:

```text
liquidity_adjusted_real_wealth =
    traditional_net_worth + liquidity_weight_human_capital * human_capital
```

## Number Provenance

Every displayed number should map to one of these categories:

- SCF input data: survey year, household weights, age, wage income, and net worth come from the Federal Reserve 2022 SCF public summary extract.
- SCF-derived calculations: household counts, quantile population shares, priced wealth totals, and priced wealth shares are computed from `wgt` and `networth`.
- SCF plus model assumptions: discounted future earnings and full wealth are computed from positive `wageinc`, `age`, `wgt`, and the visible sidebar assumptions.
- Model assumptions: discount rate, real wage growth, retirement age, employment probability, tax haircut, and liquidity weight are scenario controls shown in the sidebar.
- Report definitions: age buckets and wealth-quantile breakpoints are defined by the report and shown in the source audit.

## Run Locally

```bash
uv sync
uv run streamlit run Home.py
```

## Test

```bash
uv run pytest -q
```

## Streamlit Community Cloud Deployment

1. Push this repository to GitHub.
2. Go to https://share.streamlit.io/.
3. Sign in with GitHub.
4. Create a new app.
5. Select this repository.
6. Set the main file path to `Home.py`.
7. Deploy.

Dependency management uses `uv` through `pyproject.toml` and `uv.lock`. Streamlit Community Cloud recognizes `uv.lock` as a dependency file, so this repo intentionally does not include `requirements.txt`.

## Limitations

1. Traditional net worth and human capital are different kinds of wealth.
2. Marketable assets are liquid, transferable, borrowable, and inheritable.
3. Human capital is personal, risky, nontransferable, partly taxable, and sensitive to health and labor-market risk.
4. Human-capital estimates depend heavily on discount rates, wage growth, employment probability, retirement age, and taxes.
5. The current human-capital estimate uses SCF wage income only; a fuller model should incorporate employment probabilities, earnings trajectories, education, occupation, health, and demographic transitions from CPS/ACS-style data.

## License

Code is available under the Apache License 2.0. Official source datasets retain their providers' terms and attribution requirements.
