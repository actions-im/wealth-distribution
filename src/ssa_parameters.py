from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class SSAParameters:
    year: int
    first_bend_point: float
    second_bend_point: float
    taxable_maximum: float
    employee_oasdi_rate: float
    full_retirement_age: int
    combined_payable_factor_at_depletion: float


PARAMETERS = {
    2022: SSAParameters(
        year=2022,
        first_bend_point=1_024,
        second_bend_point=6_172,
        taxable_maximum=147_000,
        employee_oasdi_rate=0.062,
        full_retirement_age=67,
        combined_payable_factor_at_depletion=0.80,
    )
}


def parameters_for_year(year: int) -> SSAParameters:
    try:
        return PARAMETERS[year]
    except KeyError as error:
        raise ValueError(f"unsupported SSA parameter year: {year}") from error


def primary_insurance_amount(aime: float, *, year: int = 2022) -> float:
    """Return monthly PIA before SSA's statutory dime rounding."""
    if not math.isfinite(aime) or aime < 0:
        raise ValueError("aime must be finite and nonnegative")
    parameters = parameters_for_year(year)
    first_band = min(aime, parameters.first_bend_point)
    second_band = min(
        max(aime - parameters.first_bend_point, 0),
        parameters.second_bend_point - parameters.first_bend_point,
    )
    third_band = max(aime - parameters.second_bend_point, 0)
    return float(0.90 * first_band + 0.32 * second_band + 0.15 * third_band)
