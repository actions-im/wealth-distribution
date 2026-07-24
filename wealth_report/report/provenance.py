"""Number-audit tables and source captions for the Methodology page.

Source-field strings are centralized constants so chart audits, component
tables, and captions stay aligned when SCF fields change.
"""

from __future__ import annotations

from typing import Mapping

import pandas as pd

ASSUMPTION_SOURCE = "User-adjustable model assumption shown in the sidebar"
COMPUTED_SCF_SOURCE = (
    "Computed from Federal Reserve 2022 SCF public summary extract NETWORTH and WGT, and Full "
    "SCF p22i6.dta respondent/spouse demographic, wage, Social Security, pension, and inheritance fields"
)

SUMMARY_NET_WORTH_FIELDS = "Summary SCF rscfp2022.dta: NETWORTH, WGT"
FULL_MODEL_SOURCE_FIELDS = (
    "Summary SCF rscfp2022.dta: NETWORTH, WGT; Full SCF p22i6.dta: respondent/spouse "
    "demographics; main- and second-job wage amount, frequency, hours, and weeks "
    "(X4110–X4113, X4507–X4510; X4710–X4713, X5107–X5110); former-job earnings "
    "and reported nonworker work-history duration fields "
    "(X4602, X4605, X4606, X4613, X4614, X4616; "
    "X5202, X5205, X5206, X5213, X5214, X5216); "
    "current Social Security payment, frequency, and benefit type (X5304, X5306, X5307, X5309, "
    "X5311, X5312); DB pension fields including current-benefit COLA status; and inheritance "
    "fields X5819, X5821, X5825; SSA mortality "
    "and 2022 program parameters; SSI average-payment benchmark"
)
FULL_MODEL_SOURCE_KEYS = (
    "scf_summary; scf_full; ssa_period_life_2019_tr2022; "
    "ssa_2022_parameters; ssa_2022_trustees; ssa_2022_ssi"
)
AGE_PANEL_SOURCE_FIELDS = (
    "Summary SCF rscfp2022.dta: NETWORTH, WGT, AGE; Full SCF p22i6.dta: "
    "X5819, X5821, X5825; respondent/spouse wage amounts, frequencies, hours, "
    "and weeks for main and second jobs; former-job earnings and nonworker work-history "
    "duration fields X4602–X4616 and X5202–X5216; "
    "current Social Security payment, "
    "frequency, and benefit type (X5304, X5306, X5307, X5309, X5311, X5312); "
    "DB pension benefit fields; SSA mortality and 2022 program parameters"
)
CHANGE_PP_SOURCE_FIELDS = (
    "The two derived resource shares for the same reported rank interval; the full-resource "
    "state uses Summary SCF rscfp2022.dta: NETWORTH, WGT; Full SCF p22i6.dta: X5819, X5821, "
    "X5825; and SSA mortality"
)


def build_shift_number_audit(
    shift_data: pd.DataFrame, assumptions: Mapping[str, float | int]
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
        base = {
            "Rank basis": record["rank_basis"],
            "Source fields": (
                SUMMARY_NET_WORTH_FIELDS if is_conventional else FULL_MODEL_SOURCE_FIELDS
            ),
            "Source keys": "scf_summary" if is_conventional else FULL_MODEL_SOURCE_KEYS,
            "Classification": (
                "Computed from official SCF microdata"
                if is_conventional
                else "Model-derived from official inputs"
            ),
        }
        group, state = record["group"], record["state"]
        metric_specs = (
            ("resource share", float(record["share"]), "resource share",
             "weighted total for this independently ranked group / weighted total "
             "for all groups under the same measure"),
            ("weighted total", float(record["weighted_total"]), "2022 dollars",
             "sum(household resource value × SCF WGT) within the ranked group"),
            ("weighted household share", float(record["household_share"]),
             "weighted household share",
             "sum(SCF WGT in group) / sum(SCF WGT in all groups)"),
        )
        for label, value, unit, formula in metric_specs:
            rows.append(
                {
                    **base,
                    "Displayed number": f"{group} · {state} · {label}",
                    "Value": value,
                    "Unit": unit,
                    "Formula": formula,
                }
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
                "Source fields": CHANGE_PP_SOURCE_FIELDS,
                "Source keys": FULL_MODEL_SOURCE_KEYS,
                "Classification": "Model-derived comparison",
            }
        )
    audit = pd.DataFrame(rows)
    audit.attrs["assumptions"] = dict(assumptions)
    return audit


def build_age_shift_number_audit(
    age_shift_data: pd.DataFrame, assumptions: Mapping[str, float | int]
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
                    "Source fields": AGE_PANEL_SOURCE_FIELDS,
                    "Source keys": FULL_MODEL_SOURCE_KEYS,
                    "Classification": "Model-derived from official inputs",
                },
            ]
        )
        audits.append(pd.concat([panel_audit, summary_rows], ignore_index=True))

    audit = pd.concat(audits, ignore_index=True)
    audit.attrs["assumptions"] = dict(assumptions)
    return audit


def build_component_methodology_table(
    assumptions: Mapping[str, float | int],
) -> pd.DataFrame:
    """Return the formula and source lineage for each modeled component."""
    specs = _component_specs(assumptions)
    return pd.DataFrame(specs)


def _component_specs(assumptions: Mapping[str, float | int]) -> list[dict[str, object]]:
    return [
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
            "Source fields": (
                "Full SCF p22i6.dta: respondent age X14, sex X8021, wage amount/frequency "
                "X4112/X4113, hours/weeks X4110/X4111, second job X4507–X4510; spouse age "
                "X19, sex X103, wage amount/frequency X4712/X4713, hours/weeks X4710/X4711, "
                "second job X5107–X5110"
            ),
            "Current assumptions": (
                f"discount={assumptions['discount_rate']:.3f}; "
                f"real wage growth={assumptions['wage_growth']:.3f}; "
                f"retirement age={assumptions['retirement_age']}; "
                f"employment={assumptions['employment_probability']:.2f}; "
                f"re-entry probability={assumptions['reentry_probability']:.2f}; "
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
                "Full SCF p22i6.dta: respondent/spouse wage, nonworker former-job earnings, "
                "and reported work-history duration fields X4602, X4605, X4606, X4613, "
                "X4614, X4616, X5202, X5205, X5206, X5213, X5214, X5216, "
                "ages, sex, reported current Social Security payment/frequency X5306/X5307 and "
                "X5311/X5312, and reported benefit types X5304/X5309; SSA bend points, taxable "
                "maximum, employee rate, and mortality"
            ),
            "Current assumptions": (
                f"payable factor={assumptions['payable_benefit_factor']:.2f}; "
                f"retirement age={assumptions['retirement_age']}"
            ),
            "Source keys": (
                "scf_full; ssa_period_life_2019_tr2022; ssa_2022_parameters; "
                "ssa_2022_trustees"
            ),
            "Important treatment": (
                "Only reported retired-worker payments are used as current benefits. Reported SSI, "
                "disability, survivor/dependent, and unclassified payments are excluded from that "
                "retired-worker flow; unsupported spousal and survivor benefits are not imputed. "
                "Reported former-job earnings and duration proxy current non-earners' history where usable; otherwise "
                "history is marked unestimated. Re-entry wages affect future covered earnings only."
            ),
        },
        {
            "Component": "Defined-benefit pensions",
            "Calculation": (
                "Survival-weighted real PV of current or expected lifetime DB benefit flows "
                "from the reported claiming age"
            ),
            "Source fields": (
                "Full SCF plan type, owner, annual benefit, frequency, claiming age, status, and "
                "current-benefit COLA fields X5320/X5328/X5336/X5420"
            ),
            "Current assumptions": (
                f"discount={assumptions['discount_rate']:.3f}; "
                f"long-run inflation={assumptions['inflation_rate']:.3f}"
            ),
            "Source keys": "scf_full; ssa_period_life_2019_tr2022; fed_z1_db_pensions",
            "Important treatment": (
                "Defined-contribution/account balances already in NETWORTH are never added again. "
                "Reported COLA preserves real payments; no or unknown COLA is fixed nominal and "
                "loses real value during any deferral as well as retirement."
            ),
        },
        {
            "Component": "Income-security floor",
            "Calculation": (
                "For each future year and mutually exclusive adult-survival state, probability(state) × "
                "max(0, monthly benchmark × 12 × surviving-adult scaling − surviving adults' labor, "
                "Social Security, and DB pension cash income); then discount the expected top-up stream"
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
                "eligibility determination, entitlement, or transferable asset. Couple-state probabilities "
                "use an independent-mortality approximation."
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


def chart_source_caption() -> str:
    return (
        f"Source: {COMPUTED_SCF_SOURCE}. Conventional net worth uses networth x wgt. "
        "The comprehensive model adds estimated labor resources, Social Security, and defined-benefit pensions "
        "from the full SCF and SSA inputs, plus SCF-calibrated re-entry wages and a nonmarketable income-security "
        "top-up scenario using the sidebar assumptions. It also includes a constrained inheritance reallocation "
        "from SCF X5819, X5821, and X5825 with mortality-weighted donor reserves."
    )


def assumption_source_caption() -> str:
    return (
        f"Source for sidebar numbers: {ASSUMPTION_SOURCE}. These are scenario controls, "
        "not empirical Fed estimates."
    )
