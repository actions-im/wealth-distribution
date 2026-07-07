from __future__ import annotations

AGE_BUCKETS = ["<25", "25-34", "35-44", "45-54", "55-64", "65-74", "75+"]

WEALTH_QUANTILES = [
    "Bottom 50%",
    "50-90%",
    "90-99%",
    "99-99.9%",
    "Top 0.1%",
]

SOURCE_NOTE = (
    "Human capital is not marketable wealth. It is personal, risky, nontransferable, "
    "partly taxable, and highly sensitive to assumptions."
)

DEFAULT_ASSUMPTIONS = {
    "discount_rate": 0.035,
    "wage_growth": 0.015,
    "retirement_age": 67,
    "employment_probability": 0.95,
    "tax_rate": 0.0,
    "liquidity_weight": 0.25,
}

