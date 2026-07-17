from pathlib import Path


def test_public_package_uses_lowercase_layer_directories():
    root = Path("wealth_report")

    assert (root / "app").is_dir()
    assert (root / "model").is_dir()
    assert (root / "providers").is_dir()
    assert (root / "report").is_dir()
    assert not Path("src").exists()
    assert not Path("app_pages").exists()


def test_report_layer_is_split_into_focused_modules():
    report = Path("wealth_report/report")
    for name in ("types", "valuation", "pipeline", "ranking", "distribution", "provenance"):
        assert (report / f"{name}.py").is_file()
    assert (Path("wealth_report/model") / "numeric.py").is_file()
    assert (Path("wealth_report/app") / "bootstrap.py").is_file()
