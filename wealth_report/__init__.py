"""Comprehensive household resources report package.

Layers (dependency direction: app → report → {model, providers}):

- ``wealth_report.app`` — Streamlit UI, cache, content
- ``wealth_report.report`` — orchestration, ranking, charts, audits
- ``wealth_report.model`` — pure valuation logic
- ``wealth_report.providers`` — SCF, SSA, and source-manifest I/O
"""

__all__ = [
    "app",
    "model",
    "providers",
    "report",
]
