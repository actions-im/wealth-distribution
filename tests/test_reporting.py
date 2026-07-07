from src.reporting import build_executive_share_table
from src.sample_data import aggregate_country_distribution_by_quantile, build_sample_household_data


def test_executive_share_table_focuses_on_current_vs_adjusted_distribution():
    data = build_sample_household_data(
        discount_rate=0.035,
        wage_growth=0.015,
        retirement_age=67,
        employment_probability=0.95,
        tax_rate=0.0,
        liquidity_weight=0.25,
    )
    distribution = aggregate_country_distribution_by_quantile(data)

    table = build_executive_share_table(distribution)

    assert list(table.columns) == [
        "Quantile",
        "Current wealth share",
        "Adjusted wealth share",
        "Change",
    ]
    assert table.loc[0, "Current wealth share"].endswith("%")
    assert table.loc[0, "Adjusted wealth share"].endswith("%")
    assert table["Change"].str.endswith("%").all()

