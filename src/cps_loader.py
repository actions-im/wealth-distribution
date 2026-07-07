from __future__ import annotations


def estimate_expected_labor_income(age: int, education: str | None = None, occupation: str | None = None) -> float:
    """Placeholder for the CPS/ACS age-income model planned for MVP 2."""
    del education, occupation
    if age < 25:
        return 32_000.0
    if age < 35:
        return 65_000.0
    if age < 45:
        return 90_000.0
    if age < 55:
        return 102_000.0
    if age < 65:
        return 88_000.0
    if age < 75:
        return 30_000.0
    return 8_000.0

