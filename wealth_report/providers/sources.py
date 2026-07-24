from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any

import requests


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REGISTRY_PATH = PROJECT_ROOT / "data" / "sources.json"

SCF_2022_EXTRACT_ZIP_URL = "https://www.federalreserve.gov/econres/files/scfp2022s.zip"


class SourceIntegrityError(ValueError):
    """Raised when an official source does not match its registered metadata."""


@dataclass(frozen=True)
class SourceSpec:
    key: str
    provider: str
    url: str
    vintage: str
    filename: str
    documentation_url: str | None = None
    description: str | None = None
    sha256: str | None = None
    snapshot_sha256: str | None = None
    archive_member: str | None = None


def load_source_registry(path: Path = DEFAULT_REGISTRY_PATH) -> dict[str, SourceSpec]:
    raw = json.loads(path.read_text())
    return {key: SourceSpec(key=key, **values) for key, values in raw.items()}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_artifact(path: Path, expected_sha256: str | None) -> str:
    actual = sha256_file(path)
    if expected_sha256 and actual.lower() != expected_sha256.lower():
        raise SourceIntegrityError(
            f"SHA-256 mismatch for {path}: expected {expected_sha256}, got {actual}"
        )
    return actual


def build_artifact_record(
    spec: SourceSpec,
    path: Path,
    *,
    retrieved_at: str | None = None,
    headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    actual_hash = verify_artifact(path, spec.sha256)
    record = asdict(spec)
    record.update(
        {
            "path": str(path),
            "bytes": path.stat().st_size,
            "sha256": actual_hash,
            "retrieved_at": retrieved_at or datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "etag": (headers or {}).get("ETag"),
            "last_modified": (headers or {}).get("Last-Modified"),
        }
    )
    return record


def download_artifact(
    spec: SourceSpec,
    destination_dir: Path,
    *,
    timeout: int = 120,
) -> tuple[Path, dict[str, Any]]:
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = destination_dir / spec.filename
    with requests.get(spec.url, stream=True, timeout=timeout) as response:
        response.raise_for_status()
        file_descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{spec.filename}.", dir=destination_dir
        )
        try:
            with os.fdopen(file_descriptor, "wb") as temporary:
                for chunk in response.iter_content(1024 * 1024):
                    if chunk:
                        temporary.write(chunk)
            temporary_path = Path(temporary_name)
            verify_artifact(temporary_path, spec.sha256)
            temporary_path.replace(destination)
        except BaseException:
            Path(temporary_name).unlink(missing_ok=True)
            raise

    return destination, build_artifact_record(spec, destination, headers=dict(response.headers))
