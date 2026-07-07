from __future__ import annotations

import pandas as pd

from src.formatting import percent
from src.provenance import computed_scf_row_source


def build_executive_share_table(distribution: pd.DataFrame) -> pd.DataFrame:
    table = pd.DataFrame(
        {
            "Quantile": distribution["wealth_quantile"],
            "Priced wealth share": distribution["traditional_net_worth_share"].map(percent),
            "Full wealth share": distribution["combined_real_wealth_share"].map(percent),
            "Change": distribution["combined_minus_marketable_share"].map(lambda value: percent(value, signed=True)),
            "Source": computed_scf_row_source(),
        }
    )
    return table


def build_detail_wealth_table(distribution: pd.DataFrame) -> pd.DataFrame:
    from src.formatting import dollars_trillions

    table = distribution[
        [
            "wealth_quantile",
            "population_share",
            "household_count",
            "traditional_net_worth_total",
            "human_capital_total",
            "combined_real_wealth_total",
        ]
    ].copy()
    table.columns = [
        "Quantile",
        "Population share",
        "Households",
        "Priced wealth",
        "Discounted future earnings",
        "Full wealth",
    ]
    table["Population share"] = table["Population share"].map(percent)
    table["Households"] = table["Households"].map(lambda value: f"{value / 1_000_000:,.1f}M")
    for column in [
        "Priced wealth",
        "Discounted future earnings",
        "Full wealth",
    ]:
        table[column] = table[column].map(dollars_trillions)
    table["Source"] = computed_scf_row_source()
    return table
