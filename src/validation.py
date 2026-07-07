from __future__ import annotations

from src.human_capital import annuity_factor


def national_human_capital_sanity_check(
    labor_compensation: float = 16.082502e12,
    horizon_years: int = 40,
    wage_growth: float = 0.015,
    discount_rate: float = 0.035,
) -> float:
    return labor_compensation * annuity_factor(horizon_years, wage_growth, discount_rate)

