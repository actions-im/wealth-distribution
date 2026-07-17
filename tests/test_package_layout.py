from pathlib import Path


def test_public_package_uses_lowercase_layer_directories():
    root = Path("wealth_report")

    assert (root / "app").is_dir()
    assert (root / "model").is_dir()
    assert (root / "providers").is_dir()
    assert (root / "report").is_dir()
    assert not Path("src").exists()
