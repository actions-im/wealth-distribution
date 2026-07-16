from __future__ import annotations

from pathlib import Path
from dataclasses import dataclass
from typing import Iterable, Mapping

import pandas as pd

from src.actuarial import conditional_survival
from src.config import AGE_BUCKETS, WEALTH_QUANTILES, ModelAssumptions
from src.human_capital import estimate_human_capital, estimate_labor_wealth
from src.pensions import DefinedBenefitPlan, value_defined_benefit_plan
from src.scf_detailed import (
    DetailedHouseholdInput,
    PersonInput,
    build_detailed_household_input,
    load_detailed_scf,
)
from src.scf_loader import download_scf_extract, load_scf_extract
from src.social_security import SocialSecurityPerson, social_security_wealth
from src.source_manifest import download_artifact, load_source_registry
from src.ssa_loader import load_ssa_period_life_table
from src.weighted_stats import (
    assign_weighted_quantile_group,
    weighted_median,
    weighted_rank_groups,
    weighted_rank_positions,
)


SCF_2022_DATASET_LABEL = "Federal Reserve 2022 SCF public summary extract"
SCF_2022_DATA_NOTE = (
    "Charts use the Federal Reserve 2022 Survey of Consumer Finances public summary extract. "
    "Rows are weighted with SCF household weights; future earnings use positive SCF wage income "
    "as the labor-income proxy."
)

WEALTH_QUANTILE_GROUPS = [
    ("Bottom 50%", 0.0, 0.5),
    ("50-90%", 0.5, 0.9),
    ("90-99%", 0.9, 0.99),
    ("99-99.9%", 0.99, 0.999),
    ("Top 0.1%", 0.999, 1.0),
]

REPORT_METRICS = [
    "traditional_net_worth",
    "human_capital",
    "combined_real_wealth",
    "liquidity_adjusted_real_wealth",
]


@dataclass(frozen=True)
class ComprehensiveHouseholdInput:
    net_worth: float
    accrued_labor: float
    continuation_labor: float
    accrued_social_security: float
    continuation_social_security: float
    accrued_db_pension: float
    continuation_db_pension: float
    exclusions: tuple[str, ...] = ()
    source_version: str = "scf-2022"
    assumption_version: str = "2022-baseline-v1"


@dataclass(frozen=True)
class ComprehensiveHouseholdRecord:
    net_worth: float
    accrued_labor: float
    continuation_labor: float
    accrued_social_security: float
    continuation_social_security: float
    accrued_db_pension: float
    continuation_db_pension: float
    defensive_resources: float
    continuation_resources: float
    exclusions: tuple[str, ...]
    source_version: str
    assumption_version: str


def build_comprehensive_household(
    household: ComprehensiveHouseholdInput,
) -> ComprehensiveHouseholdRecord:
    """Assemble auditable totals from separately valued household components."""
    values = (
        household.net_worth,
        household.accrued_labor,
        household.continuation_labor,
        household.accrued_social_security,
        household.continuation_social_security,
        household.accrued_db_pension,
        household.continuation_db_pension,
    )
    if any(pd.isna(value) for value in values):
        raise ValueError("comprehensive household components cannot be missing")
    defensive = (
        household.net_worth
        + household.accrued_labor
        + household.accrued_social_security
        + household.accrued_db_pension
    )
    continuation = (
        household.net_worth
        + household.continuation_labor
        + household.continuation_social_security
        + household.continuation_db_pension
    )
    return ComprehensiveHouseholdRecord(
        **household.__dict__,
        defensive_resources=float(defensive),
        continuation_resources=float(continuation),
    )


def value_detailed_household(
    *,
    net_worth: float,
    household: DetailedHouseholdInput,
    life_table: dict[str, dict[int, float]],
    assumptions: ModelAssumptions = ModelAssumptions(),
    reentry_wage_schedule: Mapping[tuple[str, str], float] | None = None,
) -> ComprehensiveHouseholdRecord:
    """Value person-level SCF inputs and retain explicit model exclusions."""
    exclusions: set[str] = set()

    def future_survival(person: PersonInput) -> list[float]:
        if person.sex not in life_table:
            exclusions.add(f"unknown_sex_{person.sex}")
            return []
        curve = conditional_survival(life_table[person.sex], person.age)
        return curve[1:]

    people = [("respondent", household.respondent)]
    if household.spouse is not None:
        people.append(("spouse", household.spouse))
    survival = {owner: future_survival(person) for owner, person in people}

    labor_values = {"defensive": 0.0, "continuation": 0.0}
    for owner, person in people:
        if not survival[owner]:
            exclusions.add(f"labor_missing_survival_{owner}")
            continue
        for mode in labor_values:
            reentry_income = 0.0
            if person.age < assumptions.retirement_age and reentry_wage_schedule:
                reentry_income = float(
                    reentry_wage_schedule.get((person.sex, age_group(person.age)), 0.0)
                )
            labor_values[mode] += estimate_labor_wealth(
                current_income=person.annual_wage,
                age=person.age,
                retirement_age=assumptions.retirement_age,
                survival=survival[owner],
                reentry_income=reentry_income,
                reentry_probability=assumptions.reentry_probability,
                employment_probability=assumptions.employment_probability,
                wage_growth=assumptions.wage_growth,
                discount_rate=assumptions.discount_rate,
                tax_rate=assumptions.tax_rate,
                mode=mode,
            )
    accrued_labor = labor_values["defensive"]
    continuation_labor = labor_values["continuation"]

    social_values = {"accrued": 0.0, "continuation": 0.0}
    for owner, person in people:
        if not survival[owner]:
            exclusions.add(f"social_security_missing_survival_{owner}")
            continue
        career_years = min(max(person.age - 22, 0), 35)
        ss_person = SocialSecurityPerson(
            age=person.age,
            annual_wage=person.annual_wage,
            annual_reported_benefit=person.annual_social_security,
            career_years=career_years,
            claiming_age=assumptions.retirement_age,
        )
        for mode in social_values:
            result = social_security_wealth(
                ss_person,
                mode=mode,
                survival=survival[owner],
                discount_rate=assumptions.discount_rate,
                payable_factor=assumptions.payable_benefit_factor,
                retirement_age=assumptions.retirement_age,
            )
            social_values[mode] += result.net
            exclusions.update(result.exclusions)

    pension_values = {"accrued": 0.0, "continuation": 0.0}
    for pension in household.db_pensions:
        person = household.spouse if pension.owner == "spouse" else household.respondent
        if person is None or not survival.get(pension.owner):
            exclusions.add(f"pension_missing_owner_or_survival_{pension.owner}")
            continue
        remaining = max(assumptions.retirement_age - person.age, 0)
        career = max(person.age - 22, 0)
        accrued_fraction = 1.0 if pension.status == "current" else career / max(career + remaining, 1)
        plan = DefinedBenefitPlan(
            annual_benefit=pension.annual_benefit,
            current_age=person.age,
            claiming_age=pension.claiming_age,
            accrued_fraction=min(max(accrued_fraction, 0), 1),
        )
        for mode in pension_values:
            result = value_defined_benefit_plan(
                plan,
                mode=mode,
                survival=survival[pension.owner],
                discount_rate=assumptions.discount_rate,
            )
            pension_values[mode] += result.present_value
            exclusions.update(result.exclusions)

    return build_comprehensive_household(
        ComprehensiveHouseholdInput(
            net_worth=float(net_worth),
            accrued_labor=accrued_labor,
            continuation_labor=continuation_labor,
            accrued_social_security=social_values["accrued"],
            continuation_social_security=social_values["continuation"],
            accrued_db_pension=pension_values["accrued"],
            continuation_db_pension=pension_values["continuation"],
            exclusions=tuple(sorted(exclusions)),
            assumption_version=assumptions.version,
        )
    )


def build_reentry_wage_schedule(
    people: Iterable[tuple[PersonInput, float]],
    *,
    retirement_age: int,
) -> dict[tuple[str, str], float]:
    """Return SCF-weighted median positive wages by sex and respondent-age bucket."""
    rows = [
        {
            "sex": person.sex,
            "age_group": age_group(person.age),
            "annual_wage": person.annual_wage,
            "household_weight": weight,
        }
        for person, weight in people
        if person.age < retirement_age and person.annual_wage > 0 and weight > 0
    ]
    if not rows:
        return {}
    frame = pd.DataFrame(rows)
    schedule: dict[tuple[str, str], float] = {}
    for (sex, bucket), group in frame.groupby(["sex", "age_group"], sort=False):
        schedule[(str(sex), str(bucket))] = weighted_median(
            group["annual_wage"], group["household_weight"]
        )
    return schedule


def build_ranked_distributions(
    data: pd.DataFrame,
    *,
    metrics: dict[str, str] | None = None,
) -> dict[str, pd.DataFrame]:
    """Rank each reported resource measure by itself, never by a shared proxy."""
    metrics = metrics or {
        "conventional": "net_worth",
        "defensive": "defensive_resources",
        "continuation": "continuation_resources",
    }
    required = {"household_id", "household_weight", *metrics.values()}
    missing = required - set(data.columns)
    if missing:
        raise ValueError(f"ranked distributions are missing columns: {sorted(missing)}")

    distributions: dict[str, pd.DataFrame] = {}
    for name, metric in metrics.items():
        ranked = data.copy()
        ranked["rank_position"] = weighted_rank_positions(
            ranked[metric],
            ranked["household_weight"],
            tie_breaker=ranked["household_id"],
        )
        ranked["rank_group"] = weighted_rank_groups(
            ranked[metric],
            ranked["household_weight"],
            WEALTH_QUANTILE_GROUPS,
            tie_breaker=ranked["household_id"],
        )
        ranked["rank_basis"] = metric
        distributions[name] = ranked
    return distributions


def aggregate_ranked_resource_distributions(data: pd.DataFrame) -> pd.DataFrame:
    """Return comparable shares after independently ranking each measure."""
    ranked = build_ranked_distributions(data)
    metrics = {
        "conventional": "net_worth",
        "defensive": "defensive_resources",
        "continuation": "continuation_resources",
    }
    rows: list[dict[str, object]] = []
    for measure, frame in ranked.items():
        metric = metrics[measure]
        weighted_values = frame[metric] * frame["household_weight"]
        grand_total = weighted_values.sum()
        for group_name, _, _ in WEALTH_QUANTILE_GROUPS:
            selected = frame["rank_group"] == group_name
            group_total = weighted_values[selected].sum()
            rows.append(
                {
                    "measure": measure,
                    "rank_basis": metric,
                    "rank_group": group_name,
                    "household_share": frame.loc[selected, "household_weight"].sum()
                    / frame["household_weight"].sum(),
                    "weighted_total": group_total,
                    "wealth_share": group_total / grand_total if grand_total else 0.0,
                }
            )
    return pd.DataFrame(rows)


def load_real_wealth_household_data(
    discount_rate: float,
    wage_growth: float,
    retirement_age: int,
    employment_probability: float,
    tax_rate: float,
    liquidity_weight: float,
    raw_dir: Path = Path("data/raw"),
) -> pd.DataFrame:
    zip_path = raw_dir / "scf_2022_extract.zip"
    if not zip_path.exists():
        zip_path = download_scf_extract(raw_dir=raw_dir)

    return build_real_wealth_household_data(
        load_scf_extract(zip_path),
        discount_rate=discount_rate,
        wage_growth=wage_growth,
        retirement_age=retirement_age,
        employment_probability=employment_probability,
        tax_rate=tax_rate,
        liquidity_weight=liquidity_weight,
    )


def load_comprehensive_household_data(
    assumptions: ModelAssumptions,
    raw_dir: Path = Path("data/raw"),
) -> pd.DataFrame:
    """Load pinned SCF summary/full inputs and value all modeled components."""
    summary_path = raw_dir / "scf_2022_extract.zip"
    if not summary_path.exists():
        summary_path = download_scf_extract(raw_dir=raw_dir)
    full_path = raw_dir / "scf_2022_full.zip"
    if not full_path.exists():
        full_path, _ = download_artifact(load_source_registry()["scf_full"], raw_dir)

    summary = normalize_scf_rows(load_scf_extract(summary_path)).set_index("scf_row_id")
    detailed = load_detailed_scf(full_path)
    life_table = load_ssa_period_life_table()
    detailed_households = [
        build_detailed_household_input(values) for values in detailed.to_dict("records")
    ]
    reentry_people: list[tuple[PersonInput, float]] = []
    for household in detailed_households:
        if household.row_id not in summary.index:
            continue
        weight = float(summary.loc[household.row_id, "household_weight"])
        reentry_people.append((household.respondent, weight))
        if household.spouse is not None:
            reentry_people.append((household.spouse, weight))
    reentry_wage_schedule = build_reentry_wage_schedule(
        reentry_people, retirement_age=assumptions.retirement_age
    )
    rows: list[dict[str, object]] = []
    unmatched = 0
    for household in detailed_households:
        if household.row_id not in summary.index:
            unmatched += 1
            continue
        base = summary.loc[household.row_id]
        record = value_detailed_household(
            net_worth=base["traditional_net_worth"],
            household=household,
            life_table=life_table,
            assumptions=assumptions,
            reentry_wage_schedule=reentry_wage_schedule,
        )
        rows.append(
            {
                "household_id": household.row_id,
                "family_id": household.family_id,
                "implicate": household.implicate,
                "household_weight": float(base["household_weight"]),
                "age": household.respondent.age,
                **record.__dict__,
                "exclusions": ";".join(record.exclusions),
            }
        )
    if unmatched:
        raise ValueError(f"{unmatched} detailed SCF rows did not match the summary extract")
    if not rows:
        raise ValueError("no comprehensive SCF household records were produced")
    return pd.DataFrame(rows)


def build_real_wealth_household_data(
    scf_rows: pd.DataFrame | Iterable[dict],
    discount_rate: float,
    wage_growth: float,
    retirement_age: int,
    employment_probability: float,
    tax_rate: float,
    liquidity_weight: float,
) -> pd.DataFrame:
    data = normalize_scf_rows(scf_rows)
    data["wealth_quantile"] = assign_weighted_quantile_group(
        data["traditional_net_worth"],
        data["household_weight"],
        WEALTH_QUANTILE_GROUPS,
    )
    data["wealth_quantile"] = pd.Categorical(data["wealth_quantile"], categories=WEALTH_QUANTILES, ordered=True)
    data["age_group"] = pd.Categorical(data["age"].map(age_group), categories=AGE_BUCKETS, ordered=True)

    data["human_capital"] = [
        estimate_human_capital(
            current_labor_income=labor_income,
            age=int(age),
            retirement_age=retirement_age,
            wage_growth=wage_growth,
            discount_rate=discount_rate,
            employment_probability=employment_probability,
            tax_rate=tax_rate,
        )
        for labor_income, age in zip(data["labor_income"], data["age"], strict=True)
    ]
    data["combined_real_wealth"] = data["traditional_net_worth"] + data["human_capital"]
    data["liquidity_adjusted_real_wealth"] = (
        data["traditional_net_worth"] + liquidity_weight * data["human_capital"]
    )
    data["household_population_share"] = data["household_weight"] / data["household_weight"].sum()
    return data


def aggregate_real_country_distribution_by_quantile(data: pd.DataFrame) -> pd.DataFrame:
    working = data.copy()
    for metric in REPORT_METRICS:
        working[f"{metric}_total"] = working[metric] * working["household_weight"]

    totals = (
        working.groupby("wealth_quantile", observed=False, sort=False)
        .agg(
            population_share=("household_population_share", "sum"),
            household_count=("household_weight", "sum"),
            traditional_net_worth_total=("traditional_net_worth_total", "sum"),
            human_capital_total=("human_capital_total", "sum"),
            combined_real_wealth_total=("combined_real_wealth_total", "sum"),
            liquidity_adjusted_real_wealth_total=("liquidity_adjusted_real_wealth_total", "sum"),
        )
        .reset_index()
    )
    totals["wealth_quantile"] = totals["wealth_quantile"].astype(str)

    for metric in REPORT_METRICS:
        total_column = f"{metric}_total"
        share_column = f"{metric}_share"
        grand_total = totals[total_column].sum()
        totals[share_column] = totals[total_column] / grand_total if grand_total else 0.0

    totals["human_capital_minus_marketable_share"] = (
        totals["human_capital_share"] - totals["traditional_net_worth_share"]
    )
    totals["combined_minus_marketable_share"] = (
        totals["combined_real_wealth_share"] - totals["traditional_net_worth_share"]
    )
    return _sort_report_groups(totals)


def aggregate_real_by_age(data: pd.DataFrame) -> pd.DataFrame:
    return _weighted_metric_table(data, ["age_group"])


def aggregate_real_age_quantile_matrix(data: pd.DataFrame) -> pd.DataFrame:
    return _weighted_metric_table(data, ["age_group", "wealth_quantile"])


def age_group(age: int | float) -> str:
    if age < 25:
        return "<25"
    if age < 35:
        return "25-34"
    if age < 45:
        return "35-44"
    if age < 55:
        return "45-54"
    if age < 65:
        return "55-64"
    if age < 75:
        return "65-74"
    return "75+"


def normalize_scf_rows(scf_rows: pd.DataFrame | Iterable[dict]) -> pd.DataFrame:
    data = pd.DataFrame(scf_rows).copy()
    data.columns = [str(column).strip().lower() for column in data.columns]

    required_columns = {"wgt", "age", "wageinc", "networth"}
    missing_columns = required_columns - set(data.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"SCF rows are missing required columns: {missing}")

    if "scf_row_id" not in data.columns:
        data["scf_row_id"] = data["y1"] if "y1" in data.columns else range(1, len(data) + 1)
    if "family_id" not in data.columns:
        if "yy1" in data.columns:
            data["family_id"] = data["yy1"]
        else:
            data["family_id"] = data["scf_row_id"]
    if "implicate" not in data.columns:
        if "y1" in data.columns:
            data["implicate"] = pd.to_numeric(data["y1"], errors="coerce") % 10
        else:
            data["implicate"] = 1

    normalized = pd.DataFrame(
        {
            "scf_row_id": data["scf_row_id"],
            "family_id": pd.to_numeric(data["family_id"], errors="coerce"),
            "implicate": pd.to_numeric(data["implicate"], errors="coerce"),
            "household_weight": pd.to_numeric(data["wgt"], errors="coerce"),
            "age": pd.to_numeric(data["age"], errors="coerce"),
            "labor_income": pd.to_numeric(data["wageinc"], errors="coerce").clip(lower=0),
            "traditional_net_worth": pd.to_numeric(data["networth"], errors="coerce"),
        }
    ).dropna(subset=["household_weight", "age", "labor_income", "traditional_net_worth"])

    normalized = normalized[normalized["household_weight"] > 0].copy()
    if normalized.empty:
        raise ValueError("SCF rows did not contain any valid positive-weight households")

    return normalized


def _weighted_metric_table(data: pd.DataFrame, group_columns: list[str]) -> pd.DataFrame:
    rows = []
    for group_key, group in data.groupby(group_columns, observed=True, sort=False):
        if not isinstance(group_key, tuple):
            group_key = (group_key,)
        row = dict(zip(group_columns, group_key, strict=True))
        row["household_count"] = group["household_weight"].sum()
        for metric in REPORT_METRICS:
            row[metric] = weighted_median(group[metric], group["household_weight"])
        rows.append(row)

    result = pd.DataFrame(rows)
    for column in group_columns:
        result[column] = result[column].astype(str)
    return _sort_report_groups(result)


def _sort_report_groups(data: pd.DataFrame) -> pd.DataFrame:
    sorted_data = data.copy()
    sort_columns = []
    if "age_group" in sorted_data.columns:
        sorted_data["age_group"] = pd.Categorical(sorted_data["age_group"], categories=AGE_BUCKETS, ordered=True)
        sort_columns.append("age_group")
    if "wealth_quantile" in sorted_data.columns:
        sorted_data["wealth_quantile"] = pd.Categorical(
            sorted_data["wealth_quantile"],
            categories=WEALTH_QUANTILES,
            ordered=True,
        )
        sort_columns.append("wealth_quantile")

    if sort_columns:
        sorted_data = sorted_data.sort_values(sort_columns).reset_index(drop=True)
        for column in sort_columns:
            sorted_data[column] = sorted_data[column].astype(str)

    return sorted_data
