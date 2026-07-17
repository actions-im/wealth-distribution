from __future__ import annotations

from dataclasses import asdict, dataclass
import math


SOURCE_NOTE = (
    "Human capital is not marketable wealth. It is personal, risky, nontransferable, "
    "partly taxable, and highly sensitive to assumptions."
)


@dataclass(frozen=True)
class ModelAssumptions:
    """Canonical scenario controls for the comprehensive-resources model."""

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

    def as_controls(self) -> dict[str, float | int]:
        """Sidebar / cache-key dict (excludes internal version stamp)."""
        values = asdict(self)
        values.pop("version", None)
        return values


# Derived from ModelAssumptions so defaults cannot drift.
DEFAULT_ASSUMPTIONS: dict[str, float | int] = ModelAssumptions().as_controls()
