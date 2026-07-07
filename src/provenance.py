from __future__ import annotations

import pandas as pd

from src.data_sources import FED_EXPECTED_FUTURE_INCOME_URL, FED_HUMAN_WEALTH_MODEL_URL, SCF_2022_EXTRACT_ZIP_URL
from src.real_data import SCF_2022_DATASET_LABEL


ASSUMPTION_SOURCE = "User-adjustable model assumption shown in the sidebar"
DEFINITION_SOURCE = "Report definition"
COMPUTED_SCF_SOURCE = (
    "Computed from Federal Reserve 2022 SCF public summary extract fields networth, wageinc, age, and wgt"
)


def chart_source_caption() -> str:
    return (
        f"Source: {COMPUTED_SCF_SOURCE}. Priced wealth uses networth x wgt. "
        "Full wealth adds discounted positive wageinc using the sidebar assumptions."
    )


def assumption_source_caption() -> str:
    return (
        f"Source for sidebar numbers: {ASSUMPTION_SOURCE}. These are scenario controls, "
        "not empirical Fed estimates."
    )


def table_source_note() -> str:
    return (
        "Each numeric row is sourced in the Source column. SCF-derived numbers are weighted with wgt; "
        "assumption-driven numbers use the visible sidebar settings."
    )


def computed_scf_row_source() -> str:
    return "SCF 2022: networth, wageinc, age, wgt; full-wealth values also use sidebar assumptions"


def build_number_source_table(assumptions: dict[str, float | int]) -> pd.DataFrame:
    rows = [
        {
            "Number category": "Survey year and raw household microdata",
            "Source": SCF_2022_DATASET_LABEL,
            "Method": f"Downloaded from {SCF_2022_EXTRACT_ZIP_URL}; app reads rscfp2022.dta.",
        },
        {
            "Number category": "Household counts and population shares",
            "Source": SCF_2022_DATASET_LABEL,
            "Method": "Sum SCF household weight field wgt within each net-worth quantile.",
        },
        {
            "Number category": "Priced wealth dollars and shares",
            "Source": SCF_2022_DATASET_LABEL,
            "Method": "Sum networth x wgt within each quantile; divide by national weighted networth total for shares.",
        },
        {
            "Number category": "Discounted future earnings dollars and shares",
            "Source": f"{SCF_2022_DATASET_LABEL} plus sidebar assumptions",
            "Method": (
                "Use positive wageinc, age, and wgt. Present value uses "
                f"discount_rate={assumptions['discount_rate']}, "
                f"wage_growth={assumptions['wage_growth']}, "
                f"retirement_age={assumptions['retirement_age']}, "
                f"employment_probability={assumptions['employment_probability']}, "
                f"tax_rate={assumptions['tax_rate']}."
            ),
        },
        {
            "Number category": "Full wealth dollars and shares",
            "Source": f"{SCF_2022_DATASET_LABEL} plus sidebar assumptions",
            "Method": "Priced wealth plus discounted future earnings; weighted by wgt for totals and shares.",
        },
        {
            "Number category": "Discount rate",
            "Source": ASSUMPTION_SOURCE,
            "Method": f"Sidebar value: discount_rate={assumptions['discount_rate']}.",
        },
        {
            "Number category": "Real wage growth",
            "Source": ASSUMPTION_SOURCE,
            "Method": f"Sidebar value: wage_growth={assumptions['wage_growth']}.",
        },
        {
            "Number category": "Retirement age",
            "Source": ASSUMPTION_SOURCE,
            "Method": f"Sidebar value: retirement_age={assumptions['retirement_age']}.",
        },
        {
            "Number category": "Employment probability",
            "Source": ASSUMPTION_SOURCE,
            "Method": f"Sidebar value: employment_probability={assumptions['employment_probability']}.",
        },
        {
            "Number category": "Flat tax haircut",
            "Source": ASSUMPTION_SOURCE,
            "Method": f"Sidebar value: tax_rate={assumptions['tax_rate']}.",
        },
        {
            "Number category": "Human-capital liquidity weight",
            "Source": ASSUMPTION_SOURCE,
            "Method": f"Sidebar value: liquidity_weight={assumptions['liquidity_weight']}.",
        },
        {
            "Number category": "Wealth quantile breakpoints",
            "Source": DEFINITION_SOURCE,
            "Method": "Report-defined household net-worth groups: bottom 50, 50-90, 90-99, 99-99.9, top 0.1.",
        },
        {
            "Number category": "Age bucket breakpoints",
            "Source": DEFINITION_SOURCE,
            "Method": "Report-defined age groups: under 25, 25-34, 35-44, 45-54, 55-64, 65-74, 75+.",
        },
        {
            "Number category": "Human-capital methodology",
            "Source": "Federal Reserve research links",
            "Method": (
                "Present-value treatment is cited as methodology context, not as an official Fed wealth statistic: "
                f"{FED_EXPECTED_FUTURE_INCOME_URL}; {FED_HUMAN_WEALTH_MODEL_URL}."
            ),
        },
    ]
    return pd.DataFrame(rows)
