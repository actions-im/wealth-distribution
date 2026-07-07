# Real Wealth Distribution

Interactive Streamlit report showing how standard wealth inequality arguments compare mismatched ledgers: capitalized future cash flows embedded in asset prices versus present-only household balance sheets that assign future labor earnings a value of zero.

## Core Concept

Standard wealth distribution statistics measure marketable net worth: assets minus debts. But stock and business wealth already reflect expectations about future cash flows, while future labor earnings are usually omitted from household wealth statistics. This report keeps marketable net worth intact, then adds a separate human-capital layer to compare future cash-flow claims more consistently.

The app does not claim that human capital is the same as stocks, bonds, real estate, or businesses. Human capital cannot be sold, transferred, borrowed against in the same way, or inherited. The purpose is to compare valuation frameworks and lifecycle effects, not to deny measured asset inequality.

## Current MVP

The app currently includes:

- A working multipage Streamlit interface.
- Real Federal Reserve 2022 SCF public summary extract data for the interactive charts.
- A total-country distribution view that groups households by SCF-weighted net-worth quantiles.
- Human-capital present-value calculations.
- Weighted-statistics utilities for SCF-style survey data.
- Fed SCF downloader/loader and Fed DFA source support.
- Source-data page with official links.
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
share of marketable net worth owned by the top 1% under the standard ledger
vs.
share of combined marketable wealth + discounted future labor earnings owned by the top 1%
```

The app uses SCF `networth` for the standard ledger and positive SCF `wageinc` as the labor-income proxy for discounted future earnings. The SCF public summary extract includes multiple implicates; the supplied SCF weights sum to the national household count across the extract and are used directly.

Liquidity-adjusted real wealth:

```text
liquidity_adjusted_real_wealth =
    traditional_net_worth + liquidity_weight_human_capital * human_capital
```

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

Add a license before publishing the repository.
