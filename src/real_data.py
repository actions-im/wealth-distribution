from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd

from src.config import AGE_BUCKETS, WEALTH_QUANTILES
from src.human_capital import estimate_human_capital
from src.scf_loader import download_scf_extract, load_scf_extract
from src.weighted_stats import assign_weighted_quantile_group, weighted_median


SCF_2022_DATASET_LABEL = "Federal Reserve 2022 SCF public summary extract"
SCF_2022_DATA_NOTE = (
    "Charts use the Federal Reserve 2022 Survey of Consumer Finances public summary extract. "
    "Rows are weighted with SCF household weights; future earnings use positive SCF wage income "
    "as the labor-income proxy."
)

WEALTH_QUANTILE_GROUPS = [
    ("Bottom 50%", 0.0, 0.5),
    ("50-90%", 0.5, 0.9),
    ("90-99%", 0.9, 0.99),
    ("99-99.9%", 0.99, 0.999),
    ("Top 0.1%", 0.999, 1.0),
]

REPORT_METRICS = [
    "traditional_net_worth",
    "human_capital",
    "combined_real_wealth",
    "liquidity_adjusted_real_wealth",
]


def load_real_wealth_household_data(
    discount_rate: float,
    wage_growth: float,
    retirement_age: int,
    employment_probability: float,
    tax_rate: float,
    liquidity_weight: float,
    raw_dir: Path = Path("data/raw"),
) -> pd.DataFrame:
    zip_path = raw_dir / "scf_2022_extract.zip"
    if not zip_path.exists():
        zip_path = download_scf_extract(raw_dir=raw_dir)

    return build_real_wealth_household_data(
        load_scf_extract(zip_path),
        discount_rate=discount_rate,
        wage_growth=wage_growth,
        retirement_age=retirement_age,
        employment_probability=employment_probability,
        tax_rate=tax_rate,
        liquidity_weight=liquidity_weight,
    )


def build_real_wealth_household_data(
    scf_rows: pd.DataFrame | Iterable[dict],
    discount_rate: float,
    wage_growth: float,
    retirement_age: int,
    employment_probability: float,
    tax_rate: float,
    liquidity_weight: float,
) -> pd.DataFrame:
    data = _normalize_input_rows(scf_rows)
    data["wealth_quantile"] = assign_weighted_quantile_group(
        data["traditional_net_worth"],
        data["household_weight"],
        WEALTH_QUANTILE_GROUPS,
    )
    data["wealth_quantile"] = pd.Categorical(data["wealth_quantile"], categories=WEALTH_QUANTILES, ordered=True)
    data["age_group"] = pd.Categorical(data["age"].map(age_group), categories=AGE_BUCKETS, ordered=True)

    data["human_capital"] = [
        estimate_human_capital(
            current_labor_income=labor_income,
            age=int(age),
            retirement_age=retirement_age,
            wage_growth=wage_growth,
            discount_rate=discount_rate,
            employment_probability=employment_probability,
            tax_rate=tax_rate,
        )
        for labor_income, age in zip(data["labor_income"], data["age"], strict=True)
    ]
    data["combined_real_wealth"] = data["traditional_net_worth"] + data["human_capital"]
    data["liquidity_adjusted_real_wealth"] = (
        data["traditional_net_worth"] + liquidity_weight * data["human_capital"]
    )
    data["household_population_share"] = data["household_weight"] / data["household_weight"].sum()
    return data


def aggregate_real_country_distribution_by_quantile(data: pd.DataFrame) -> pd.DataFrame:
    working = data.copy()
    for metric in REPORT_METRICS:
        working[f"{metric}_total"] = working[metric] * working["household_weight"]

    totals = (
        working.groupby("wealth_quantile", observed=False, sort=False)
        .agg(
            population_share=("household_population_share", "sum"),
            household_count=("household_weight", "sum"),
            traditional_net_worth_total=("traditional_net_worth_total", "sum"),
            human_capital_total=("human_capital_total", "sum"),
            combined_real_wealth_total=("combined_real_wealth_total", "sum"),
            liquidity_adjusted_real_wealth_total=("liquidity_adjusted_real_wealth_total", "sum"),
        )
        .reset_index()
    )
    totals["wealth_quantile"] = totals["wealth_quantile"].astype(str)

    for metric in REPORT_METRICS:
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
    return _sort_report_groups(totals)


def aggregate_real_by_age(data: pd.DataFrame) -> pd.DataFrame:
    return _weighted_metric_table(data, ["age_group"])


def aggregate_real_age_quantile_matrix(data: pd.DataFrame) -> pd.DataFrame:
    return _weighted_metric_table(data, ["age_group", "wealth_quantile"])


def age_group(age: int | float) -> str:
    if age < 25:
        return "<25"
    if age < 35:
        return "25-34"
    if age < 45:
        return "35-44"
    if age < 55:
        return "45-54"
    if age < 65:
        return "55-64"
    if age < 75:
        return "65-74"
    return "75+"


def _normalize_input_rows(scf_rows: pd.DataFrame | Iterable[dict]) -> pd.DataFrame:
    data = pd.DataFrame(scf_rows).copy()
    data.columns = [str(column).strip().lower() for column in data.columns]

    required_columns = {"wgt", "age", "wageinc", "networth"}
    missing_columns = required_columns - set(data.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"SCF rows are missing required columns: {missing}")

    if "scf_row_id" not in data.columns:
        data["scf_row_id"] = range(1, len(data) + 1)

    normalized = pd.DataFrame(
        {
            "scf_row_id": data["scf_row_id"],
            "household_weight": pd.to_numeric(data["wgt"], errors="coerce"),
            "age": pd.to_numeric(data["age"], errors="coerce"),
            "labor_income": pd.to_numeric(data["wageinc"], errors="coerce").clip(lower=0),
            "traditional_net_worth": pd.to_numeric(data["networth"], errors="coerce"),
        }
    ).dropna(subset=["household_weight", "age", "labor_income", "traditional_net_worth"])

    normalized = normalized[normalized["household_weight"] > 0].copy()
    if normalized.empty:
        raise ValueError("SCF rows did not contain any valid positive-weight households")

    return normalized


def _weighted_metric_table(data: pd.DataFrame, group_columns: list[str]) -> pd.DataFrame:
    rows = []
    for group_key, group in data.groupby(group_columns, observed=True, sort=False):
        if not isinstance(group_key, tuple):
            group_key = (group_key,)
        row = dict(zip(group_columns, group_key, strict=True))
        row["household_count"] = group["household_weight"].sum()
        for metric in REPORT_METRICS:
            row[metric] = weighted_median(group[metric], group["household_weight"])
        rows.append(row)

    result = pd.DataFrame(rows)
    for column in group_columns:
        result[column] = result[column].astype(str)
    return _sort_report_groups(result)


def _sort_report_groups(data: pd.DataFrame) -> pd.DataFrame:
    sorted_data = data.copy()
    sort_columns = []
    if "age_group" in sorted_data.columns:
        sorted_data["age_group"] = pd.Categorical(sorted_data["age_group"], categories=AGE_BUCKETS, ordered=True)
        sort_columns.append("age_group")
    if "wealth_quantile" in sorted_data.columns:
        sorted_data["wealth_quantile"] = pd.Categorical(
            sorted_data["wealth_quantile"],
            categories=WEALTH_QUANTILES,
            ordered=True,
        )
        sort_columns.append("wealth_quantile")

    if sort_columns:
        sorted_data = sorted_data.sort_values(sort_columns).reset_index(drop=True)
        for column in sort_columns:
            sorted_data[column] = sorted_data[column].astype(str)

    return sorted_data
