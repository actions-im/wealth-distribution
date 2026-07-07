from __future__ import annotations

import pandas as pd

from src.config import AGE_BUCKETS, WEALTH_QUANTILES
from src.human_capital import estimate_human_capital


AGE_MIDPOINTS = {
    "<25": 23,
    "25-34": 30,
    "35-44": 40,
    "45-54": 50,
    "55-64": 60,
    "65-74": 70,
    "75+": 78,
}

PLACEHOLDER_HOUSEHOLD_COUNT = 132_000_000

BASE_LABOR_INCOME = {
    "<25": 32_000,
    "25-34": 65_000,
    "35-44": 90_000,
    "45-54": 102_000,
    "55-64": 88_000,
    "65-74": 30_000,
    "75+": 8_000,
}

BASE_NET_WORTH = {
    "<25": 8_000,
    "25-34": 55_000,
    "35-44": 170_000,
    "45-54": 320_000,
    "55-64": 520_000,
    "65-74": 620_000,
    "75+": 500_000,
}

QUANTILE_MULTIPLIER = {
    "Bottom 50%": 0.10,
    "50-90%": 1.0,
    "90-99%": 7.0,
    "99-99.9%": 70.0,
    "Top 0.1%": 450.0,
}

INCOME_MULTIPLIER = {
    "Bottom 50%": 0.70,
    "50-90%": 1.0,
    "90-99%": 1.55,
    "99-99.9%": 2.10,
    "Top 0.1%": 3.00,
}

AGE_POPULATION_SHARE = {
    "<25": 0.08,
    "25-34": 0.17,
    "35-44": 0.17,
    "45-54": 0.16,
    "55-64": 0.16,
    "65-74": 0.14,
    "75+": 0.12,
}

QUANTILE_POPULATION_SHARE = {
    "Bottom 50%": 0.50,
    "50-90%": 0.40,
    "90-99%": 0.09,
    "99-99.9%": 0.009,
    "Top 0.1%": 0.001,
}


def build_sample_household_data(
    discount_rate: float,
    wage_growth: float,
    retirement_age: int,
    employment_probability: float,
    tax_rate: float,
    liquidity_weight: float,
) -> pd.DataFrame:
    rows = []
    for age_group in AGE_BUCKETS:
        age = AGE_MIDPOINTS[age_group]
        for quantile in WEALTH_QUANTILES:
            net_worth = BASE_NET_WORTH[age_group] * QUANTILE_MULTIPLIER[quantile]
            labor_income = BASE_LABOR_INCOME[age_group] * INCOME_MULTIPLIER[quantile]
            human_capital = estimate_human_capital(
                current_labor_income=labor_income,
                age=age,
                retirement_age=retirement_age,
                wage_growth=wage_growth,
                discount_rate=discount_rate,
                employment_probability=employment_probability,
                tax_rate=tax_rate,
            )
            rows.append(
                {
                    "age_group": age_group,
                    "age": age,
                    "wealth_quantile": quantile,
                    "age_population_share": AGE_POPULATION_SHARE[age_group],
                    "quantile_population_share": QUANTILE_POPULATION_SHARE[quantile],
                    "household_population_share": AGE_POPULATION_SHARE[age_group]
                    * QUANTILE_POPULATION_SHARE[quantile],
                    "traditional_net_worth": net_worth,
                    "labor_income": labor_income,
                    "human_capital": human_capital,
                    "combined_real_wealth": net_worth + human_capital,
                    "liquidity_adjusted_real_wealth": net_worth
                    + liquidity_weight * human_capital,
                }
            )

    return pd.DataFrame(rows)


def aggregate_by_age(data: pd.DataFrame) -> pd.DataFrame:
    metrics = [
        "traditional_net_worth",
        "human_capital",
        "combined_real_wealth",
        "liquidity_adjusted_real_wealth",
    ]
    return data.groupby("age_group", sort=False)[metrics].median().reset_index()


def aggregate_by_quantile(data: pd.DataFrame) -> pd.DataFrame:
    metrics = [
        "traditional_net_worth",
        "human_capital",
        "combined_real_wealth",
        "liquidity_adjusted_real_wealth",
    ]
    return data.groupby("wealth_quantile", sort=False)[metrics].median().reset_index()


def aggregate_country_distribution_by_quantile(data: pd.DataFrame) -> pd.DataFrame:
    metrics = [
        "traditional_net_worth",
        "human_capital",
        "combined_real_wealth",
        "liquidity_adjusted_real_wealth",
    ]
    working = data.copy()
    for metric in metrics:
        working[f"{metric}_total"] = (
            working[metric] * working["household_population_share"] * PLACEHOLDER_HOUSEHOLD_COUNT
        )

    totals = (
        working.groupby("wealth_quantile", sort=False)
        .agg(
            population_share=("household_population_share", "sum"),
            household_count=("household_population_share", lambda value: value.sum() * PLACEHOLDER_HOUSEHOLD_COUNT),
            traditional_net_worth_total=("traditional_net_worth_total", "sum"),
            human_capital_total=("human_capital_total", "sum"),
            combined_real_wealth_total=("combined_real_wealth_total", "sum"),
            liquidity_adjusted_real_wealth_total=("liquidity_adjusted_real_wealth_total", "sum"),
        )
        .reset_index()
    )

    for metric in metrics:
        total_column = f"{metric}_total"
        share_column = f"{metric}_share"
        grand_total = totals[total_column].sum()
        totals[share_column] = totals[total_column] / grand_total if grand_total else 0.0

    totals["human_capital_minus_marketable_share"] = (
        totals["human_capital_share"] - totals["traditional_net_worth_share"]
    )
    totals["combined_minus_marketable_share"] = (
        totals["combined_real_wealth_share"] - totals["traditional_net_worth_share"]
    )
    return totals
