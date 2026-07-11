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
