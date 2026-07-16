import hashlib
import json
from pathlib import Path

import pytest

from src.source_manifest import (
    SourceIntegrityError,
    SourceSpec,
    build_artifact_record,
    load_source_registry,
    verify_artifact,
)


def test_registry_contains_required_official_sources():
    registry = load_source_registry()

    assert {
        "scf_summary",
        "scf_full",
        "scf_replicate_weights",
        "ssa_life_male",
        "ssa_life_female",
        "ssa_2022_parameters",
        "ssa_2022_trustees",
        "fed_z1_db_pensions",
    } <= set(registry)
    assert all(spec.url.startswith("https://") for spec in registry.values())


def test_verify_artifact_rejects_wrong_hash(tmp_path):
    path = tmp_path / "source.bin"
    path.write_bytes(b"wrong")

    with pytest.raises(SourceIntegrityError, match="SHA-256"):
        verify_artifact(path, expected_sha256="0" * 64)


def test_artifact_record_contains_reproducibility_fields(tmp_path):
    path = tmp_path / "source.bin"
    path.write_bytes(b"official")
    spec = SourceSpec(
        key="fixture",
        provider="Fixture provider",
        url="https://example.com/source.bin",
        vintage="2022",
        filename="source.bin",
        sha256=hashlib.sha256(b"official").hexdigest(),
    )

    record = build_artifact_record(spec, path, retrieved_at="2026-07-11T00:00:00Z")

    assert record["sha256"] == spec.sha256
    assert record["bytes"] == len(b"official")
    assert record["retrieved_at"] == "2026-07-11T00:00:00Z"
    assert json.dumps(record)


def test_registry_file_is_valid_json():
    assert json.loads(Path("data/sources.json").read_text())
