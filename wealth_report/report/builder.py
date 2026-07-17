from __future__ import annotations

from pathlib import Path
from dataclasses import dataclass
import math
from typing import Iterable, Mapping

import pandas as pd

from wealth_report.model.actuarial import conditional_survival
from wealth_report.model.assumptions import ModelAssumptions
from wealth_report.model.labor import (
    estimate_labor_wealth,
    projected_labor_income_stream,
)
from wealth_report.model.inheritance import allocate_inheritance_reallocation
from wealth_report.model.income_security import value_income_security_floor
from wealth_report.model.pensions import (
    DefinedBenefitPlan,
    defined_benefit_income_stream,
    value_defined_benefit_plan,
)
from wealth_report.providers.scf.detailed import (
    DetailedHouseholdInput,
    PersonInput,
    build_detailed_household_input,
    load_detailed_scf,
)
from wealth_report.providers.scf.summary import (
    download_scf_extract,
    load_scf_extract,
    normalize_scf_rows,
)
from wealth_report.model.social_security import (
    SocialSecurityPerson,
    social_security_income_stream,
    social_security_wealth,
)
from wealth_report.providers.sources import download_artifact, load_source_registry
from wealth_report.providers.ssa.mortality import load_ssa_period_life_table
from wealth_report.model.statistics import weighted_median, weighted_rank_groups, weighted_rank_positions


SCF_2022_DATASET_LABEL = "Federal Reserve 2022 SCF public summary extract"
SCF_2022_DATA_NOTE = (
    "The conventional measure uses the Federal Reserve 2022 Survey of Consumer Finances public "
    "summary extract and SCF household weights. The comprehensive model additionally uses the full "
    "public file's respondent/spouse wage, work-schedule, retirement, and pension fields."
)

WEALTH_QUANTILE_GROUPS = [
    ("Bottom 50%", 0.0, 0.5),
    ("50-90%", 0.5, 0.9),
    ("90-99%", 0.9, 0.99),
    ("99-99.9%", 0.99, 0.999),
    ("Top 0.1%", 0.999, 1.0),
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
    continuation_income_security_floor: float = 0.0
    continuation_expected_inheritance: float = 0.0
    continuation_estate_donor_reserve: float = 0.0
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
    continuation_income_security_floor: float
    defensive_resources: float
    continuation_resources: float
    exclusions: tuple[str, ...]
    source_version: str
    assumption_version: str
    continuation_expected_inheritance: float = 0.0
    continuation_estate_donor_reserve: float = 0.0


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
        household.continuation_income_security_floor,
        household.continuation_expected_inheritance,
        household.continuation_estate_donor_reserve,
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
        + household.continuation_income_security_floor
        + household.continuation_expected_inheritance
        - household.continuation_estate_donor_reserve
    )
    return ComprehensiveHouseholdRecord(
        **household.__dict__,
        defensive_resources=float(defensive),
        continuation_resources=float(continuation),
    )


def apply_inheritance_reallocation(
    households: pd.DataFrame,
    *,
    life_table: dict[str, dict[int, float]],
    assumptions: ModelAssumptions,
) -> pd.DataFrame:
    """Reallocate expected inheritance claims without changing current net worth."""
    component_columns = (
        "net_worth",
        "continuation_labor",
        "continuation_social_security",
        "continuation_db_pension",
        "continuation_income_security_floor",
    )
    missing = set(component_columns).difference(households.columns)
    if missing:
        raise ValueError(
            "inheritance reallocation is missing continuation components: "
            f"{sorted(missing)}"
        )
    for column in component_columns:
        if not households[column].map(_is_finite_numeric).all():
            raise ValueError(
                f"inheritance reallocation {column} must be finite and numeric"
            )
    allocated, _ = allocate_inheritance_reallocation(
        households,
        life_table=life_table,
        horizon_years=assumptions.inheritance_horizon_years,
        discount_rate=assumptions.discount_rate,
    )
    allocated["continuation_expected_inheritance"] = allocated["inheritance_credit"]
    allocated["continuation_estate_donor_reserve"] = allocated["estate_donor_reserve"]
    allocated["continuation_resources"] = (
        allocated["net_worth"]
        + allocated["continuation_labor"]
        + allocated["continuation_social_security"]
        + allocated["continuation_db_pension"]
        + allocated["continuation_income_security_floor"]
        + allocated["continuation_expected_inheritance"]
        - allocated["continuation_estate_donor_reserve"]
    )
    return allocated


def _is_finite_numeric(value: object) -> bool:
    if isinstance(value, (bool, str, bytes)) or type(value).__name__ == "bool":
        return False
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


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
    continuation_labor_streams: dict[str, list[float]] = {}
    for owner, person in people:
        if not survival[owner]:
            exclusions.add(f"labor_missing_survival_{owner}")
            continue
        reentry_income = 0.0
        if person.age < assumptions.retirement_age and reentry_wage_schedule:
            reentry_income = float(
                reentry_wage_schedule.get((person.sex, age_group(person.age)), 0.0)
            )
        continuation_labor_streams[owner] = projected_labor_income_stream(
            current_income=person.annual_wage,
            age=person.age,
            retirement_age=assumptions.retirement_age,
            reentry_income=reentry_income,
            reentry_probability=assumptions.reentry_probability,
            employment_probability=assumptions.employment_probability,
            wage_growth=assumptions.wage_growth,
            tax_rate=assumptions.tax_rate,
            mode="continuation",
        )
        for mode in labor_values:
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
    continuation_social_streams: dict[str, list[float]] = {}
    for owner, person in people:
        if not survival[owner]:
            exclusions.add(f"social_security_missing_survival_{owner}")
            continue
        career_years = min(max(person.age - 22, 0), 35)
        ss_person = SocialSecurityPerson(
            age=person.age,
            annual_wage=person.annual_wage,
            annual_reported_benefit=person.annual_social_security,
            reported_benefit_type=person.social_security_benefit_type,
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
        continuation_social_streams[owner] = social_security_income_stream(
            ss_person,
            survival=survival[owner],
            payable_factor=assumptions.payable_benefit_factor,
            retirement_age=assumptions.retirement_age,
            mode="continuation",
        )

    pension_values = {"accrued": 0.0, "continuation": 0.0}
    continuation_pension_streams: dict[str, list[list[float]]] = {
        owner: [] for owner, _ in people
    }
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
        continuation_pension_streams[pension.owner].append(
            defined_benefit_income_stream(
                plan,
                mode="continuation",
                years=len(survival[pension.owner]),
            )
        )

    horizon = max((len(values) for values in survival.values()), default=0)
    annual_other_income = [0.0] * horizon
    household_survival = [0.0] * horizon
    for period in range(horizon):
        survival_values = [
            curve[period] for curve in survival.values() if period < len(curve)
        ]
        household_survival[period] = (
            1 - math.prod(1 - value for value in survival_values)
            if survival_values
            else 0.0
        )
        for owner, _ in people:
            if period < len(continuation_labor_streams.get(owner, [])):
                annual_other_income[period] += continuation_labor_streams[owner][period]
            if period < len(continuation_social_streams.get(owner, [])):
                annual_other_income[period] += continuation_social_streams[owner][period]
            for stream in continuation_pension_streams.get(owner, []):
                if period < len(stream):
                    annual_other_income[period] += stream[period]
    continuation_income_security_floor = value_income_security_floor(
        other_income=annual_other_income,
        monthly_benchmark=assumptions.income_security_floor_monthly,
        adult_count=len(people),
        survival=household_survival,
        discount_rate=assumptions.discount_rate,
    )

    return build_comprehensive_household(
        ComprehensiveHouseholdInput(
            net_worth=float(net_worth),
            accrued_labor=accrued_labor,
            continuation_labor=continuation_labor,
            accrued_social_security=social_values["accrued"],
            continuation_social_security=social_values["continuation"],
            accrued_db_pension=pension_values["accrued"],
            continuation_db_pension=pension_values["continuation"],
            continuation_income_security_floor=continuation_income_security_floor,
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
                "sex": household.respondent.sex,
                "expected_inheritance_amount": household.expected_inheritance_amount,
                "expects_sizable_estate": household.expects_sizable_estate,
                **record.__dict__,
                "exclusions": ";".join(record.exclusions),
            }
        )
    if unmatched:
        raise ValueError(f"{unmatched} detailed SCF rows did not match the summary extract")
    if not rows:
        raise ValueError("no comprehensive SCF household records were produced")
    return apply_inheritance_reallocation(
        pd.DataFrame(rows), life_table=life_table, assumptions=assumptions
    )


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
