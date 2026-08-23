"""Run the frozen Phase 7 Issaquah Creek hypothesis analyses in one pass.

The script validates the frozen inputs before calculating any association,
executes analyses in protocol order, and publishes an output package only after
the complete run succeeds. It does not modify any frozen input.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import platform
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable


ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".matplotlib-cache"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scipy
from scipy import stats
import statsmodels
import statsmodels.api as sm
from statsmodels.stats.outliers_influence import variance_inflation_factor


ANALYSIS_DATE = "2026-08-23"
PROTOCOL_VERSION = "1.1"
EXPECTED_PROTOCOL_SHA256 = (
    "33BFCCD299DA7064462B9F66F1944638E6949FFB5406C78DC9EE6E97E8D15DE2"
)
BASE_SEED = 20260823
PERMUTATION_REPETITIONS = 100_000
BOOTSTRAP_REPETITIONS = 10_000
ALPHA = 0.05
TEMPORAL_LAG1_TRIGGER = 0.30

MASTER_PATH = ROOT / "data/gold/issaquah_creek_master.csv"
EXPOSURE_PATH = ROOT / (
    "outputs/temperature_proxy/"
    "issaquah_life_stage_temperature_exposure_1995_2025.csv"
)
ENVIRONMENT_PATH = ROOT / "data/silver/issaquah_annual_environment.csv"
PROTOCOL_PATH = ROOT / "docs/phase7_hypothesis_analysis_protocol.md"
PREASSOCIATION_GATE_PATH = ROOT / (
    "outputs/temperature_proxy/"
    "issaquah_temperature_proxy_preassociation_validation.json"
)
OUTPUT_DIR = ROOT / "outputs/phase7"

TEMPORAL_REQUIRED_FIELDS = (
    "analysis_id",
    "n",
    "predictor_raw_lag1_rank_autocorrelation",
    "outcome_raw_lag1_rank_autocorrelation",
    "predictor_residual_lag1_autocorrelation",
    "outcome_residual_lag1_autocorrelation",
    "rho_primary",
    "rho_detrended",
    "direction_status",
    "magnitude_change_pct",
    "circular_shift_status",
    "circular_shift_exact_two_sided_p",
)


ANALYSIS_SPECS = {
    "A1": {
        "species": "Chinook",
        "window_id": "aug15_sep30",
        "label": "Chinook adult migration: Aug 15-Sep 30",
        "expected_direction": "negative",
    },
    "A2": {
        "species": "Chinook",
        "window_id": "aug15_oct31",
        "label": "Chinook window sensitivity: Aug 15-Oct 31",
        "expected_direction": "negative",
    },
    "A3": {
        "species": "Coho",
        "window_id": "sep15_oct31",
        "label": "Coho adult migration: Sep 15-Oct 31",
        "expected_direction": "negative",
    },
    "A4": {
        "species": "Coho",
        "window_id": "sep15_nov30",
        "label": "Coho window sensitivity: Sep 15-Nov 30",
        "expected_direction": "negative",
    },
    "A5": {
        "species": "Coho",
        "window_id": "jun_sep",
        "label": "Coho juvenile/rearing: Jun-Sep at return year minus 2",
        "expected_direction": "negative",
    },
}


@dataclass(frozen=True)
class PredictorSpec:
    term: str
    source: str
    transform: str = "identity"


@dataclass
class OLSBundle:
    model_id: str
    analysis_id: str
    family: str
    sensitivity_id: str
    species: str
    outcome: str
    outcome_scale: str
    data: pd.DataFrame
    year_column: str
    predictors: tuple[PredictorSpec, ...]
    coefficient_rows: list[dict[str, object]]
    diagnostic_rows: list[dict[str, object]]
    summary: dict[str, object]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def require_columns(table: pd.DataFrame, required: Iterable[str], label: str) -> None:
    missing = sorted(set(required) - set(table.columns))
    if missing:
        raise ValueError(f"{label} is missing required fields: {missing}")


def allclose(left: pd.Series, right: pd.Series, atol: float = 1e-12) -> bool:
    return bool(
        np.allclose(
            pd.to_numeric(left, errors="coerce"),
            pd.to_numeric(right, errors="coerce"),
            rtol=0.0,
            atol=atol,
            equal_nan=False,
        )
    )


def json_ready(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_ready(item) for item in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        return None if not math.isfinite(float(value)) else float(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    return value


def validation_check(
    rows: list[dict[str, object]],
    check_id: str,
    passed: bool,
    detail: str,
) -> None:
    rows.append(
        {
            "check_id": check_id,
            "status": "PASS" if passed else "FAIL",
            "detail": detail,
        }
    )


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, object]]:
    for path in (
        MASTER_PATH,
        EXPOSURE_PATH,
        ENVIRONMENT_PATH,
        PROTOCOL_PATH,
        PREASSOCIATION_GATE_PATH,
    ):
        if not path.is_file():
            raise FileNotFoundError(f"Frozen input is missing: {relative(path)}")
    master = pd.read_csv(MASTER_PATH)
    exposure = pd.read_csv(EXPOSURE_PATH)
    environment = pd.read_csv(ENVIRONMENT_PATH)
    for field in ("return_year_in_1997_2025", "return_year_eligible_for_phase7"):
        if exposure[field].dtype != bool:
            normalized = exposure[field].astype(str).str.strip().str.lower()
            if not normalized.isin({"true", "false"}).all():
                raise ValueError(f"Temperature exposure has invalid Boolean values in {field}")
            exposure[field] = normalized.map({"true": True, "false": False})
    with PREASSOCIATION_GATE_PATH.open("r", encoding="utf-8") as handle:
        gate = json.load(handle)
    return master, exposure, environment, gate


def join_response_rows(
    exposure: pd.DataFrame, master: pd.DataFrame
) -> dict[str, pd.DataFrame]:
    joined: dict[str, pd.DataFrame] = {}
    for analysis_id in ("A1", "A2", "A3", "A4", "A5"):
        left = exposure.loc[
            (exposure["analysis_id"] == analysis_id)
            & exposure["return_year_eligible_for_phase7"]
        ].copy()
        merged = left.merge(
            master,
            how="left",
            left_on=["species", "primary_return_year"],
            right_on=["species", "return_year"],
            validate="one_to_one",
            indicator=True,
            suffixes=("_exposure", "_response"),
        )
        joined[analysis_id] = merged.sort_values("primary_return_year").reset_index(
            drop=True
        )
    return joined


def validate_inputs(
    master: pd.DataFrame,
    exposure: pd.DataFrame,
    environment: pd.DataFrame,
    gate: dict[str, object],
) -> tuple[list[dict[str, object]], dict[str, pd.DataFrame]]:
    checks: list[dict[str, object]] = []
    require_columns(
        master,
        (
            "return_year",
            "species",
            "total_adults",
            "total_jacks",
            "adult_plus_jacks",
        ),
        "salmon master",
    )
    require_columns(
        exposure,
        (
            "exposure_year",
            "analysis_id",
            "window_id",
            "species",
            "primary_return_year",
            "return_year_eligible_for_phase7",
            "expected_days",
            "matched_window_mean_usgs_flow_cfs",
            "primary_thermal_model_id",
            "primary_thermal_variable",
            "primary_thermal_value_c",
            "sensitivity_thermal_model_id",
            "sensitivity_thermal_variable",
            "sensitivity_thermal_value_c",
            "threshold_count_metric_status",
            "other_nonmean_thermal_metric_status",
            "t1_complete_days",
            "t1_window_mean_proxy_c",
            "t1_extrapolation_days",
            "t1_extrapolation_pct",
            "t2_complete_days",
            "t2_window_mean_proxy_c",
            "t2_extrapolation_days",
            "t2_extrapolation_pct",
            "t2_minus_t1_window_mean_c",
        ),
        "temperature exposure",
    )
    require_columns(
        environment,
        ("return_year", "swe_apr01_inches", "flow_jul_sep_mean_cfs"),
        "annual environment",
    )

    protocol_hash = sha256_file(PROTOCOL_PATH)
    validation_check(
        checks,
        "protocol_sha256",
        protocol_hash == EXPECTED_PROTOCOL_SHA256,
        f"observed={protocol_hash}; expected={EXPECTED_PROTOCOL_SHA256}",
    )
    frozen_protocol = gate.get("frozen_phase7_protocol", {})
    validation_check(
        checks,
        "gate_protocol_identity",
        frozen_protocol.get("version") == PROTOCOL_VERSION
        and frozen_protocol.get("sha256") == EXPECTED_PROTOCOL_SHA256
        and frozen_protocol.get("amendments") == ["D-022"],
        "gate must identify protocol v1.1, exact SHA-256, and amendment D-022",
    )
    validation_check(
        checks,
        "preassociation_gate",
        gate.get("gate_status") == "PASS_FOR_PHASE7_PROXY_INPUT_CONSTRUCTION"
        and gate.get("salmon_association_tests_run") is False,
        "construction gate must pass and retain salmon_association_tests_run=false",
    )

    expected_years = set(range(1997, 2026))
    master_keys_unique = not master.duplicated(["species", "return_year"]).any()
    validation_check(
        checks,
        "response_rows_unique",
        master_keys_unique,
        "no duplicate species-return_year response keys",
    )
    species_years_ok = (
        len(master) == 58
        and set(master["species"]) == {"Chinook", "Coho"}
        and all(
            set(master.loc[master["species"] == species, "return_year"].astype(int))
            == expected_years
            for species in ("Chinook", "Coho")
        )
    )
    validation_check(
        checks,
        "response_species_year_coverage",
        species_years_ok,
        "29 unique 1997-2025 rows are required for each species",
    )
    response_identity = allclose(
        master["adult_plus_jacks"], master["total_adults"] + master["total_jacks"]
    )
    validation_check(
        checks,
        "adult_plus_jacks_identity",
        response_identity,
        "adult_plus_jacks must equal total_adults + total_jacks",
    )

    exposure_ids_ok = len(exposure) == 155 and set(exposure["analysis_id"]) == set(
        ANALYSIS_SPECS
    )
    validation_check(
        checks,
        "exposure_shape",
        exposure_ids_ok,
        "155 rows and analysis IDs A1-A5 are required",
    )
    duplicate_exposure = exposure.duplicated(["analysis_id", "exposure_year"]).any()
    validation_check(
        checks,
        "exposure_rows_unique",
        not duplicate_exposure,
        "one row per analysis_id-exposure_year",
    )
    for analysis_id, spec in ANALYSIS_SPECS.items():
        group = exposure.loc[exposure["analysis_id"] == analysis_id]
        eligible = group.loc[group["return_year_eligible_for_phase7"]]
        structural_ok = (
            len(group) == 31
            and len(eligible) == 29
            and set(group["species"]) == {spec["species"]}
            and set(group["window_id"]) == {spec["window_id"]}
        )
        validation_check(
            checks,
            f"{analysis_id.lower()}_rows_species_window",
            structural_ok,
            f"31 total/29 eligible rows; {spec['species']}; {spec['window_id']}",
        )
        eligible_years_ok = set(eligible["primary_return_year"].astype(int)) == expected_years
        validation_check(
            checks,
            f"{analysis_id.lower()}_eligible_return_years",
            eligible_years_ok,
            "eligible primary return years must be exactly 1997-2025",
        )

    a5 = exposure.loc[exposure["analysis_id"] == "A5"]
    a5_eligible = a5.loc[a5["return_year_eligible_for_phase7"]]
    a5_mapping_ok = (
        set(a5_eligible["exposure_year"].astype(int)) == set(range(1995, 2024))
        and np.array_equal(
            a5_eligible["primary_return_year"].to_numpy(int),
            a5_eligible["exposure_year"].to_numpy(int) + 2,
        )
    )
    validation_check(
        checks,
        "a5_lag_identity",
        a5_mapping_ok,
        "A5 must map exposure years 1995-2023 to return years 1997-2025",
    )

    designation_ok = (
        exposure["primary_thermal_model_id"].eq("T2").all()
        and exposure["primary_thermal_variable"].eq("t2_window_mean_proxy_c").all()
        and exposure["sensitivity_thermal_model_id"].eq("T1").all()
        and exposure["sensitivity_thermal_variable"].eq("t1_window_mean_proxy_c").all()
        and exposure["threshold_count_metric_status"].eq("exploratory_only").all()
        and exposure["other_nonmean_thermal_metric_status"].eq("exploratory_only").all()
    )
    validation_check(
        checks,
        "thermal_designation",
        designation_ok,
        "T2 mean primary, T1 mean sensitivity, and nonmean metrics exploratory only",
    )
    thermal_values_ok = allclose(
        exposure["primary_thermal_value_c"], exposure["t2_window_mean_proxy_c"]
    ) and allclose(
        exposure["sensitivity_thermal_value_c"],
        exposure["t1_window_mean_proxy_c"],
    )
    validation_check(
        checks,
        "t1_t2_value_identities",
        thermal_values_ok,
        "primary and sensitivity aliases must exactly reproduce T2 and T1 means",
    )
    difference_ok = allclose(
        exposure["t2_minus_t1_window_mean_c"],
        exposure["t2_window_mean_proxy_c"] - exposure["t1_window_mean_proxy_c"],
        atol=0.0011,
    )
    validation_check(
        checks,
        "t2_minus_t1_identity",
        difference_ok,
        "stored T2-minus-T1 value must match component means to output precision",
    )

    complete_days_ok = (
        exposure["t1_complete_days"].eq(exposure["expected_days"]).all()
        and exposure["t2_complete_days"].eq(exposure["expected_days"]).all()
    )
    validation_check(
        checks,
        "thermal_window_completeness",
        complete_days_ok,
        "both models must cover every expected window day",
    )
    extrapolation_ok = True
    extrapolation_detail: list[str] = []
    for model in ("t1", "t2"):
        days = pd.to_numeric(exposure[f"{model}_extrapolation_days"], errors="coerce")
        pct = pd.to_numeric(exposure[f"{model}_extrapolation_pct"], errors="coerce")
        expected = pd.to_numeric(exposure["expected_days"], errors="coerce")
        model_ok = (
            days.notna().all()
            and np.equal(days, np.floor(days)).all()
            and days.ge(0).all()
            and days.le(expected).all()
            and np.allclose(pct, days / expected * 100.0, rtol=0.0, atol=0.0011)
        )
        extrapolation_ok = extrapolation_ok and bool(model_ok)
        extrapolation_detail.append(
            f"{model.upper()}: {int((days > 0).sum())} flagged windows, "
            f"{int(days.sum())} flagged window-days"
        )
    validation_check(
        checks,
        "extrapolation_flags",
        extrapolation_ok,
        "; ".join(extrapolation_detail),
    )

    audits_ok = all(
        gate.get(f"{model}_extrapolation_audit", {}).get("total_extrapolation_days")
        == expected_days
        and gate.get(f"{model}_extrapolation_audit", {}).get("total_output_days")
        == 11_323
        for model, expected_days in (("t1", 304), ("t2", 248))
    )
    validation_check(
        checks,
        "daily_proxy_and_audit_coverage",
        audits_ok,
        "gate must attest 11,323 daily rows/model and complete T1=304/T2=248 audits",
    )
    gate_designation = gate.get("thermal_variable_designation", {})
    gate_designation_ok = (
        gate_designation.get("primary_model_id") == "T2"
        and gate_designation.get("primary_variable") == "t2_window_mean_proxy_c"
        and gate_designation.get("sensitivity_model_id") == "T1"
        and gate_designation.get("threshold_count_metrics") == "exploratory_only"
    )
    validation_check(
        checks,
        "gate_thermal_designation",
        gate_designation_ok,
        "pre-association gate must independently designate T2 as primary",
    )

    temporal_contract_ok = set(TEMPORAL_REQUIRED_FIELDS) == {
        "analysis_id",
        "n",
        "predictor_raw_lag1_rank_autocorrelation",
        "outcome_raw_lag1_rank_autocorrelation",
        "predictor_residual_lag1_autocorrelation",
        "outcome_residual_lag1_autocorrelation",
        "rho_primary",
        "rho_detrended",
        "direction_status",
        "magnitude_change_pct",
        "circular_shift_status",
        "circular_shift_exact_two_sided_p",
    }
    validation_check(
        checks,
        "d022_output_contract",
        temporal_contract_ok,
        "D-022 lag-1, detrended rho, magnitude, and circular-shift fields exposed",
    )

    joined = join_response_rows(exposure, master)
    for analysis_id, table in joined.items():
        join_ok = (
            len(table) == 29
            and table["_merge"].eq("both").all()
            and table["species"].eq(ANALYSIS_SPECS[analysis_id]["species"]).all()
            and table["return_year"].eq(table["primary_return_year"]).all()
            and not table.duplicated(["species", "return_year"]).any()
        )
        validation_check(
            checks,
            f"{analysis_id.lower()}_response_join",
            join_ok,
            "exact species and primary-return-year one-to-one join; 29 rows",
        )
        complete_fields = [
            "primary_thermal_value_c",
            "sensitivity_thermal_value_c",
            "matched_window_mean_usgs_flow_cfs",
            "total_adults",
            "adult_plus_jacks",
            "t2_extrapolation_days",
        ]
        complete_count = int(table[complete_fields].notna().all(axis=1).sum())
        validation_check(
            checks,
            f"{analysis_id.lower()}_complete_cases",
            complete_count == 29,
            f"complete cases={complete_count}; required=29",
        )

    env_a6 = environment.loc[environment["return_year"].between(1997, 2025)]
    a6_complete = int(
        env_a6[["swe_apr01_inches", "flow_jul_sep_mean_cfs"]]
        .notna()
        .all(axis=1)
        .sum()
    )
    validation_check(
        checks,
        "a6_complete_cases",
        len(env_a6) == 29
        and not env_a6["return_year"].duplicated().any()
        and set(env_a6["return_year"].astype(int)) == expected_years
        and a6_complete == 29,
        f"unique 1997-2025 rows={len(env_a6)}; complete cases={a6_complete}",
    )
    a7_complete = int(
        a5[["matched_window_mean_usgs_flow_cfs", "primary_thermal_value_c"]]
        .notna()
        .all(axis=1)
        .sum()
    )
    validation_check(
        checks,
        "a7_complete_cases",
        len(a5) == 31 and a7_complete == 31,
        f"1995-2025 A5 exposure rows={len(a5)}; complete cases={a7_complete}",
    )

    failures = [row for row in checks if row["status"] != "PASS"]
    if failures:
        details = "\n".join(
            f"- {row['check_id']}: {row['detail']}" for row in failures
        )
        raise ValueError(f"Phase 7 input validation failed:\n{details}")
    return checks, joined


def midrank_correlation(x: np.ndarray, y: np.ndarray) -> float:
    rank_x = stats.rankdata(np.asarray(x, dtype=float), method="average")
    rank_y = stats.rankdata(np.asarray(y, dtype=float), method="average")
    return float(np.corrcoef(rank_x, rank_y)[0, 1])


def permutation_spearman(
    x: np.ndarray, y: np.ndarray, repetitions: int, seed: int
) -> tuple[float, int]:
    rank_x = stats.rankdata(np.asarray(x, dtype=float), method="average")
    rank_y = stats.rankdata(np.asarray(y, dtype=float), method="average")
    x_centered = rank_x - rank_x.mean()
    y_centered = rank_y - rank_y.mean()
    denominator = float(np.linalg.norm(x_centered) * np.linalg.norm(y_centered))
    observed = float(np.dot(x_centered, y_centered) / denominator)
    rng = np.random.default_rng(seed)
    extreme = 0
    completed = 0
    chunk_size = 2_000
    while completed < repetitions:
        size = min(chunk_size, repetitions - completed)
        tiled = np.broadcast_to(y_centered, (size, len(y_centered))).copy()
        permuted = rng.permuted(tiled, axis=1)
        correlations = permuted @ x_centered / denominator
        extreme += int(np.count_nonzero(np.abs(correlations) >= abs(observed)))
        completed += size
    return float((1 + extreme) / (repetitions + 1)), extreme


def bootstrap_spearman_interval(
    x: np.ndarray, y: np.ndarray, repetitions: int, seed: int
) -> tuple[float, float, int]:
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    rng = np.random.default_rng(seed)
    finite: list[np.ndarray] = []
    completed = 0
    chunk_size = 1_000
    while completed < repetitions:
        size = min(chunk_size, repetitions - completed)
        indices = rng.integers(0, len(x), size=(size, len(x)))
        rank_x = stats.rankdata(x[indices], axis=1, method="average")
        rank_y = stats.rankdata(y[indices], axis=1, method="average")
        rank_x -= rank_x.mean(axis=1, keepdims=True)
        rank_y -= rank_y.mean(axis=1, keepdims=True)
        denominator = np.sqrt(
            np.sum(rank_x**2, axis=1) * np.sum(rank_y**2, axis=1)
        )
        valid = denominator > 0
        correlations = np.sum(rank_x[valid] * rank_y[valid], axis=1) / denominator[valid]
        finite.append(correlations[np.isfinite(correlations)])
        completed += size
    estimates = np.concatenate(finite)
    if estimates.size == 0:
        return math.nan, math.nan, 0
    low, high = np.quantile(estimates, [0.025, 0.975])
    return float(low), float(high), int(estimates.size)


def transform_values(values: pd.Series, transform: str) -> np.ndarray:
    result = pd.to_numeric(values, errors="coerce").to_numpy(float)
    if transform == "identity":
        return result
    if transform == "log":
        if np.any(result <= 0):
            raise ValueError("Log-transformed predictor/outcome contains nonpositive data")
        return np.log(result)
    if transform == "log1p":
        if np.any(result < 0):
            raise ValueError("log1p-transformed outcome contains negative data")
        return np.log1p(result)
    raise ValueError(f"Unknown transform: {transform}")


def fit_ols(
    data: pd.DataFrame,
    *,
    model_id: str,
    analysis_id: str,
    family: str,
    sensitivity_id: str,
    species: str,
    outcome: str,
    outcome_transform: str,
    year_column: str,
    predictors: tuple[PredictorSpec, ...],
) -> OLSBundle:
    required = [outcome, year_column] + [item.source for item in predictors]
    complete = data.dropna(subset=required).copy().sort_values(year_column)
    if len(complete) <= len(predictors) + 2:
        raise ValueError(f"Too few complete cases for {model_id}")
    y = transform_values(complete[outcome], outcome_transform)
    design_data: dict[str, np.ndarray] = {}
    predictor_summary: dict[str, tuple[float, float]] = {}
    for predictor in predictors:
        raw = transform_values(complete[predictor.source], predictor.transform)
        mean = float(raw.mean())
        standard_deviation = float(raw.std(ddof=1))
        if not math.isfinite(standard_deviation) or standard_deviation <= 0:
            raise ValueError(f"Constant/nonfinite predictor {predictor.source} in {model_id}")
        design_data[predictor.term] = (raw - mean) / standard_deviation
        predictor_summary[predictor.term] = (mean, standard_deviation)
    design = sm.add_constant(pd.DataFrame(design_data), has_constant="add")
    ordinary = sm.OLS(y, design).fit()
    robust = ordinary.get_robustcov_results(cov_type="HC3", use_t=True)
    confidence = np.asarray(robust.conf_int(alpha=ALPHA))
    term_names = list(design.columns)
    coefficient_rows: list[dict[str, object]] = []
    for index, term in enumerate(term_names):
        predictor_mean, predictor_sd = predictor_summary.get(term, (math.nan, math.nan))
        beta = float(robust.params[index])
        coefficient_rows.append(
            {
                "model_id": model_id,
                "analysis_id": analysis_id,
                "family": family,
                "sensitivity_id": sensitivity_id,
                "species": species,
                "outcome": outcome,
                "outcome_scale": outcome_transform,
                "n": len(complete),
                "term": term,
                "coefficient": beta,
                "hc3_standard_error": float(robust.bse[index]),
                "hc3_ci_low": float(confidence[index, 0]),
                "hc3_ci_high": float(confidence[index, 1]),
                "hc3_p_value": float(robust.pvalues[index]),
                "predictor_transformed_mean": predictor_mean,
                "predictor_transformed_sample_sd": predictor_sd,
                "fitted_percent_count_difference_per_1sd": (
                    float(100.0 * np.expm1(beta))
                    if outcome_transform == "log1p" and term != "const"
                    else math.nan
                ),
            }
        )

    influence = ordinary.get_influence()
    cooks = np.asarray(influence.cooks_distance[0], dtype=float)
    leverage = np.asarray(influence.hat_matrix_diag, dtype=float)
    studentized = np.asarray(influence.resid_studentized_external, dtype=float)
    diagnostic_rows: list[dict[str, object]] = []
    for position, (_, row) in enumerate(complete.iterrows()):
        diagnostic_rows.append(
            {
                "model_id": model_id,
                "analysis_id": analysis_id,
                "family": family,
                "sensitivity_id": sensitivity_id,
                "species": species,
                "year": int(row[year_column]),
                "observed_model_scale": float(y[position]),
                "fitted_model_scale": float(ordinary.fittedvalues.iloc[position]),
                "residual_model_scale": float(ordinary.resid.iloc[position]),
                "externally_studentized_residual": float(studentized[position]),
                "leverage": float(leverage[position]),
                "cooks_distance": float(cooks[position]),
                "cooks_threshold_4_over_n": float(4.0 / len(complete)),
                "cooks_flag": bool(cooks[position] > 4.0 / len(complete)),
            }
        )
    maximum_position = int(np.argmax(cooks))
    summary = {
        "model_id": model_id,
        "analysis_id": analysis_id,
        "family": family,
        "sensitivity_id": sensitivity_id,
        "species": species,
        "outcome": outcome,
        "outcome_scale": outcome_transform,
        "n": len(complete),
        "parameters_including_intercept": len(term_names),
        "adjusted_r_squared": float(ordinary.rsquared_adj),
        "maximum_cooks_distance": float(cooks[maximum_position]),
        "maximum_cooks_year": int(complete.iloc[maximum_position][year_column]),
        "cooks_threshold_4_over_n": float(4.0 / len(complete)),
        "cooks_flag_count": int(np.count_nonzero(cooks > 4.0 / len(complete))),
    }
    return OLSBundle(
        model_id=model_id,
        analysis_id=analysis_id,
        family=family,
        sensitivity_id=sensitivity_id,
        species=species,
        outcome=outcome,
        outcome_scale=outcome_transform,
        data=complete,
        year_column=year_column,
        predictors=predictors,
        coefficient_rows=coefficient_rows,
        diagnostic_rows=diagnostic_rows,
        summary=summary,
    )


def observed_direction(value: float) -> str:
    if value > 0:
        return "positive"
    if value < 0:
        return "negative"
    return "zero"


def run_association(
    data: pd.DataFrame,
    *,
    analysis_id: str,
    family: str,
    sensitivity_id: str,
    species: str,
    label: str,
    expected_direction: str,
    predictor: str,
    outcome: str,
    year_column: str,
    predictor_label: str,
    outcome_label: str,
    ols_outcome_transform: str,
    ols_predictors: tuple[PredictorSpec, ...],
    permutation_seed: int,
    bootstrap_seed: int,
) -> tuple[dict[str, object], OLSBundle]:
    required = [predictor, outcome, year_column]
    complete = data.dropna(subset=required).copy().sort_values(year_column)
    x = pd.to_numeric(complete[predictor]).to_numpy(float)
    y = pd.to_numeric(complete[outcome]).to_numpy(float)
    rho = midrank_correlation(x, y)
    p_value, extreme = permutation_spearman(
        x, y, PERMUTATION_REPETITIONS, permutation_seed
    )
    ci_low, ci_high, finite = bootstrap_spearman_interval(
        x, y, BOOTSTRAP_REPETITIONS, bootstrap_seed
    )
    model_id = f"{analysis_id}_{sensitivity_id}"
    ols = fit_ols(
        complete,
        model_id=model_id,
        analysis_id=analysis_id,
        family=family,
        sensitivity_id=sensitivity_id,
        species=species,
        outcome=outcome,
        outcome_transform=ols_outcome_transform,
        year_column=year_column,
        predictors=ols_predictors,
    )
    main_term = ols_predictors[0].term
    main_coefficient = next(
        row for row in ols.coefficient_rows if row["term"] == main_term
    )
    direction = observed_direction(rho)
    result = {
        "family": family,
        "analysis_id": analysis_id,
        "sensitivity_id": sensitivity_id,
        "analysis_label": label,
        "species": species,
        "predictor": predictor_label,
        "outcome": outcome_label,
        "n": len(complete),
        "expected_direction": expected_direction,
        "observed_direction": direction,
        "direction_matches_expected": direction == expected_direction,
        "spearman_rho": rho,
        "bootstrap_ci_low": ci_low,
        "bootstrap_ci_high": ci_high,
        "bootstrap_repetitions": BOOTSTRAP_REPETITIONS,
        "bootstrap_finite_estimates": finite,
        "bootstrap_seed": bootstrap_seed,
        "permutation_p_raw": p_value,
        "permutation_extreme_count": extreme,
        "permutation_repetitions": PERMUTATION_REPETITIONS,
        "permutation_seed": permutation_seed,
        "p_adjustment_family": "none_descriptive",
        "permutation_p_holm": math.nan,
        "passes_family_alpha_0_05": False,
        "ols_model_id": model_id,
        "ols_main_term": main_term,
        "ols_beta": main_coefficient["coefficient"],
        "ols_hc3_ci_low": main_coefficient["hc3_ci_low"],
        "ols_hc3_ci_high": main_coefficient["hc3_ci_high"],
        "ols_hc3_p_value": main_coefficient["hc3_p_value"],
        "ols_fitted_percent_count_difference_per_1sd": main_coefficient[
            "fitted_percent_count_difference_per_1sd"
        ],
        "maximum_cooks_year": ols.summary["maximum_cooks_year"],
        "maximum_cooks_distance": ols.summary["maximum_cooks_distance"],
        "t2_extrapolation_flagged_rows": (
            int((complete["t2_extrapolation_days"] > 0).sum())
            if "t2_extrapolation_days" in complete
            else 0
        ),
        "t2_extrapolation_days_total": (
            int(complete["t2_extrapolation_days"].sum())
            if "t2_extrapolation_days" in complete
            else 0
        ),
    }
    return result, ols


def holm_adjust(rows: list[dict[str, object]], family_name: str) -> None:
    p_values = np.asarray([row["permutation_p_raw"] for row in rows], dtype=float)
    order = np.argsort(p_values, kind="stable")
    sorted_p = p_values[order]
    adjusted_sorted = np.maximum.accumulate(
        np.asarray([(len(rows) - index) * value for index, value in enumerate(sorted_p)])
    )
    adjusted = np.empty(len(rows), dtype=float)
    adjusted[order] = np.minimum(adjusted_sorted, 1.0)
    for row, value in zip(rows, adjusted):
        row["p_adjustment_family"] = family_name
        row["permutation_p_holm"] = float(value)
        row["passes_family_alpha_0_05"] = bool(value < ALPHA)


def influence_refit_rows(bundle: OLSBundle) -> list[dict[str, object]]:
    excluded_year = int(bundle.summary["maximum_cooks_year"])
    reduced = bundle.data.loc[bundle.data[bundle.year_column] != excluded_year].copy()
    refit = fit_ols(
        reduced,
        model_id=f"{bundle.model_id}_highest_cook_removed",
        analysis_id=bundle.analysis_id,
        family="influence_sensitivity",
        sensitivity_id=f"{bundle.sensitivity_id}_highest_cook_removed",
        species=bundle.species,
        outcome=bundle.outcome,
        outcome_transform=bundle.outcome_scale,
        year_column=bundle.year_column,
        predictors=bundle.predictors,
    )
    full_by_term = {row["term"]: row for row in bundle.coefficient_rows}
    rows: list[dict[str, object]] = []
    for row in refit.coefficient_rows:
        if row["term"] == "const":
            continue
        full = full_by_term[row["term"]]
        rows.append(
            {
                "model_id": bundle.model_id,
                "analysis_id": bundle.analysis_id,
                "family": bundle.family,
                "sensitivity_id": bundle.sensitivity_id,
                "species": bundle.species,
                "term": row["term"],
                "n_full": bundle.summary["n"],
                "n_refit": refit.summary["n"],
                "excluded_year": excluded_year,
                "excluded_cooks_distance": bundle.summary["maximum_cooks_distance"],
                "full_coefficient": full["coefficient"],
                "full_hc3_ci_low": full["hc3_ci_low"],
                "full_hc3_ci_high": full["hc3_ci_high"],
                "refit_coefficient": row["coefficient"],
                "refit_hc3_ci_low": row["hc3_ci_low"],
                "refit_hc3_ci_high": row["hc3_ci_high"],
                "sign_changed": bool(
                    np.sign(float(full["coefficient"]))
                    != np.sign(float(row["coefficient"]))
                ),
            }
        )
    return rows


def leave_one_year_out(
    analysis_id: str, data: pd.DataFrame, primary_rho: float
) -> tuple[list[dict[str, object]], dict[str, object]]:
    ordered = data.sort_values("primary_return_year")
    rows: list[dict[str, object]] = []
    for _, omitted in ordered.iterrows():
        reduced = ordered.loc[
            ordered["primary_return_year"] != omitted["primary_return_year"]
        ]
        rho = midrank_correlation(
            reduced["primary_thermal_value_c"].to_numpy(float),
            reduced["total_adults"].to_numpy(float),
        )
        rows.append(
            {
                "analysis_id": analysis_id,
                "species": ANALYSIS_SPECS[analysis_id]["species"],
                "removed_return_year": int(omitted["primary_return_year"]),
                "n": len(reduced),
                "rho_primary_full": primary_rho,
                "rho_leave_one_year_out": rho,
                "sign_changed_from_primary": bool(
                    np.sign(rho) != np.sign(primary_rho)
                ),
            }
        )
    rhos = np.asarray([row["rho_leave_one_year_out"] for row in rows], dtype=float)
    summary = {
        "analysis_id": analysis_id,
        "species": ANALYSIS_SPECS[analysis_id]["species"],
        "n_full": len(ordered),
        "rho_primary_full": primary_rho,
        "rho_leave_one_year_out_min": float(rhos.min()),
        "rho_leave_one_year_out_max": float(rhos.max()),
        "sign_change_count": int(
            sum(bool(row["sign_changed_from_primary"]) for row in rows)
        ),
    }
    return rows, summary


def lag1_correlation(values: np.ndarray) -> float:
    values = np.asarray(values, dtype=float)
    return float(np.corrcoef(values[1:], values[:-1])[0, 1])


def temporal_sensitivity(
    analysis_id: str, data: pd.DataFrame, primary_rho: float
) -> dict[str, object]:
    ordered = data.sort_values("primary_return_year")
    years = ordered["primary_return_year"].to_numpy(float)
    rank_temp = stats.rankdata(
        ordered["primary_thermal_value_c"].to_numpy(float), method="average"
    )
    rank_return = stats.rankdata(
        ordered["total_adults"].to_numpy(float), method="average"
    )
    centered_year = years - years.mean()
    trend_design = np.column_stack([np.ones(len(years)), centered_year])
    temp_residual = rank_temp - trend_design @ np.linalg.lstsq(
        trend_design, rank_temp, rcond=None
    )[0]
    return_residual = rank_return - trend_design @ np.linalg.lstsq(
        trend_design, rank_return, rcond=None
    )[0]
    rho_detrended = float(np.corrcoef(temp_residual, return_residual)[0, 1])
    temp_residual_lag1 = lag1_correlation(temp_residual)
    return_residual_lag1 = lag1_correlation(return_residual)
    trigger = (
        abs(temp_residual_lag1) >= TEMPORAL_LAG1_TRIGGER
        or abs(return_residual_lag1) >= TEMPORAL_LAG1_TRIGGER
    )
    circular_p = math.nan
    circular_extreme = math.nan
    if trigger:
        shifted = np.asarray(
            [
                np.corrcoef(temp_residual, np.roll(return_residual, shift))[0, 1]
                for shift in range(len(years))
            ],
            dtype=float,
        )
        circular_extreme = int(np.count_nonzero(np.abs(shifted) >= abs(rho_detrended)))
        circular_p = float(circular_extreme / len(years))
        circular_status = "triggered_abs_residual_lag1_ge_0_30"
    else:
        circular_status = "not_triggered_below_abs_lag1_0_30"
    if np.sign(primary_rho) == np.sign(rho_detrended):
        direction_status = "retained"
    else:
        direction_status = "reversed"
    magnitude_change = (
        float(100.0 * (abs(rho_detrended) - abs(primary_rho)) / abs(primary_rho))
        if primary_rho != 0
        else math.nan
    )
    result = {
        "analysis_id": analysis_id,
        "species": ANALYSIS_SPECS[analysis_id]["species"],
        "n": len(ordered),
        "first_return_year": int(years.min()),
        "last_return_year": int(years.max()),
        "predictor_raw_lag1_rank_autocorrelation": lag1_correlation(rank_temp),
        "outcome_raw_lag1_rank_autocorrelation": lag1_correlation(rank_return),
        "predictor_residual_lag1_autocorrelation": temp_residual_lag1,
        "outcome_residual_lag1_autocorrelation": return_residual_lag1,
        "rho_primary": primary_rho,
        "rho_detrended": rho_detrended,
        "direction_status": direction_status,
        "magnitude_change_pct": magnitude_change,
        "circular_shift_trigger_abs_lag1": TEMPORAL_LAG1_TRIGGER,
        "circular_shift_status": circular_status,
        "circular_shift_offsets": len(years) if trigger else 0,
        "circular_shift_extreme_count": circular_extreme,
        "circular_shift_exact_two_sided_p": circular_p,
        "interpretation_status": "temporal_trend_sensitivity_only",
    }
    missing_contract = set(TEMPORAL_REQUIRED_FIELDS) - set(result)
    if missing_contract:
        raise AssertionError(f"D-022 output contract lost fields: {missing_contract}")
    return result


def a8_vif_rows(bundle: OLSBundle) -> list[dict[str, object]]:
    design_values: dict[str, np.ndarray] = {}
    for predictor in bundle.predictors:
        raw = transform_values(bundle.data[predictor.source], predictor.transform)
        design_values[predictor.term] = (raw - raw.mean()) / raw.std(ddof=1)
    design = sm.add_constant(pd.DataFrame(design_values), has_constant="add")
    return [
        {
            "model_id": bundle.model_id,
            "analysis_id": bundle.analysis_id,
            "species": bundle.species,
            "term": term,
            "variance_inflation_factor": float(
                variance_inflation_factor(design.to_numpy(float), index)
            ),
        }
        for index, term in enumerate(design.columns)
        if term != "const"
    ]


def plot_a8_diagnostics(bundles: list[OLSBundle], output_path: Path) -> None:
    fig, axes = plt.subplots(len(bundles), 3, figsize=(14, 7.5), squeeze=False)
    colors = {"Chinook": "#c44e52", "Coho": "#4c72b0"}
    for row_index, bundle in enumerate(bundles):
        diagnostics = pd.DataFrame(bundle.diagnostic_rows).sort_values("year")
        color = colors[bundle.species]
        axis = axes[row_index, 0]
        axis.scatter(
            diagnostics["fitted_model_scale"],
            diagnostics["residual_model_scale"],
            color=color,
            alpha=0.85,
        )
        axis.axhline(0, color="#555555", linewidth=1)
        axis.set_xlabel("Fitted log1p(adults)")
        axis.set_ylabel("Residual")
        axis.set_title(f"{bundle.species}: residual vs fitted")

        axis = axes[row_index, 1]
        stats.probplot(
            diagnostics["residual_model_scale"].to_numpy(float),
            dist="norm",
            plot=axis,
        )
        axis.get_lines()[0].set_markerfacecolor(color)
        axis.get_lines()[0].set_markeredgecolor(color)
        axis.set_title(f"{bundle.species}: normal Q-Q")

        axis = axes[row_index, 2]
        marker_line, stem_lines, baseline = axis.stem(
            diagnostics["year"],
            diagnostics["cooks_distance"],
            linefmt="-",
            markerfmt="o",
            basefmt="-",
        )
        plt.setp(marker_line, color=color, markerfacecolor=color)
        plt.setp(stem_lines, color=color)
        plt.setp(baseline, color="#777777")
        axis.axhline(
            diagnostics["cooks_threshold_4_over_n"].iloc[0],
            color="#222222",
            linestyle="--",
            linewidth=1,
            label="4/n",
        )
        axis.set_xlabel("Return year")
        axis.set_ylabel("Cook's distance")
        axis.set_title(f"{bundle.species}: influence")
        axis.legend(frameon=False)
    fig.suptitle("Phase 7 A8 temperature + flow model diagnostics", fontsize=14)
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    fig.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def fmt(value: object, digits: int = 3) -> str:
    if value is None:
        return "NA"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if not math.isfinite(number):
        return "NA"
    return f"{number:.{digits}f}"


def markdown_table(headers: list[str], rows: list[list[object]]) -> list[str]:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    lines.extend("| " + " | ".join(map(str, row)) + " |" for row in rows)
    return lines


def classify_primary_results(
    primary: list[dict[str, object]], sensitivities: list[dict[str, object]]
) -> None:
    sensitivity_lookup = {
        (row["analysis_id"], row["sensitivity_id"]): row for row in sensitivities
    }
    for row in primary:
        t1 = sensitivity_lookup[(row["analysis_id"], "t1_replacement")]
        influence = sensitivity_lookup[(row["analysis_id"], "highest_cook_removed")]
        supported = (
            bool(row["direction_matches_expected"])
            and bool(row["passes_family_alpha_0_05"])
            and np.sign(float(t1["spearman_rho"]))
            == np.sign(float(row["spearman_rho"]))
            and np.sign(float(influence["spearman_rho"]))
            == np.sign(float(row["spearman_rho"]))
        )
        row["protocol_support_classification"] = (
            "supported_by_observational_analysis"
            if supported
            else "not_supported_by_these_data"
        )


def build_report(
    input_hashes: dict[str, str],
    checks: list[dict[str, object]],
    primary: list[dict[str, object]],
    mechanisms: list[dict[str, object]],
    sensitivities: list[dict[str, object]],
    loo_summary: list[dict[str, object]],
    temporal: list[dict[str, object]],
    a8_summaries: list[dict[str, object]],
    a8_coefficients: list[dict[str, object]],
    a8_vifs: list[dict[str, object]],
) -> str:
    lines = [
        "# Phase 7 frozen hypothesis-analysis results",
        "",
        f"Run date: {ANALYSIS_DATE}",
        "",
        f"Frozen protocol: version {PROTOCOL_VERSION}; SHA-256 `{EXPECTED_PROTOCOL_SHA256}`.",
        "",
        "Status: deterministic observational analysis of modeled temperature proxies. "
        "These results are not causal effects, observed continuous water temperatures, "
        "or regulatory 7DADMax estimates.",
        "",
        "## Input validation",
        "",
        f"All {len(checks)} validation checks passed before any association was calculated. "
        "The exact frozen input hashes are recorded in `phase7_output_manifest.json` and "
        "`phase7_input_validation.json`.",
        "",
        "## Primary family: A1, A3, A5",
        "",
    ]
    primary_rows: list[list[object]] = []
    for row in primary:
        primary_rows.append(
            [
                row["analysis_id"],
                row["species"],
                row["n"],
                fmt(row["spearman_rho"]),
                f"{fmt(row['bootstrap_ci_low'])}, {fmt(row['bootstrap_ci_high'])}",
                fmt(row["permutation_p_raw"], 5),
                fmt(row["permutation_p_holm"], 5),
                fmt(row["ols_beta"]),
                fmt(row["ols_fitted_percent_count_difference_per_1sd"], 1),
                row["protocol_support_classification"],
            ]
        )
    lines.extend(
        markdown_table(
            [
                "ID",
                "Species",
                "n",
                "rho",
                "95% bootstrap CI",
                "raw p",
                "Holm p",
                "OLS beta",
                "%/1 SD",
                "Protocol classification",
            ],
            primary_rows,
        )
    )
    lines.extend(
        [
            "",
            "The rank tests use 100,000 unrestricted outcome permutations. Holm correction "
            "is confined to A1/A3/A5. The OLS coefficient is for standardized T2 window "
            "temperature in `log1p(total_adults)` models with HC3 intervals.",
            "",
            "## Mechanism family: A6, A7",
            "",
        ]
    )
    lines.extend(
        markdown_table(
            ["ID", "Relationship", "n", "Expected", "rho", "95% CI", "raw p", "Holm p"],
            [
                [
                    row["analysis_id"],
                    row["analysis_label"],
                    row["n"],
                    row["expected_direction"],
                    fmt(row["spearman_rho"]),
                    f"{fmt(row['bootstrap_ci_low'])}, {fmt(row['bootstrap_ci_high'])}",
                    fmt(row["permutation_p_raw"], 5),
                    fmt(row["permutation_p_holm"], 5),
                ]
                for row in mechanisms
            ],
        )
    )
    lines.extend(["", "## Frozen sensitivity analyses", ""])
    lines.extend(
        markdown_table(
            ["ID", "Sensitivity", "n", "rho", "unadjusted p", "max Cook year"],
            [
                [
                    row["analysis_id"],
                    row["sensitivity_id"],
                    row["n"],
                    fmt(row["spearman_rho"]),
                    fmt(row["permutation_p_raw"], 5),
                    row["maximum_cooks_year"],
                ]
                for row in sensitivities
            ],
        )
    )
    lines.extend(
        [
            "",
            "All sensitivity p-values are descriptive and unadjusted. Full coefficients, "
            "HC3 intervals, Cook diagnostics, and the one-time highest-Cook OLS refits are "
            "provided in machine-readable tables.",
            "",
            "### Leave-one-year-out rho",
            "",
        ]
    )
    lines.extend(
        markdown_table(
            ["ID", "Full rho", "LOYO min", "LOYO max", "sign changes"],
            [
                [
                    row["analysis_id"],
                    fmt(row["rho_primary_full"]),
                    fmt(row["rho_leave_one_year_out_min"]),
                    fmt(row["rho_leave_one_year_out_max"]),
                    row["sign_change_count"],
                ]
                for row in loo_summary
            ],
        )
    )
    lines.extend(["", "### Temporal-trend sensitivity (D-022)", ""])
    lines.extend(
        markdown_table(
            [
                "ID",
                "temp raw lag1",
                "return raw lag1",
                "temp resid lag1",
                "return resid lag1",
                "primary rho",
                "detrended rho",
                "direction",
                "magnitude change %",
                "circular shift",
                "shift p",
            ],
            [
                [
                    row["analysis_id"],
                    fmt(row["predictor_raw_lag1_rank_autocorrelation"]),
                    fmt(row["outcome_raw_lag1_rank_autocorrelation"]),
                    fmt(row["predictor_residual_lag1_autocorrelation"]),
                    fmt(row["outcome_residual_lag1_autocorrelation"]),
                    fmt(row["rho_primary"]),
                    fmt(row["rho_detrended"]),
                    row["direction_status"],
                    fmt(row["magnitude_change_pct"], 1),
                    row["circular_shift_status"],
                    fmt(row["circular_shift_exact_two_sided_p"], 5),
                ]
                for row in temporal
            ],
        )
    )
    lines.extend(
        [
            "",
            "This is strictly a temporal-trend sensitivity. It is not a fitted time-series "
            "model and does not prove that all cohort or multi-year dependence was removed.",
            "",
            "## A8 secondary temperature + flow models",
            "",
        ]
    )
    coefficient_lookup: dict[tuple[str, str], dict[str, object]] = {
        (row["species"], row["term"]): row for row in a8_coefficients if row["term"] != "const"
    }
    vif_lookup = {(row["species"], row["term"]): row for row in a8_vifs}
    a8_rows: list[list[object]] = []
    for summary in a8_summaries:
        for term in ("z_t2_window_mean_c", "z_log_matched_flow_cfs"):
            coefficient = coefficient_lookup[(summary["species"], term)]
            vif = vif_lookup[(summary["species"], term)]
            a8_rows.append(
                [
                    summary["species"],
                    term,
                    fmt(coefficient["coefficient"]),
                    f"{fmt(coefficient['hc3_ci_low'])}, {fmt(coefficient['hc3_ci_high'])}",
                    fmt(coefficient["hc3_p_value"], 5),
                    fmt(vif["variance_inflation_factor"]),
                    fmt(summary["adjusted_r_squared"]),
                ]
            )
    lines.extend(
        markdown_table(
            ["Species", "Term", "beta", "HC3 95% CI", "HC3 p", "VIF", "adjusted R2"],
            a8_rows,
        )
    )
    lines.extend(
        [
            "",
            "A8 is secondary and descriptive and cannot overturn A1 or A3. See "
            "`phase7_a8_diagnostics.png` for residual, Q-Q, and Cook plots.",
            "",
            "## Output interpretation boundary",
            "",
            "T2 is an air-temperature-plus-seasonal proxy calibrated to grab samples; T1 "
            "adds flow and is used only as model-form sensitivity. Extrapolation exclusions "
            "are sensitivity analyses. Threshold counts and all other nonmean thermal "
            "metrics remain exploratory only and were not tested here.",
            "",
        ]
    )
    return "\n".join(lines)


def write_csv(frame: pd.DataFrame, path: Path) -> None:
    frame.to_csv(path, index=False, lineterminator="\n", float_format="%.10g")


def publish_package(staging: Path) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest_name = "phase7_output_manifest.json"
    staged_files = sorted(
        (path for path in staging.iterdir() if path.name != manifest_name),
        key=lambda path: path.name,
    )
    for staged in staged_files:
        os.replace(staged, OUTPUT_DIR / staged.name)
    # The manifest is the completion marker and is therefore published last.
    os.replace(staging / manifest_name, OUTPUT_DIR / manifest_name)


def main() -> None:
    # Stage 1: load and validate only. No association is calculated before this returns.
    master, exposure, environment, gate = load_inputs()
    checks, joined = validate_inputs(master, exposure, environment, gate)
    input_hashes = {
        relative(path): sha256_file(path)
        for path in (
            MASTER_PATH,
            EXPOSURE_PATH,
            ENVIRONMENT_PATH,
            PROTOCOL_PATH,
            PREASSOCIATION_GATE_PATH,
        )
    }

    regression_bundles: list[OLSBundle] = []

    # Stage 2: frozen primary family in A1, A3, A5 order.
    primary_results: list[dict[str, object]] = []
    primary_bundle_by_id: dict[str, OLSBundle] = {}
    for analysis_id in ("A1", "A3", "A5"):
        spec = ANALYSIS_SPECS[analysis_id]
        result, bundle = run_association(
            joined[analysis_id],
            analysis_id=analysis_id,
            family="primary_salmon_temperature",
            sensitivity_id="t2_primary",
            species=str(spec["species"]),
            label=str(spec["label"]),
            expected_direction=str(spec["expected_direction"]),
            predictor="primary_thermal_value_c",
            outcome="total_adults",
            year_column="primary_return_year",
            predictor_label="T2 biological-window mean proxy (C)",
            outcome_label="total_adults",
            ols_outcome_transform="log1p",
            ols_predictors=(
                PredictorSpec("z_t2_window_mean_c", "primary_thermal_value_c"),
            ),
            permutation_seed=BASE_SEED + int(analysis_id[1:]),
            bootstrap_seed=BASE_SEED + 100 + int(analysis_id[1:]),
        )
        primary_results.append(result)
        primary_bundle_by_id[analysis_id] = bundle
        regression_bundles.append(bundle)
    holm_adjust(primary_results, "primary_A1_A3_A5_holm")

    # Stage 3: frozen physical mechanism family in A6, A7 order.
    mechanism_results: list[dict[str, object]] = []
    a6_data = environment.loc[environment["return_year"].between(1997, 2025)].copy()
    a6_result, a6_bundle = run_association(
        a6_data,
        analysis_id="A6",
        family="mechanism",
        sensitivity_id="frozen_primary",
        species="not_applicable",
        label="April 1 SWE -> Jul-Sep mean flow",
        expected_direction="positive",
        predictor="swe_apr01_inches",
        outcome="flow_jul_sep_mean_cfs",
        year_column="return_year",
        predictor_label="April 1 SWE (inches)",
        outcome_label="Jul-Sep mean flow (cfs)",
        ols_outcome_transform="log",
        ols_predictors=(PredictorSpec("z_swe_apr01_inches", "swe_apr01_inches"),),
        permutation_seed=BASE_SEED + 6,
        bootstrap_seed=BASE_SEED + 106,
    )
    mechanism_results.append(a6_result)
    regression_bundles.append(a6_bundle)
    a7_data = exposure.loc[exposure["analysis_id"] == "A5"].copy()
    a7_result, a7_bundle = run_association(
        a7_data,
        analysis_id="A7",
        family="mechanism",
        sensitivity_id="frozen_primary",
        species="not_applicable",
        label="Matched Jun-Sep flow -> T2 Jun-Sep temperature",
        expected_direction="negative",
        predictor="matched_window_mean_usgs_flow_cfs",
        outcome="primary_thermal_value_c",
        year_column="exposure_year",
        predictor_label="matched Jun-Sep mean flow (cfs)",
        outcome_label="T2 Jun-Sep mean proxy (C)",
        ols_outcome_transform="identity",
        ols_predictors=(
            PredictorSpec(
                "z_log_matched_flow_cfs", "matched_window_mean_usgs_flow_cfs", "log"
            ),
        ),
        permutation_seed=BASE_SEED + 7,
        bootstrap_seed=BASE_SEED + 107,
    )
    mechanism_results.append(a7_result)
    regression_bundles.append(a7_bundle)
    holm_adjust(mechanism_results, "mechanism_A6_A7_holm")

    # Stage 4: all frozen sensitivity analyses, in protocol/user-request order.
    sensitivity_results: list[dict[str, object]] = []
    for analysis_id in ("A2", "A4"):
        spec = ANALYSIS_SPECS[analysis_id]
        result, bundle = run_association(
            joined[analysis_id],
            analysis_id=analysis_id,
            family="window_sensitivity",
            sensitivity_id="window_alternative",
            species=str(spec["species"]),
            label=str(spec["label"]),
            expected_direction=str(spec["expected_direction"]),
            predictor="primary_thermal_value_c",
            outcome="total_adults",
            year_column="primary_return_year",
            predictor_label="T2 alternative-window mean proxy (C)",
            outcome_label="total_adults",
            ols_outcome_transform="log1p",
            ols_predictors=(
                PredictorSpec("z_t2_window_mean_c", "primary_thermal_value_c"),
            ),
            permutation_seed=BASE_SEED + int(analysis_id[1:]),
            bootstrap_seed=BASE_SEED + 100 + int(analysis_id[1:]),
        )
        sensitivity_results.append(result)
        regression_bundles.append(bundle)

    for analysis_id in ("A1", "A3", "A5"):
        spec = ANALYSIS_SPECS[analysis_id]
        result, bundle = run_association(
            joined[analysis_id],
            analysis_id=analysis_id,
            family="model_form_sensitivity",
            sensitivity_id="t1_replacement",
            species=str(spec["species"]),
            label=f"{spec['label']} (T1 replacement)",
            expected_direction=str(spec["expected_direction"]),
            predictor="sensitivity_thermal_value_c",
            outcome="total_adults",
            year_column="primary_return_year",
            predictor_label="T1 biological-window mean proxy (C)",
            outcome_label="total_adults",
            ols_outcome_transform="log1p",
            ols_predictors=(
                PredictorSpec("z_t1_window_mean_c", "sensitivity_thermal_value_c"),
            ),
            permutation_seed=BASE_SEED + int(analysis_id[1:]),
            bootstrap_seed=BASE_SEED + 100 + int(analysis_id[1:]),
        )
        sensitivity_results.append(result)
        regression_bundles.append(bundle)

    for analysis_id in ("A1", "A3", "A5"):
        spec = ANALYSIS_SPECS[analysis_id]
        result, bundle = run_association(
            joined[analysis_id],
            analysis_id=analysis_id,
            family="outcome_sensitivity",
            sensitivity_id="adults_plus_jacks",
            species=str(spec["species"]),
            label=f"{spec['label']} (adults + jacks)",
            expected_direction=str(spec["expected_direction"]),
            predictor="primary_thermal_value_c",
            outcome="adult_plus_jacks",
            year_column="primary_return_year",
            predictor_label="T2 biological-window mean proxy (C)",
            outcome_label="adult_plus_jacks",
            ols_outcome_transform="log1p",
            ols_predictors=(
                PredictorSpec("z_t2_window_mean_c", "primary_thermal_value_c"),
            ),
            permutation_seed=BASE_SEED + int(analysis_id[1:]),
            bootstrap_seed=BASE_SEED + 100 + int(analysis_id[1:]),
        )
        sensitivity_results.append(result)
        regression_bundles.append(bundle)

    for analysis_id in ("A1", "A3", "A5"):
        spec = ANALYSIS_SPECS[analysis_id]
        unflagged = joined[analysis_id].loc[
            joined[analysis_id]["t2_extrapolation_days"] == 0
        ]
        result, bundle = run_association(
            unflagged,
            analysis_id=analysis_id,
            family="extrapolation_sensitivity",
            sensitivity_id="no_t2_extrapolation_rows",
            species=str(spec["species"]),
            label=f"{spec['label']} (T2 unflagged rows only)",
            expected_direction=str(spec["expected_direction"]),
            predictor="primary_thermal_value_c",
            outcome="total_adults",
            year_column="primary_return_year",
            predictor_label="T2 biological-window mean proxy (C)",
            outcome_label="total_adults",
            ols_outcome_transform="log1p",
            ols_predictors=(
                PredictorSpec("z_t2_window_mean_c", "primary_thermal_value_c"),
            ),
            permutation_seed=BASE_SEED + int(analysis_id[1:]),
            bootstrap_seed=BASE_SEED + 100 + int(analysis_id[1:]),
        )
        sensitivity_results.append(result)
        regression_bundles.append(bundle)

    for analysis_id in ("A1", "A3", "A5"):
        spec = ANALYSIS_SPECS[analysis_id]
        excluded_year = int(primary_bundle_by_id[analysis_id].summary["maximum_cooks_year"])
        reduced = joined[analysis_id].loc[
            joined[analysis_id]["primary_return_year"] != excluded_year
        ]
        result, bundle = run_association(
            reduced,
            analysis_id=analysis_id,
            family="influence_sensitivity",
            sensitivity_id="highest_cook_removed",
            species=str(spec["species"]),
            label=f"{spec['label']} (highest-Cook year {excluded_year} removed)",
            expected_direction=str(spec["expected_direction"]),
            predictor="primary_thermal_value_c",
            outcome="total_adults",
            year_column="primary_return_year",
            predictor_label="T2 biological-window mean proxy (C)",
            outcome_label="total_adults",
            ols_outcome_transform="log1p",
            ols_predictors=(
                PredictorSpec("z_t2_window_mean_c", "primary_thermal_value_c"),
            ),
            permutation_seed=BASE_SEED + int(analysis_id[1:]),
            bootstrap_seed=BASE_SEED + 100 + int(analysis_id[1:]),
        )
        result["excluded_primary_highest_cooks_year"] = excluded_year
        sensitivity_results.append(result)
        # This is already the required one-time refit and is not recursively refit.
        regression_bundles.append(bundle)

    primary_by_id = {row["analysis_id"]: row for row in primary_results}
    loo_rows: list[dict[str, object]] = []
    loo_summary: list[dict[str, object]] = []
    temporal_rows: list[dict[str, object]] = []
    for analysis_id in ("A1", "A3", "A5"):
        detail, summary = leave_one_year_out(
            analysis_id,
            joined[analysis_id],
            float(primary_by_id[analysis_id]["spearman_rho"]),
        )
        loo_rows.extend(detail)
        loo_summary.append(summary)
        temporal_rows.append(
            temporal_sensitivity(
                analysis_id,
                joined[analysis_id],
                float(primary_by_id[analysis_id]["spearman_rho"]),
            )
        )

    # Influence refits apply once to every OLS specified up through this stage.
    influence_rows: list[dict[str, object]] = []
    for bundle in regression_bundles:
        if bundle.sensitivity_id != "highest_cook_removed":
            influence_rows.extend(influence_refit_rows(bundle))

    # Stage 5: A8, separately for Chinook (A1 rows) and Coho (A3 rows).
    a8_bundles: list[OLSBundle] = []
    a8_vifs: list[dict[str, object]] = []
    for analysis_id in ("A1", "A3"):
        species = str(ANALYSIS_SPECS[analysis_id]["species"])
        bundle = fit_ols(
            joined[analysis_id],
            model_id=f"A8_{species.lower()}_temperature_plus_flow",
            analysis_id="A8",
            family="secondary_combined_model",
            sensitivity_id=f"{analysis_id.lower()}_rows",
            species=species,
            outcome="total_adults",
            outcome_transform="log1p",
            year_column="primary_return_year",
            predictors=(
                PredictorSpec("z_t2_window_mean_c", "primary_thermal_value_c"),
                PredictorSpec(
                    "z_log_matched_flow_cfs",
                    "matched_window_mean_usgs_flow_cfs",
                    "log",
                ),
            ),
        )
        a8_bundles.append(bundle)
        a8_vifs.extend(a8_vif_rows(bundle))
        influence_rows.extend(influence_refit_rows(bundle))
        regression_bundles.append(bundle)

    classify_primary_results(primary_results, sensitivity_results)

    coefficient_rows = [
        row for bundle in regression_bundles for row in bundle.coefficient_rows
    ]
    diagnostic_rows = [
        row for bundle in regression_bundles for row in bundle.diagnostic_rows
    ]
    ols_summary_rows = [bundle.summary for bundle in regression_bundles]
    joined_output = pd.concat(
        [
            joined[analysis_id].assign(join_analysis_id=analysis_id)
            for analysis_id in ("A1", "A2", "A3", "A4", "A5")
        ],
        ignore_index=True,
    )
    joined_output = joined_output.drop(columns=["_merge"])

    with tempfile.TemporaryDirectory(prefix="phase7-stage-", dir=ROOT / "outputs") as temp:
        staging = Path(temp)
        validation_payload = {
            "analysis_date": ANALYSIS_DATE,
            "status": "PASS",
            "checks_passed": len(checks),
            "checks_failed": 0,
            "protocol_version": PROTOCOL_VERSION,
            "protocol_sha256": EXPECTED_PROTOCOL_SHA256,
            "input_sha256": input_hashes,
            "checks": checks,
        }
        (staging / "phase7_input_validation.json").write_text(
            json.dumps(json_ready(validation_payload), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        write_csv(joined_output, staging / "phase7_joined_analysis_rows.csv")
        write_csv(pd.DataFrame(primary_results), staging / "phase7_primary_associations.csv")
        write_csv(
            pd.DataFrame(mechanism_results), staging / "phase7_mechanism_associations.csv"
        )
        write_csv(
            pd.DataFrame(sensitivity_results),
            staging / "phase7_sensitivity_associations.csv",
        )
        write_csv(pd.DataFrame(loo_rows), staging / "phase7_leave_one_year_out_rho.csv")
        write_csv(
            pd.DataFrame(loo_summary),
            staging / "phase7_leave_one_year_out_summary.csv",
        )
        write_csv(
            pd.DataFrame(temporal_rows), staging / "phase7_temporal_sensitivity.csv"
        )
        write_csv(
            pd.DataFrame(coefficient_rows), staging / "phase7_regression_coefficients.csv"
        )
        write_csv(
            pd.DataFrame(ols_summary_rows), staging / "phase7_regression_summaries.csv"
        )
        write_csv(
            pd.DataFrame(diagnostic_rows), staging / "phase7_regression_diagnostics.csv"
        )
        write_csv(
            pd.DataFrame(influence_rows), staging / "phase7_influence_sensitivity.csv"
        )
        write_csv(pd.DataFrame(a8_vifs), staging / "phase7_a8_vif.csv")
        plot_a8_diagnostics(a8_bundles, staging / "phase7_a8_diagnostics.png")

        report = build_report(
            input_hashes,
            checks,
            primary_results,
            mechanism_results,
            sensitivity_results,
            loo_summary,
            temporal_rows,
            [bundle.summary for bundle in a8_bundles],
            [row for bundle in a8_bundles for row in bundle.coefficient_rows],
            a8_vifs,
        )
        (staging / "phase7_hypothesis_analysis_report.md").write_text(
            report, encoding="utf-8", newline="\n"
        )
        artifact_hashes = {
            path.name: sha256_file(path)
            for path in sorted(staging.iterdir(), key=lambda item: item.name)
        }
        manifest = {
            "analysis_date": ANALYSIS_DATE,
            "status": "COMPLETE",
            "salmon_association_tests_run": True,
            "execution_order": [
                "input_validation",
                "primary_A1_A3_A5",
                "mechanism_A6_A7",
                "frozen_sensitivities",
                "secondary_A8",
            ],
            "protocol": {
                "path": relative(PROTOCOL_PATH),
                "version": PROTOCOL_VERSION,
                "sha256": EXPECTED_PROTOCOL_SHA256,
                "amendments": ["D-022"],
            },
            "analysis_program": {
                "path": relative(Path(__file__)),
                "sha256": sha256_file(Path(__file__)),
            },
            "inputs": input_hashes,
            "parameters": {
                "base_seed": BASE_SEED,
                "permutation_repetitions": PERMUTATION_REPETITIONS,
                "bootstrap_repetitions": BOOTSTRAP_REPETITIONS,
                "family_alpha": ALPHA,
                "temporal_residual_lag1_trigger": TEMPORAL_LAG1_TRIGGER,
            },
            "software": {
                "python": platform.python_version(),
                "pandas": pd.__version__,
                "numpy": np.__version__,
                "scipy": scipy.__version__,
                "statsmodels": statsmodels.__version__,
                "matplotlib": matplotlib.__version__,
            },
            "validation_checks_passed": len(checks),
            "row_counts": {
                "primary_results": len(primary_results),
                "mechanism_results": len(mechanism_results),
                "sensitivity_results": len(sensitivity_results),
                "leave_one_year_out_results": len(loo_rows),
                "temporal_sensitivity_results": len(temporal_rows),
                "a8_models": len(a8_bundles),
            },
            "artifacts_sha256": artifact_hashes,
        }
        (staging / "phase7_output_manifest.json").write_text(
            json.dumps(json_ready(manifest), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        publish_package(staging)

    print(
        f"Phase 7 complete: {len(checks)} validation checks passed; "
        f"3 primary, 2 mechanism, {len(sensitivity_results)} sensitivity, "
        f"and 2 A8 models published to {relative(OUTPUT_DIR)}."
    )


if __name__ == "__main__":
    main()
