from __future__ import annotations

from dataclasses import dataclass
import math

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
    "reentry_probability": 0.25,
    "payable_benefit_factor": 0.80,
    "income_security_floor_monthly": 622.0,
    "inheritance_horizon_years": 15,
}


@dataclass(frozen=True)
class ModelAssumptions:
    discount_rate: float = 0.035
    wage_growth: float = 0.015
    retirement_age: int = 67
    employment_probability: float = 0.95
    reentry_probability: float = 0.25
    tax_rate: float = 0.0
    payable_benefit_factor: float = 0.80
    income_security_floor_monthly: float = 622.0
    inheritance_horizon_years: int = 15
    version: str = "2022-baseline-v1"

    def __post_init__(self) -> None:
        if not math.isfinite(self.discount_rate) or self.discount_rate <= -1:
            raise ValueError("discount_rate must be finite and greater than -1")
        if not math.isfinite(self.wage_growth) or self.wage_growth <= -1:
            raise ValueError("wage_growth must be finite and greater than -1")
        if not 18 <= self.retirement_age <= 100:
            raise ValueError("retirement_age must be between 18 and 100")
        for name in (
            "employment_probability",
            "reentry_probability",
            "tax_rate",
            "payable_benefit_factor",
        ):
            value = getattr(self, name)
            if not math.isfinite(value) or not 0 <= value <= 1:
                raise ValueError(f"{name} must be finite and between zero and one")
        if (
            not math.isfinite(self.income_security_floor_monthly)
            or self.income_security_floor_monthly < 0
        ):
            raise ValueError("income_security_floor_monthly must be finite and nonnegative")
        if (
            isinstance(self.inheritance_horizon_years, bool)
            or not isinstance(self.inheritance_horizon_years, int)
            or not 5 <= self.inheritance_horizon_years <= 30
        ):
            raise ValueError("inheritance_horizon_years must be an integer between 5 and 30")
