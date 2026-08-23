"""Independently validate reported Phase 7 outputs without rerunning analyses.

This standard-library-only validator does not import the Phase 7 analysis
program and does not recompute correlations, permutations, bootstraps, or OLS
models. It checks output schemas, identities, family membership, reported Holm
adjustments, frozen row counts, analysis/sensitivity separation, and hashes.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "outputs/phase7"
VALIDATION_PATH = OUTPUT_DIR / "phase7_independent_validation.json"
ANALYSIS_PROGRAM_PATH = ROOT / "src/run_phase7_hypothesis_tests.py"

VALIDATOR_VERSION = "1.0.0"
EXPECTED_ANALYSIS_PROGRAM_VERSION = "1.2.0"
EXPECTED_PROTOCOL_SHA256 = (
    "33BFCCD299DA7064462B9F66F1944638E6949FFB5406C78DC9EE6E97E8D15DE2"
)
EXPECTED_PRIMARY_IDS = ("A1", "A3", "A5")
EXPECTED_MECHANISM_IDS = ("A6", "A7")
EXPECTED_PRIMARY_N = {"A1": 29, "A3": 29, "A5": 29}
EXPECTED_MECHANISM_N = {"A6": 29, "A7": 31}
PRIMARY_HOLM_FAMILY = "primary_A1_A3_A5_holm"
MECHANISM_HOLM_FAMILY = "mechanism_A6_A7_holm"
EXPECTED_DIRECTION_ROLE = "prespecified_reporting_only_not_pvalue_tail"

REQUIRED_OUTPUTS = {
    "primary": "phase7_primary_results.csv",
    "mechanism": "phase7_mechanism_results.csv",
    "sensitivity": "phase7_sensitivity_results.csv",
    "primary_detail": "phase7_primary_associations.csv",
    "mechanism_detail": "phase7_mechanism_associations.csv",
    "sensitivity_detail": "phase7_sensitivity_associations.csv",
    "temporal_detail": "phase7_temporal_sensitivity.csv",
    "joined_rows": "phase7_joined_analysis_rows.csv",
    "metadata": "phase7_execution_metadata.json",
    "manifest": "phase7_output_manifest.json",
    "report": "phase7_hypothesis_analysis_report.md",
}


class Checks:
    def __init__(self) -> None:
        self.rows: list[dict[str, object]] = []

    def add(self, check_id: str, passed: bool, detail: str) -> None:
        self.rows.append(
            {
                "check_id": check_id,
                "status": "PASS" if passed else "FAIL",
                "detail": detail,
            }
        )

    @property
    def failures(self) -> list[dict[str, object]]:
        return [row for row in self.rows if row["status"] == "FAIL"]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"CSV has no header: {relative(path)}")
        return list(reader)


def read_json(path: Path) -> dict[str, object]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {relative(path)}")
    return value


def as_int(row: dict[str, str], field: str) -> int:
    return int(row[field])


def as_float(row: dict[str, str], field: str) -> float:
    return float(row[field])


def optional_float(row: dict[str, str], field: str) -> float | None:
    value = row.get(field, "").strip()
    return None if value == "" else float(value)


def as_bool(row: dict[str, str], field: str) -> bool:
    value = row[field].strip().lower()
    if value not in {"true", "false"}:
        raise ValueError(f"{field} is not a Boolean: {row[field]!r}")
    return value == "true"


def close(left: float, right: float, tolerance: float = 1e-8) -> bool:
    return math.isclose(left, right, rel_tol=tolerance, abs_tol=tolerance)


def sign(value: float) -> int:
    return 1 if value > 0 else -1 if value < 0 else 0


def direction(value: float) -> str:
    return "positive" if value > 0 else "negative" if value < 0 else "zero"


def holm_adjust(rows: list[dict[str, str]], p_field: str) -> dict[str, float]:
    """Recalculate only the adjustment of already-reported raw p-values."""
    indexed = [(index, row, as_float(row, p_field)) for index, row in enumerate(rows)]
    ordered = sorted(indexed, key=lambda item: (item[2], item[0]))
    running_max = 0.0
    adjusted: dict[str, float] = {}
    family_size = len(rows)
    for rank, (_, row, p_value) in enumerate(ordered):
        running_max = max(running_max, (family_size - rank) * p_value)
        adjusted[row["analysis_id"]] = min(running_max, 1.0)
    return adjusted


def unique_by(rows: Iterable[dict[str, str]], field: str) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for row in rows:
        if row[field] in result:
            raise ValueError(f"Duplicate {field}={row[field]}")
        result[row[field]] = row
    return result


def required_columns(
    checks: Checks,
    check_id: str,
    rows: list[dict[str, str]],
    fields: set[str],
) -> bool:
    present = set(rows[0]) if rows else set()
    missing = sorted(fields - present)
    checks.add(check_id, not missing, f"missing={missing}" if missing else "all required fields present")
    return not missing


def write_validation(checks: Checks, manifest: dict[str, object] | None) -> None:
    passed = len(checks.rows) - len(checks.failures)
    validator_path = Path(__file__).resolve()
    manifest_hash = (
        sha256_file(OUTPUT_DIR / REQUIRED_OUTPUTS["manifest"])
        if (OUTPUT_DIR / REQUIRED_OUTPUTS["manifest"]).is_file()
        else None
    )
    payload = {
        "status": "PASS" if not checks.failures else "FAIL",
        "validator": {
            "path": relative(validator_path),
            "version": VALIDATOR_VERSION,
            "sha256": sha256_file(validator_path),
            "runtime_dependency": "python_standard_library_only",
            "imports_analysis_program": False,
        },
        "validated_analysis_run_timestamp_utc": (
            manifest.get("run_timestamp_utc") if manifest else None
        ),
        "validated_output_manifest_sha256": manifest_hash,
        "scope": (
            "Output-only structural and consistency validation; association statistics "
            "are not recalculated from source data. The validation report is intentionally "
            "outside the analysis manifest so the validator remains independent."
        ),
        "checks_total": len(checks.rows),
        "checks_passed": passed,
        "checks_failed": len(checks.failures),
        "checks": checks.rows,
    }
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    temporary = VALIDATION_PATH.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    os.replace(temporary, VALIDATION_PATH)


def validate() -> tuple[Checks, dict[str, object] | None]:
    checks = Checks()
    paths = {key: OUTPUT_DIR / name for key, name in REQUIRED_OUTPUTS.items()}
    missing = [relative(path) for path in paths.values() if not path.is_file()]
    checks.add(
        "required_outputs_exist",
        not missing,
        f"missing={missing}" if missing else f"all {len(paths)} required outputs exist",
    )
    if missing:
        return checks, None

    try:
        primary = read_csv_rows(paths["primary"])
        mechanism = read_csv_rows(paths["mechanism"])
        sensitivity = read_csv_rows(paths["sensitivity"])
        primary_detail = read_csv_rows(paths["primary_detail"])
        mechanism_detail = read_csv_rows(paths["mechanism_detail"])
        sensitivity_detail = read_csv_rows(paths["sensitivity_detail"])
        temporal_detail = read_csv_rows(paths["temporal_detail"])
        joined = read_csv_rows(paths["joined_rows"])
        metadata = read_json(paths["metadata"])
        manifest = read_json(paths["manifest"])
    except Exception as error:
        checks.add("required_outputs_readable", False, f"{type(error).__name__}: {error}")
        return checks, None
    checks.add("required_outputs_readable", True, "all required CSV/JSON outputs parsed")

    manifest_artifacts = manifest.get("artifacts_sha256", {})
    hash_errors: list[str] = []
    if not isinstance(manifest_artifacts, dict):
        hash_errors.append("artifacts_sha256 is not an object")
    else:
        for name, expected_hash in manifest_artifacts.items():
            artifact = OUTPUT_DIR / str(name)
            if not artifact.is_file():
                hash_errors.append(f"missing:{name}")
            elif sha256_file(artifact) != expected_hash:
                hash_errors.append(f"hash:{name}")
        for role, path in paths.items():
            if role not in {"manifest"} and path.name not in manifest_artifacts:
                hash_errors.append(f"not_manifested:{path.name}")
    checks.add(
        "analysis_manifest_integrity",
        not hash_errors,
        f"errors={hash_errors}" if hash_errors else f"verified {len(manifest_artifacts)} artifact hashes",
    )

    required_columns(
        checks,
        "primary_schema",
        primary,
        {
            "analysis_id",
            "analysis_role",
            "predictor_model_id",
            "thermal_metric_role",
            "row_exclusion_status",
            "n",
            "expected_sign",
            "inference_sidedness",
            "expected_direction_role",
            "observed_spearman_rho",
            "raw_permutation_p",
            "holm_adjusted_p",
            "formal_support_status",
        },
    )
    required_columns(
        checks,
        "mechanism_schema",
        mechanism,
        {
            "analysis_id",
            "analysis_role",
            "n",
            "expected_sign",
            "inference_sidedness",
            "expected_direction_role",
            "observed_spearman_rho",
            "raw_permutation_p",
            "holm_adjusted_p",
        },
    )
    required_columns(
        checks,
        "sensitivity_schema",
        sensitivity,
        {
            "analysis_id",
            "analysis_role",
            "sensitivity_type",
            "sensitivity_id",
            "n",
            "inference_sidedness",
            "expected_direction_role",
            "sensitivity_rho",
            "raw_permutation_p",
            "inference_status",
        },
    )

    primary_ids = [row.get("analysis_id", "") for row in primary]
    mechanism_ids = [row.get("analysis_id", "") for row in mechanism]
    checks.add(
        "exactly_three_primary_thermal_tests",
        len(primary) == 3 and set(primary_ids) == set(EXPECTED_PRIMARY_IDS),
        f"rows={len(primary)}; ids={primary_ids}",
    )
    checks.add(
        "exactly_two_mechanism_tests",
        len(mechanism) == 2 and set(mechanism_ids) == set(EXPECTED_MECHANISM_IDS),
        f"rows={len(mechanism)}; ids={mechanism_ids}",
    )

    try:
        primary_map = unique_by(primary, "analysis_id")
        mechanism_map = unique_by(mechanism, "analysis_id")
        primary_detail_map = unique_by(primary_detail, "analysis_id")
        mechanism_detail_map = unique_by(mechanism_detail, "analysis_id")
        checks.add("result_ids_unique", True, "primary and mechanism IDs are unique")
    except Exception as error:
        checks.add("result_ids_unique", False, str(error))
        return checks, manifest

    try:
        calculated_primary_holm = holm_adjust(primary, "raw_permutation_p")
        primary_holm_ok = all(
            close(as_float(row, "holm_adjusted_p"), calculated_primary_holm[analysis_id])
            for analysis_id, row in primary_map.items()
        )
        calculated_mechanism_holm = holm_adjust(mechanism, "raw_permutation_p")
        mechanism_holm_ok = all(
            close(as_float(row, "holm_adjusted_p"), calculated_mechanism_holm[analysis_id])
            for analysis_id, row in mechanism_map.items()
        )
    except Exception as error:
        primary_holm_ok = False
        mechanism_holm_ok = False
        calculated_primary_holm = {"error": str(error)}
        calculated_mechanism_holm = {"error": str(error)}
    checks.add(
        "holm_primary_family_reconciles",
        primary_holm_ok,
        f"reported IDs={primary_ids}; recalculated_from_reported_raw_p={calculated_primary_holm}",
    )
    checks.add(
        "holm_mechanism_family_reconciles",
        mechanism_holm_ok,
        f"reported IDs={mechanism_ids}; recalculated_from_reported_raw_p={calculated_mechanism_holm}",
    )
    family_labels_ok = all(
        row.get("p_adjustment_family") == PRIMARY_HOLM_FAMILY
        for row in primary_detail
    ) and all(
        row.get("p_adjustment_family") == MECHANISM_HOLM_FAMILY
        for row in mechanism_detail
    )
    checks.add(
        "holm_applied_to_correct_families",
        family_labels_ok,
        "A1/A3/A5 use primary family; A6/A7 use separate mechanism family",
    )

    primary_joined = [row for row in joined if row.get("analysis_id") in EXPECTED_PRIMARY_IDS]
    primary_join_counts = Counter(row.get("analysis_id") for row in primary_joined)
    primary_metrics_ok = all(
        row.get("analysis_role") == "primary_confirmatory_family"
        and row.get("predictor_model_id") == "T2"
        and row.get("thermal_metric_role") == "primary_window_mean"
        for row in primary
    ) and all(
        row.get("primary_thermal_model_id") == "T2"
        and row.get("primary_thermal_variable") == "t2_window_mean_proxy_c"
        and row.get("threshold_count_metric_status") == "exploratory_only"
        and row.get("other_nonmean_thermal_metric_status") == "exploratory_only"
        for row in primary_joined
    )
    checks.add(
        "no_exploratory_metric_in_primary_family",
        primary_metrics_ok,
        "primary role is T2 window mean; joined nonmean/threshold metrics are exploratory_only",
    )
    no_t1_primary = all(
        row.get("predictor_model_id") == "T2" for row in primary
    ) and all(
        row.get("predictor") == "T2 biological-window mean proxy (C)"
        and row.get("sensitivity_id") == "t2_primary"
        for row in primary_detail
    ) and all(
        close(
            as_float(row, "primary_thermal_value_c"),
            as_float(row, "t2_window_mean_proxy_c"),
        )
        for row in primary_joined
    )
    checks.add(
        "no_t1_value_as_primary_predictor",
        no_t1_primary,
        "primary predictor/model/value identities are T2; T1 appears only in sensitivity fields",
    )

    primary_n_ok = all(
        as_int(primary_map[analysis_id], "n") == EXPECTED_PRIMARY_N[analysis_id]
        and as_int(primary_detail_map[analysis_id], "n") == EXPECTED_PRIMARY_N[analysis_id]
        and primary_join_counts[analysis_id] == EXPECTED_PRIMARY_N[analysis_id]
        for analysis_id in EXPECTED_PRIMARY_IDS
    )
    checks.add(
        "primary_n_matches_frozen_expectations",
        primary_n_ok,
        f"result/detail/join counts={dict(primary_join_counts)}",
    )
    mechanism_n_ok = all(
        as_int(mechanism_map[analysis_id], "n") == EXPECTED_MECHANISM_N[analysis_id]
        and as_int(mechanism_detail_map[analysis_id], "n")
        == EXPECTED_MECHANISM_N[analysis_id]
        for analysis_id in EXPECTED_MECHANISM_IDS
    )
    checks.add(
        "mechanism_n_matches_frozen_expectations",
        mechanism_n_ok,
        f"expected={EXPECTED_MECHANISM_N}",
    )
    joined_keys = [
        (row.get("analysis_id"), row.get("species"), row.get("primary_return_year"))
        for row in joined
    ]
    joined_counts = Counter(row.get("analysis_id") for row in joined)
    joined_ok = (
        len(joined) == 145
        and len(set(joined_keys)) == 145
        and all(joined_counts[analysis_id] == 29 for analysis_id in ("A1", "A2", "A3", "A4", "A5"))
    )
    checks.add(
        "joined_response_rows_unique_and_complete",
        joined_ok,
        f"rows={len(joined)}; by_analysis={dict(joined_counts)}",
    )

    retained_flags_ok = True
    retained_details: dict[str, dict[str, int]] = {}
    for analysis_id in EXPECTED_PRIMARY_IDS:
        group = [row for row in primary_joined if row["analysis_id"] == analysis_id]
        flagged_rows = sum(as_int(row, "t2_extrapolation_days") > 0 for row in group)
        flagged_days = sum(as_int(row, "t2_extrapolation_days") for row in group)
        reported = primary_detail_map[analysis_id]
        retained_flags_ok = retained_flags_ok and (
            primary_map[analysis_id].get("row_exclusion_status")
            == "none_all_29_frozen_rows_retained"
            and as_int(reported, "n") == len(group)
            and as_int(reported, "t2_extrapolation_flagged_rows") == flagged_rows
            and as_int(reported, "t2_extrapolation_days_total") == flagged_days
        )
        retained_details[analysis_id] = {
            "n": len(group),
            "flagged_rows_retained": flagged_rows,
            "flagged_days_retained": flagged_days,
        }
    checks.add(
        "no_post_hoc_primary_row_deletion",
        retained_flags_ok,
        f"{retained_details}",
    )

    inference_roles_ok = all(
        row.get("inference_sidedness") == "two_sided"
        and row.get("expected_direction_role") == EXPECTED_DIRECTION_ROLE
        and row.get("expected_sign") in {"negative", "positive"}
        and as_bool(row, "expected_direction_matched")
        == (direction(as_float(row, "observed_spearman_rho")) == row["expected_sign"])
        for row in primary + mechanism
    ) and all(
        row.get("inference_sidedness") == "two_sided"
        and row.get("expected_direction_role") == EXPECTED_DIRECTION_ROLE
        and as_int(row, "permutation_repetitions") == 100_000
        for row in primary_detail + mechanism_detail
    )
    checks.add(
        "expected_direction_separate_from_inference_tail",
        inference_roles_ok,
        "expected sign is reporting-only; every confirmatory permutation field declares two_sided",
    )

    sensitivity_counts = Counter(row.get("sensitivity_type") for row in sensitivity)
    expected_sensitivity_counts = {
        "alternate_window": 2,
        "T1": 3,
        "jack_inclusive": 3,
        "extrapolation_exclusion": 3,
        "cook_exclusion": 3,
        "temporal_sensitivity": 3,
    }
    sensitivity_roles_ok = (
        len(sensitivity) == 17
        and sensitivity_counts == Counter(expected_sensitivity_counts)
        and all(row.get("analysis_role") == "sensitivity_only" for row in sensitivity)
    )
    checks.add(
        "sensitivity_rows_have_separate_role",
        sensitivity_roles_ok,
        f"counts={dict(sensitivity_counts)}",
    )

    association_sensitivity = [
        row for row in sensitivity if row.get("sensitivity_type") != "temporal_sensitivity"
    ]
    association_sensitivity_ok = all(
        row.get("inference_sidedness") == "two_sided"
        and row.get("expected_direction_role") == EXPECTED_DIRECTION_ROLE
        and row.get("inference_status") == "descriptive_unadjusted_sensitivity"
        for row in association_sensitivity
    )
    checks.add(
        "association_sensitivities_are_descriptive_unadjusted",
        association_sensitivity_ok,
        f"rows={len(association_sensitivity)}",
    )

    no_extrap_rows = {
        row["analysis_id"]: row
        for row in sensitivity
        if row.get("sensitivity_type") == "extrapolation_exclusion"
    }
    extrapolation_n_ok = all(
        as_int(no_extrap_rows[analysis_id], "n")
        == sum(
            as_int(row, "t2_extrapolation_days") == 0
            for row in primary_joined
            if row["analysis_id"] == analysis_id
        )
        for analysis_id in EXPECTED_PRIMARY_IDS
    )
    no_extrap_n = {
        analysis_id: as_int(row, "n") for analysis_id, row in no_extrap_rows.items()
    }
    checks.add(
        "extrapolation_deletion_confined_to_sensitivity",
        extrapolation_n_ok,
        f"sensitivity n={no_extrap_n}",
    )
    cook_rows = [
        row for row in sensitivity if row.get("sensitivity_type") == "cook_exclusion"
    ]
    cook_ok = len(cook_rows) == 3 and all(
        as_int(row, "n") == 28
        and row.get("excluded_return_year", "") != ""
        and row.get("analysis_role") == "sensitivity_only"
        for row in cook_rows
    )
    checks.add(
        "cook_deletion_confined_to_sensitivity",
        cook_ok,
        "three one-row Cook exclusions; primary rows retain n=29",
    )

    reported_identity_ok = True
    identity_fields = (
        ("n", "n", int),
        ("observed_spearman_rho", "spearman_rho", float),
        ("raw_permutation_p", "permutation_p_raw", float),
        ("holm_adjusted_p", "permutation_p_holm", float),
        ("bootstrap_ci_lower", "bootstrap_ci_low", float),
        ("bootstrap_ci_upper", "bootstrap_ci_high", float),
        ("ols_beta", "ols_beta", float),
        ("hc3_ci_lower", "ols_hc3_ci_low", float),
        ("hc3_ci_upper", "ols_hc3_ci_high", float),
    )
    for analysis_id in EXPECTED_PRIMARY_IDS:
        public = primary_map[analysis_id]
        detail = primary_detail_map[analysis_id]
        for public_field, detail_field, kind in identity_fields:
            if kind is int:
                matched = as_int(public, public_field) == as_int(detail, detail_field)
            else:
                matched = close(as_float(public, public_field), as_float(detail, detail_field))
            reported_identity_ok = reported_identity_ok and matched
        reported_identity_ok = reported_identity_ok and (
            public["formal_support_status"]
            == detail["protocol_support_classification"]
        )
    checks.add(
        "public_primary_results_match_detailed_primary_results",
        reported_identity_ok,
        "all effect/inference fields and support status reconcile by analysis ID",
    )

    sensitivity_lookup = {
        (row["analysis_id"], row["sensitivity_type"]): row for row in sensitivity
    }
    support_ok = True
    for analysis_id in EXPECTED_PRIMARY_IDS:
        row = primary_map[analysis_id]
        t1 = sensitivity_lookup[(analysis_id, "T1")]
        cook = sensitivity_lookup[(analysis_id, "cook_exclusion")]
        supported = (
            as_bool(row, "expected_direction_matched")
            and as_float(row, "holm_adjusted_p") < 0.05
            and sign(as_float(t1, "sensitivity_rho"))
            == sign(as_float(row, "observed_spearman_rho"))
            and sign(as_float(cook, "sensitivity_rho"))
            == sign(as_float(row, "observed_spearman_rho"))
        )
        expected_status = (
            "supported_by_observational_analysis"
            if supported
            else "not_supported_by_these_data"
        )
        support_ok = support_ok and row["formal_support_status"] == expected_status
    checks.add(
        "sensitivity_cannot_overwrite_formal_primary_status",
        support_ok,
        "formal status is reconstructed from primary Holm/direction plus frozen T1 and Cook sign checks",
    )

    temporal_rows = [
        row for row in sensitivity if row.get("sensitivity_type") == "temporal_sensitivity"
    ]
    temporal_by_id = {row["analysis_id"]: row for row in temporal_rows}
    temporal_detail_by_id = {row["analysis_id"]: row for row in temporal_detail}
    temporal_ok = (
        len(temporal_rows) == 3
        and set(temporal_by_id) == set(EXPECTED_PRIMARY_IDS)
        and len(temporal_detail) == 3
        and set(temporal_detail_by_id) == set(EXPECTED_PRIMARY_IDS)
        and all(
            row.get("analysis_role") == "sensitivity_only"
            and row.get("inference_status") == "temporal_trend_sensitivity_only"
            and row.get("inference_sidedness")
            == "not_applicable_no_unrestricted_pvalue"
            and row.get("raw_permutation_p", "") == ""
            for row in temporal_rows
        )
        and all(
            row.get("interpretation_status") == "temporal_trend_sensitivity_only"
            for row in temporal_detail
        )
        and all("temporal" not in row.get("analysis_role", "") for row in primary + mechanism)
    )
    for analysis_id in EXPECTED_PRIMARY_IDS:
        if analysis_id in temporal_by_id and analysis_id in temporal_detail_by_id:
            temporal_ok = temporal_ok and close(
                as_float(temporal_by_id[analysis_id], "sensitivity_rho"),
                as_float(temporal_detail_by_id[analysis_id], "rho_detrended"),
            )
    checks.add(
        "temporal_amendment_is_sensitivity_only",
        temporal_ok,
        "D-022 has three sensitivity-only rows, no unrestricted p-value, and no primary-family membership",
    )

    metadata_program = metadata.get("analysis_program", {})
    metadata_protocol = metadata.get("protocol", {})
    metadata_inputs = metadata.get("input_file_sha256", {})
    metadata_seeds = metadata.get("random_seeds", {})
    software = metadata.get("software_versions", {})
    metadata_ok = (
        isinstance(metadata_program, dict)
        and metadata_program.get("version") == EXPECTED_ANALYSIS_PROGRAM_VERSION
        and metadata_program.get("sha256") == sha256_file(ANALYSIS_PROGRAM_PATH)
        and isinstance(metadata_protocol, dict)
        and metadata_protocol.get("sha256") == EXPECTED_PROTOCOL_SHA256
        and isinstance(metadata_inputs, dict)
        and len(metadata_inputs) == 5
        and all(len(str(value)) == 64 for value in metadata_inputs.values())
        and isinstance(metadata_seeds, dict)
        and set(metadata_seeds.get("permutation_by_analysis_id", {}))
        == {"A1", "A2", "A3", "A4", "A5", "A6", "A7"}
        and isinstance(software, dict)
        and {"python", "pandas", "numpy", "scipy", "statsmodels", "matplotlib"}
        <= set(software)
    )
    checks.add(
        "execution_metadata_contract",
        metadata_ok,
        "protocol/program SHA and version, five input hashes, explicit seeds, and package versions present",
    )
    manifest_program = manifest.get("analysis_program", {})
    manifest_ok = (
        manifest.get("status") == "COMPLETE"
        and manifest.get("salmon_association_tests_run") is True
        and manifest.get("run_timestamp_utc") == metadata.get("run_timestamp_utc")
        and isinstance(manifest_program, dict)
        and manifest_program.get("sha256") == metadata_program.get("sha256")
        and manifest_program.get("version") == metadata_program.get("version")
        and manifest.get("row_counts", {}).get(
            "combined_machine_readable_sensitivity_results"
        )
        == 17
    )
    checks.add(
        "manifest_metadata_identity",
        manifest_ok,
        "completion status, run timestamp, program identity, and sensitivity row count reconcile",
    )
    return checks, manifest


def main() -> None:
    checks, manifest = validate()
    write_validation(checks, manifest)
    if checks.failures:
        print(
            f"Phase 7 independent validation: FAIL "
            f"({len(checks.failures)} of {len(checks.rows)} checks failed); "
            f"see {relative(VALIDATION_PATH)}."
        )
        sys.exit(1)
    print(
        f"Phase 7 independent validation: PASS "
        f"({len(checks.rows)} checks); wrote {relative(VALIDATION_PATH)}."
    )


if __name__ == "__main__":
    main()
