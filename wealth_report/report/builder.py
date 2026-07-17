"""Backward-compatible re-exports for the report calculation surface.

Prefer importing from the focused modules:
  - wealth_report.report.types
  - wealth_report.report.valuation
  - wealth_report.report.pipeline
  - wealth_report.report.ranking
"""

from __future__ import annotations

from wealth_report.report.pipeline import load_comprehensive_household_data
from wealth_report.report.ranking import (
    WEALTH_QUANTILE_GROUPS,
    age_group,
    aggregate_ranked_resource_distributions,
    build_ranked_distributions,
)
from wealth_report.report.types import (
    SCF_2022_DATASET_LABEL,
    ComprehensiveHouseholdInput,
    ComprehensiveHouseholdRecord,
    build_comprehensive_household,
)
from wealth_report.report.valuation import (
    apply_inheritance_reallocation,
    value_detailed_household,
)

__all__ = [
    "SCF_2022_DATASET_LABEL",
    "WEALTH_QUANTILE_GROUPS",
    "ComprehensiveHouseholdInput",
    "ComprehensiveHouseholdRecord",
    "age_group",
    "aggregate_ranked_resource_distributions",
    "apply_inheritance_reallocation",
    "build_comprehensive_household",
    "build_ranked_distributions",
    "load_comprehensive_household_data",
    "value_detailed_household",
]
