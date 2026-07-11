from __future__ import annotations

from datetime import UTC, datetime

import pandas as pd

from src.source_manifest import load_source_registry


FED_DFA_ZIP_URL = "https://www.federalreserve.gov/releases/z1/dataviz/download/zips/dfa.zip"
SCF_2022_EXTRACT_ZIP_URL = "https://www.federalreserve.gov/econres/files/scfp2022s.zip"
FRED_COE_URL = "https://fred.stlouisfed.org/series/COE"
CENSUS_CPS_URL = "https://www.census.gov/programs-surveys/cps/data/datasets.html"
CENSUS_ACS_PUMS_URL = "https://www.census.gov/programs-surveys/acs/microdata.html"
BLS_CPS_EARNINGS_URL = "https://www.bls.gov/cps/earnings.htm"
STREAMLIT_QUICKSTART_URL = (
    "https://github.com/streamlit/docs/blob/main/content/deploy/community-cloud/get-started/quickstart.md"
)
FED_EXPECTED_FUTURE_INCOME_URL = "https://www.federalreserve.gov/pubs/ifdp/2009/971/ifdp971.htm"
FED_HUMAN_WEALTH_MODEL_URL = "https://www.federalreserve.gov/pubs/feds/2010/201056/index.html"
FED_COMPREHENSIVE_WEALTH_URL = "https://www.federalreserve.gov/econres/feds/files/2026007pap.pdf"


OFFICIAL_SOURCES = load_source_registry()


def source_table() -> pd.DataFrame:
    retrieved = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    return pd.DataFrame(
        [
            {
                "Dataset": "Federal Reserve Distributional Financial Accounts",
                "Provider": "Federal Reserve Board",
                "URL": FED_DFA_ZIP_URL,
                "Version used": "Source link only; not used directly in current charts",
                "Used for": "Official aggregate household balance-sheet wealth context",
                "Limitations": "Aggregates marketable balance-sheet wealth, not human capital",
                "Retrieved": retrieved,
            },
            {
                "Dataset": "2022 Survey of Consumer Finances extract",
                "Provider": "Federal Reserve Board",
                "URL": SCF_2022_EXTRACT_ZIP_URL,
                "Version used": "2022 public summary extract",
                "Used for": "Household age, income, net worth, and survey-weight structure",
                "Limitations": "Multiple implicates and complex survey design need careful treatment",
                "Retrieved": retrieved,
            },
            {
                "Dataset": "National Income: Compensation of Employees, Paid (COE)",
                "Provider": "BEA via FRED",
                "URL": FRED_COE_URL,
                "Version used": "Source link only; not used directly in current charts",
                "Used for": "National labor-compensation sanity check",
                "Limitations": "Aggregate flow, not a household-level lifetime-income estimate",
                "Retrieved": retrieved,
            },
            {
                "Dataset": "CPS ASEC",
                "Provider": "U.S. Census Bureau",
                "URL": CENSUS_CPS_URL,
                "Version used": "Source link only; not used directly in current charts",
                "Used for": "Future age-income and employment-probability profiles",
                "Limitations": "Not included in MVP calculations",
                "Retrieved": retrieved,
            },
            {
                "Dataset": "ACS PUMS",
                "Provider": "U.S. Census Bureau",
                "URL": CENSUS_ACS_PUMS_URL,
                "Version used": "Source link only; not used directly in current charts",
                "Used for": "Future detailed income, education, occupation, and geography splits",
                "Limitations": "Not included in MVP calculations",
                "Retrieved": retrieved,
            },
            {
                "Dataset": "CPS earnings tables",
                "Provider": "Bureau of Labor Statistics",
                "URL": BLS_CPS_EARNINGS_URL,
                "Version used": "Source link only; not used directly in current charts",
                "Used for": "Public-facing validation of earnings by age and demographics",
                "Limitations": "Published tables are less flexible than microdata",
                "Retrieved": retrieved,
            },
            {
                "Dataset": "Consumption Response to Expected Future Income",
                "Provider": "Federal Reserve Board IFDP research",
                "URL": FED_EXPECTED_FUTURE_INCOME_URL,
                "Version used": "2009 IFDP research paper",
                "Used for": "Methodological support for human wealth and expected future income concepts",
                "Limitations": "Research concept, not an official DFA wealth-distribution statistic",
                "Retrieved": retrieved,
            },
            {
                "Dataset": "Capital Taxation with Entrepreneurial Risk",
                "Provider": "Federal Reserve Board FEDS research",
                "URL": FED_HUMAN_WEALTH_MODEL_URL,
                "Version used": "2010 FEDS research paper",
                "Used for": "Methodological support for human wealth as part of total wealth",
                "Limitations": "Macroeconomic model, not a household survey estimate",
                "Retrieved": retrieved,
            },
            {
                "Dataset": "Inequality in Comprehensive Wealth",
                "Provider": "Federal Reserve Board FEDS research",
                "URL": FED_COMPREHENSIVE_WEALTH_URL,
                "Version used": "2026 FEDS research paper",
                "Used for": "Methodological support for comprehensive wealth and PV earnings concepts",
                "Limitations": "Research paper; does not change official DFA marketable-wealth measures",
                "Retrieved": retrieved,
            },
        ]
    )
