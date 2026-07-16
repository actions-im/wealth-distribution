from __future__ import annotations

import pandas as pd

from src.data_sources import FED_EXPECTED_FUTURE_INCOME_URL, FED_HUMAN_WEALTH_MODEL_URL, SCF_2022_EXTRACT_ZIP_URL
from src.real_data import SCF_2022_DATASET_LABEL


ASSUMPTION_SOURCE = "User-adjustable model assumption shown in the sidebar"
DEFINITION_SOURCE = "Report definition"
COMPUTED_SCF_SOURCE = (
    "Computed from Federal Reserve 2022 SCF public summary extract fields networth, wageinc, age, and wgt"
)


def build_shift_number_audit(
    shift_data: pd.DataFrame, assumptions: dict[str, float | int]
) -> pd.DataFrame:
    """Trace every number visible in the distribution-shift figure."""
    required = {
        "group",
        "state",
        "share",
        "weighted_total",
        "household_share",
        "rank_basis",
        "conventional_share",
        "future_resources_share",
        "change_pp",
    }
    missing = required - set(shift_data.columns)
    if missing:
        raise ValueError(f"shift number audit is missing columns: {sorted(missing)}")

    rows: list[dict[str, object]] = []
    for record in shift_data.to_dict("records"):
        is_conventional = record["state"] == "Conventional net worth"
        source_fields = (
            "Summary SCF rscfp2022.dta: NETWORTH, WGT"
            if is_conventional
            else (
                "Summary SCF rscfp2022.dta: NETWORTH, WGT; Full SCF p22i6.dta: X5819, X5821, X5825, "
                "respondent/spouse ages and wages, reported Social Security, and DB pension benefit fields; "
                "SSA mortality and 2022 program parameters"
                "; SSI average-payment benchmark"
            )
        )
        source_keys = (
            "scf_summary"
            if is_conventional
            else (
                "scf_summary; scf_full; ssa_period_life_2019_tr2022; "
                "ssa_2022_parameters; ssa_2022_trustees"
                "; ssa_2022_ssi"
            )
        )
        classification = (
            "Computed from official SCF microdata"
            if is_conventional
            else "Model-derived from official inputs"
        )
        base = {
            "Rank basis": record["rank_basis"],
            "Source fields": source_fields,
            "Source keys": source_keys,
            "Classification": classification,
        }
        rows.extend(
            [
                {
                    **base,
                    "Displayed number": (
                        f"{record['group']} · {record['state']} · resource share"
                    ),
                    "Value": float(record["share"]),
                    "Unit": "resource share",
                    "Formula": (
                        "weighted total for this independently ranked group / weighted total "
                        "for all groups under the same measure"
                    ),
                },
                {
                    **base,
                    "Displayed number": (
                        f"{record['group']} · {record['state']} · weighted total"
                    ),
                    "Value": float(record["weighted_total"]),
                    "Unit": "2022 dollars",
                    "Formula": "sum(household resource value × SCF WGT) within the ranked group",
                },
                {
                    **base,
                    "Displayed number": (
                        f"{record['group']} · {record['state']} · weighted household share"
                    ),
                    "Value": float(record["household_share"]),
                    "Unit": "weighted household share",
                    "Formula": "sum(SCF WGT in group) / sum(SCF WGT in all groups)",
                },
            ]
        )

    for record in shift_data.drop_duplicates("group").to_dict("records"):
        rows.append(
            {
                "Displayed number": f"{record['group']} · percentage-point change",
                "Value": float(record["change_pp"]),
                "Unit": "percentage points",
                "Rank basis": "Each state uses its own metric-specific rank",
                "Formula": (
                    "100 × (all modeled future resources share − conventional net-worth share)"
                ),
                "Source fields": (
                    "The two derived resource shares for the same reported rank interval; the full-resource "
                    "state uses Summary SCF rscfp2022.dta: NETWORTH, WGT; Full SCF p22i6.dta: X5819, X5821, "
                    "X5825; and SSA mortality"
                ),
                "Source keys": (
                    "scf_summary; scf_full; ssa_period_life_2019_tr2022; "
                    "ssa_2022_parameters; ssa_2022_trustees; ssa_2022_ssi"
                ),
                "Classification": "Model-derived comparison",
            }
        )
    audit = pd.DataFrame(rows)
    audit.attrs["assumptions"] = dict(assumptions)
    return audit


def build_age_shift_number_audit(
    age_shift_data: pd.DataFrame, assumptions: dict[str, float | int]
) -> pd.DataFrame:
    """Trace every chart and panel-summary value on the Age slicing page."""
    required = {
        "age_group",
        "weighted_family_count",
        "all_resources_total",
        "group",
        "state",
        "share",
        "weighted_total",
        "household_share",
        "rank_basis",
        "conventional_share",
        "future_resources_share",
        "change_pp",
    }
    missing = required - set(age_shift_data.columns)
    if missing:
        raise ValueError(f"age-shift number audit is missing columns: {sorted(missing)}")
    if age_shift_data.empty or age_shift_data["age_group"].isna().any():
        raise ValueError("age-shift number audit requires non-empty age buckets")

    audits: list[pd.DataFrame] = []
    for age_bucket, panel in age_shift_data.groupby(
        "age_group", observed=True, sort=False
    ):
        values = panel[["weighted_family_count", "all_resources_total"]].drop_duplicates()
        if len(values) != 1:
            raise ValueError(
                "age-shift number audit requires one panel summary per age bucket"
            )

        panel_audit = build_shift_number_audit(panel, assumptions).copy()
        panel_audit.insert(0, "Report view", "Age slicing")
        panel_audit.insert(1, "Age bucket", str(age_bucket))
        summary = values.iloc[0]
        summary_rows = pd.DataFrame(
            [
                {
                    "Report view": "Age slicing",
                    "Age bucket": str(age_bucket),
                    "Displayed number": "Weighted SCF family count",
                    "Value": float(summary["weighted_family_count"]),
                    "Unit": "weighted SCF families",
                    "Rank basis": "Respondent-age bucket; no resource ranking",
                    "Formula": "sum(SCF WGT for SCF families in this respondent-age bucket)",
                    "Source fields": "Summary SCF rscfp2022.dta: AGE, WGT",
                    "Source keys": "scf_summary",
                    "Classification": "Computed from official SCF microdata",
                },
                {
                    "Report view": "Age slicing",
                    "Age bucket": str(age_bucket),
                    "Displayed number": "All modeled resources total",
                    "Value": float(summary["all_resources_total"]),
                    "Unit": "2022 dollars",
                    "Rank basis": "Respondent-age bucket; no resource ranking",
                    "Formula": (
                        "sum(continuation_resources × SCF WGT for this respondent-age bucket)"
                    ),
                    "Source fields": (
                        "Summary SCF rscfp2022.dta: NETWORTH, WGT, AGE; Full SCF p22i6.dta: "
                        "X5819, X5821, X5825, respondent/spouse ages and wages, reported Social "
                        "Security, and DB pension benefit fields; SSA mortality and 2022 program parameters"
                    ),
                    "Source keys": (
                        "scf_summary; scf_full; ssa_period_life_2019_tr2022; "
                        "ssa_2022_parameters; ssa_2022_trustees; ssa_2022_ssi"
                    ),
                    "Classification": "Model-derived from official inputs",
                },
            ]
        )
        audits.append(pd.concat([panel_audit, summary_rows], ignore_index=True))

    audit = pd.concat(audits, ignore_index=True)
    audit.attrs["assumptions"] = dict(assumptions)
    return audit


def build_component_methodology_table(
    assumptions: dict[str, float | int]
) -> pd.DataFrame:
    """Return the formula and source lineage for each modeled component."""
    return pd.DataFrame(
        [
            {
                "Component": "Conventional net worth",
                "Calculation": "SCF NETWORTH (assets minus liabilities)",
                "Source fields": "Summary SCF: NETWORTH, WGT, Y1/YY1",
                "Current assumptions": "None beyond the SCF definition",
                "Source keys": "scf_summary",
                "Important treatment": "Already includes account-type retirement balances.",
            },
            {
                "Component": "Future labor earnings",
                "Calculation": (
                    "Σ from t=1 to retirement of survival(t) × employment probability × "
                    "after-tax projected wage(t) / (1 + real discount rate)^t; a working-age "
                    "zero-wage adult uses a weighted median positive wage from the same SCF sex × age group"
                ),
                "Source fields": "Full SCF respondent/spouse ages, sex, wage amount and frequency",
                "Current assumptions": (
                    f"discount={assumptions['discount_rate']:.3f}; "
                    f"real wage growth={assumptions['wage_growth']:.3f}; "
                    f"retirement age={assumptions['retirement_age']}; "
                    f"employment={assumptions['employment_probability']:.2f}; "
                    f"tax haircut={assumptions['tax_rate']:.2f}"
                ),
                "Source keys": "scf_full; ssa_period_life_2019_tr2022",
                "Important treatment": (
                    "Person-bound, risky, nontransferable, and nonmarketable. The re-entry wage is a "
                    "transparent peer-based imputation, not an observed wage or a guaranteed return to work."
                ),
            },
            {
                "Component": "Social Security",
                "Calculation": (
                    "Survival-weighted PV of scheduled retired-worker benefits from the 2022 "
                    "AIME/PIA proxy, less PV of future employee OASDI contributions"
                ),
                "Source fields": (
                    "Full SCF wages, ages, sex, reported current Social Security; SSA bend points, "
                    "taxable maximum, employee rate, and mortality"
                ),
                "Current assumptions": (
                    f"payable factor={assumptions['payable_benefit_factor']:.2f}; "
                    f"retirement age={assumptions['retirement_age']}"
                ),
                "Source keys": (
                    "scf_full; ssa_period_life_2019_tr2022; ssa_2022_parameters; "
                    "ssa_2022_trustees"
                ),
                "Important treatment": "Spousal and survivor benefits are excluded when unsupported.",
            },
            {
                "Component": "Defined-benefit pensions",
                "Calculation": (
                    "Survival-weighted real PV of current or expected lifetime DB benefit flows "
                    "from the reported claiming age"
                ),
                "Source fields": (
                    "Full SCF plan type, owner, annual benefit, frequency, claiming age, and status"
                ),
                "Current assumptions": f"discount={assumptions['discount_rate']:.3f}",
                "Source keys": "scf_full; ssa_period_life_2019_tr2022; fed_z1_db_pensions",
                "Important treatment": (
                    "Defined-contribution/account balances already in NETWORTH are never added again."
                ),
            },
            {
                "Component": "Income-security floor",
                "Calculation": (
                    "For each future year, max(0, monthly benchmark × 12 × adult scaling "
                    "− expected labor cash income − Social Security cash benefit − DB pension cash benefit); "
                    "then survival-weight and discount the top-up stream"
                ),
                "Source fields": (
                    "Full SCF respondent/spouse count, age, sex, wages, reported Social Security, and DB plans"
                ),
                "Current assumptions": (
                    f"monthly benchmark=${assumptions['income_security_floor_monthly']:,.0f}; "
                    "two-adult scaling=1.5×"
                ),
                "Source keys": "scf_full; ssa_period_life_2019_tr2022; ssa_2022_ssi",
                "Important treatment": (
                    "Scenario benchmark calibrated to the December 2022 average SSI payment; it is not an "
                    "eligibility determination, entitlement, or transferable asset. For couples, survival of "
                    "at least one adult uses an independence approximation."
                ),
            },
            {
                "Component": "Expected inheritance reallocation",
                "Calculation": (
                    "Discounted recipient claims from positive SCF expectation field values, including SCF "
                    "imputation where applicable, when X5819 is affirmative and X5821 is positive; "
                    "mortality-weighted estate donor capacity is positive NETWORTH × probability of death within "
                    "the active horizon for affirmative X5825 donors; funding cap=min(claims, capacity); equal "
                    "weighted credit/reserve conservation applies proportional recipient and donor scales"
                ),
                "Source fields": (
                    "Summary SCF rscfp2022.dta: NETWORTH, WGT; Full SCF p22i6.dta: X5819, X5821, X5825, "
                    "respondent age and sex; SSA mortality"
                ),
                "Current assumptions": (
                    f"discount={assumptions['discount_rate']:.3f}; "
                    f"horizon={assumptions['inheritance_horizon_years']} years; "
                    "positive SCF expectation field value has no invented probability haircut"
                ),
                "Source keys": "scf_summary; scf_full; ssa_period_life_2019_tr2022",
                "Important treatment": (
                    "Constrained aggregate reallocation, not a legal claim or current legal ownership. "
                    "The public SCF does not link recipient families to donor families."
                ),
            },
            {
                "Component": "Distribution rank and share",
                "Calculation": (
                    "Rank SCF families independently under each measure; sum value × WGT in the "
                    "rank interval; divide by the measure's weighted national total"
                ),
                "Source fields": "Household component values and SCF WGT",
                "Current assumptions": "Four displayed intervals: bottom 50, next 40, next 9, top 1",
                "Source keys": "scf_summary; scf_full",
                "Important treatment": "The two states do not contain identical households.",
            },
        ]
    )


def chart_source_caption() -> str:
    return (
        f"Source: {COMPUTED_SCF_SOURCE}. Conventional net worth uses networth x wgt. "
        "The comprehensive model adds SCF-calibrated re-entry wages and a nonmarketable income-security "
        "top-up scenario using the sidebar assumptions, plus a constrained inheritance reallocation from "
        "SCF X5819, X5821, and X5825 with mortality-weighted donor reserves."
    )


def assumption_source_caption() -> str:
    return (
        f"Source for sidebar numbers: {ASSUMPTION_SOURCE}. These are scenario controls, "
        "not empirical Fed estimates."
    )


def table_source_note() -> str:
    return (
        "Each numeric row is sourced in the Source column. SCF-derived numbers are weighted with wgt; "
        "assumption-driven numbers use the visible sidebar settings."
    )


def computed_scf_row_source() -> str:
    return "SCF 2022: networth, wageinc, age, wgt; full-wealth values also use sidebar assumptions"


def build_number_source_table(assumptions: dict[str, float | int]) -> pd.DataFrame:
    rows = [
        {
            "Number category": "Survey year and raw household microdata",
            "Source": SCF_2022_DATASET_LABEL,
            "Method": f"Downloaded from {SCF_2022_EXTRACT_ZIP_URL}; app reads rscfp2022.dta.",
        },
        {
            "Number category": "Household counts and population shares",
            "Source": SCF_2022_DATASET_LABEL,
            "Method": "Sum SCF household weight field wgt within each net-worth quantile.",
        },
        {
            "Number category": "Conventional net-worth dollars and shares",
            "Source": SCF_2022_DATASET_LABEL,
            "Method": "Sum networth x wgt within each quantile; divide by national weighted networth total for shares.",
        },
        {
            "Number category": "Discounted future earnings dollars and shares",
            "Source": f"{SCF_2022_DATASET_LABEL} plus sidebar assumptions",
            "Method": (
                "Use positive wageinc, age, and wgt. Present value uses "
                f"discount_rate={assumptions['discount_rate']}, "
                f"wage_growth={assumptions['wage_growth']}, "
                f"retirement_age={assumptions['retirement_age']}, "
                f"employment_probability={assumptions['employment_probability']}, "
                f"tax_rate={assumptions['tax_rate']}."
            ),
        },
        {
            "Number category": "Legacy net-worth-plus-labor dollars and shares",
            "Source": f"{SCF_2022_DATASET_LABEL} plus sidebar assumptions",
            "Method": "Conventional net worth plus discounted future earnings; weighted by wgt for totals and shares.",
        },
        {
            "Number category": "Discount rate",
            "Source": ASSUMPTION_SOURCE,
            "Method": f"Sidebar value: discount_rate={assumptions['discount_rate']}.",
        },
        {
            "Number category": "Real wage growth",
            "Source": ASSUMPTION_SOURCE,
            "Method": f"Sidebar value: wage_growth={assumptions['wage_growth']}.",
        },
        {
            "Number category": "Retirement age",
            "Source": ASSUMPTION_SOURCE,
            "Method": f"Sidebar value: retirement_age={assumptions['retirement_age']}.",
        },
        {
            "Number category": "Employment probability",
            "Source": ASSUMPTION_SOURCE,
            "Method": f"Sidebar value: employment_probability={assumptions['employment_probability']}.",
        },
        {
            "Number category": "Flat tax haircut",
            "Source": ASSUMPTION_SOURCE,
            "Method": f"Sidebar value: tax_rate={assumptions['tax_rate']}.",
        },
        {
            "Number category": "Human-capital liquidity weight",
            "Source": ASSUMPTION_SOURCE,
            "Method": f"Sidebar value: liquidity_weight={assumptions['liquidity_weight']}.",
        },
        {
            "Number category": "Income-security floor benchmark",
            "Source": "SSA December 2022 SSI average payment plus sidebar assumption",
            "Method": (
                f"Sidebar monthly benchmark=${assumptions['income_security_floor_monthly']:,.0f}; "
                "annual floor is benchmark × 12 for one adult and 1.5× for two adults, net of modeled "
                "labor, Social Security, and DB pension cash flows."
            ),
        },
        {
            "Number category": "Expected-inheritance reallocation",
            "Source": (
                "Federal Reserve 2022 SCF summary rscfp2022.dta and full detailed p22i6.dta, "
                "SSA mortality, plus sidebar assumptions"
            ),
            "Method": (
                "Use affirmative X5819 and positive X5821 SCF expectation field values, including SCF imputation "
                "where applicable, from p22i6.dta to discount recipient claims; use X5825, respondent age, "
                "and sex from p22i6.dta plus NETWORTH and WGT from rscfp2022.dta and SSA mortality to derive "
                "donor capacity. The weighted reallocation is capped at min(claims, capacity) and credits equal "
                "reserves; the sidebar horizon is "
                f"{assumptions['inheritance_horizon_years']} years."
            ),
        },
        {
            "Number category": "Wealth quantile breakpoints",
            "Source": DEFINITION_SOURCE,
            "Method": "Report-defined household net-worth groups: bottom 50, 50-90, 90-99, 99-99.9, top 0.1.",
        },
        {
            "Number category": "Age bucket breakpoints",
            "Source": DEFINITION_SOURCE,
            "Method": "Report-defined age groups: under 25, 25-34, 35-44, 45-54, 55-64, 65-74, 75+.",
        },
        {
            "Number category": "Human-capital methodology",
            "Source": "Federal Reserve research links",
            "Method": (
                "Present-value treatment is cited as methodology context, not as an official Fed wealth statistic: "
                f"{FED_EXPECTED_FUTURE_INCOME_URL}; {FED_HUMAN_WEALTH_MODEL_URL}."
            ),
        },
    ]
    return pd.DataFrame(rows)
