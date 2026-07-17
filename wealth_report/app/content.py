"""Load version-controlled editorial copy for the Streamlit report."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path


CONTENT_ROOT = Path(__file__).resolve().parents[2] / "content"


@lru_cache(maxsize=64)
def load_markdown(section: str) -> str:
    """Return a Markdown section addressed relative to the repository content root."""
    relative_path = Path(section)
    if relative_path.is_absolute() or ".." in relative_path.parts:
        raise ValueError("content section must be a relative path inside content")
    path = (CONTENT_ROOT / relative_path).with_suffix(".md")
    if not path.is_file():
        raise FileNotFoundError(f"report content section does not exist: {section}")
    return path.read_text(encoding="utf-8").strip()
