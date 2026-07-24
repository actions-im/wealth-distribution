from pathlib import Path
import tomllib

from wealth_report.model.assumptions import ModelAssumptions


def test_open_source_release_files_exist():
    for name in [
        "LICENSE",
        "CITATION.cff",
        "CONTRIBUTING.md",
        "SECURITY.md",
        "CODE_OF_CONDUCT.md",
    ]:
        assert Path(name).is_file(), f"missing {name}"


def test_readme_uses_neutral_measure_names():
    readme = Path("README.md").read_text()

    assert "modeled comprehensive resources" in readme.lower()
    assert "the trick" not in readme.lower()


def test_methodology_documents_required_criticism_surfaces():
    methodology = Path("docs/methodology.md").read_text().lower()
    for section in [
        "scope and unit",
        "components",
        "exclusions",
        "lifecycle",
        "uncertainty",
        "source vintage",
        "limitations",
    ]:
        assert f"## {section}" in methodology


def test_release_metadata_matches_publication_candidate():
    project = tomllib.loads(Path("pyproject.toml").read_text())
    citation = Path("CITATION.cff").read_text()

    assert project["project"]["version"] == "0.3.0"
    assert "version: 0.3.0" in citation
    assert "date-released: 2026-07-23" in citation
    assert ModelAssumptions().version == "2022-baseline-v2"


def test_uncertainty_section_does_not_claim_an_unimplemented_api():
    methodology = Path("docs/methodology.md").read_text()

    assert "The uncertainty API and arithmetic are tested" not in methodology
    assert "does not yet implement replicate-weight intervals" in methodology


def test_ci_has_a_scheduled_real_data_publication_check():
    workflow = Path(".github/workflows/ci.yml").read_text()

    assert "schedule:" in workflow
    assert "--real-data" in workflow
    assert "real-data-publication" in workflow


def test_ci_uses_locked_explicit_ruff_configuration():
    project = tomllib.loads(Path("pyproject.toml").read_text())
    workflow = Path(".github/workflows/ci.yml").read_text()
    readme = Path("README.md").read_text()

    assert "ruff==0.16.0" in project["dependency-groups"]["dev"]
    assert project["tool"]["ruff"]["target-version"] == "py311"
    assert project["tool"]["ruff"]["lint"]["select"] == ["E4", "E7", "E9", "F"]
    assert "uv run ruff check app.py wealth_report scripts tests" in workflow
    assert "uvx ruff" not in workflow
    assert "uv run ruff check app.py wealth_report scripts tests" in readme
    assert "uvx ruff" not in readme


def test_real_data_publication_waits_for_verify_job():
    workflow = Path(".github/workflows/ci.yml").read_text()
    publication_job = workflow.split("  real-data-publication:", maxsplit=1)[1]

    assert "\n    needs: verify\n" in publication_job
    assert "manifest['output_files']" in publication_job
    assert "sha256_file" in publication_job
