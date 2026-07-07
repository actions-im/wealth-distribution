from src.config import DEFAULT_ASSUMPTIONS
from src.provenance import (
    ASSUMPTION_SOURCE,
    COMPUTED_SCF_SOURCE,
    build_number_source_table,
    chart_source_caption,
)
from src.real_data import SCF_2022_DATASET_LABEL
from src.reporting import build_detail_wealth_table, build_executive_share_table


def test_report_tables_include_source_column(real_distribution):
    executive = build_executive_share_table(real_distribution)
    detail = build_detail_wealth_table(real_distribution)

    assert "Source" in executive.columns
    assert "Source" in detail.columns
    assert executive["Source"].str.contains("SCF").all()
    assert detail["Source"].str.contains("SCF").all()


def test_number_source_table_maps_calculated_and_assumption_numbers():
    source_table = build_number_source_table(DEFAULT_ASSUMPTIONS)

    assert {"Number category", "Source", "Method"}.issubset(source_table.columns)
    assert any(source_table["Source"].str.contains(SCF_2022_DATASET_LABEL))
    assert any(source_table["Source"].str.contains(ASSUMPTION_SOURCE))
    assert any(source_table["Method"].str.contains("discount_rate"))


def test_chart_source_caption_identifies_computed_scf_source():
    assert chart_source_caption().startswith("Source:")
    assert COMPUTED_SCF_SOURCE in chart_source_caption()
