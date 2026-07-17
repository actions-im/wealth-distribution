from __future__ import annotations


def dollars_trillions(value: float) -> str:
    return f"${value / 1_000_000_000_000:,.1f}T"


def percent(value: float, signed: bool = False) -> str:
    if signed:
        return f"{value:+.1%}"
    return f"{value:.1%}"

