from pathlib import Path


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
