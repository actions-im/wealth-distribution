import json

from scripts.reproduce_report import reproduce


def test_reproduction_writes_tables_and_manifest(tmp_path):
    reproduce(output_dir=tmp_path, use_fixture=True)

    assert (tmp_path / "headline.csv").is_file()
    assert (tmp_path / "detail.csv").is_file()
    assert (tmp_path / "sensitivity.csv").is_file()
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    assert manifest["fixture"] is True
    assert manifest["measure_definitions"]["defensive_resources"]
