"""Validate Phase 4 statistical-model outputs and protocol invariants."""

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
TABLE_DIR = ROOT / "outputs/tables"


def check(condition: bool, message: str, results: list[str]) -> None:
    if not condition:
        raise AssertionError(message)
    results.append(message)


def main() -> None:
    validation = pd.read_csv(TABLE_DIR / "phase4_model_validation.csv")
    predictions = pd.read_csv(TABLE_DIR / "phase4_rolling_predictions.csv")
    coefficients = pd.read_csv(TABLE_DIR / "phase4_coefficients.csv")
    diagnostics = pd.read_csv(TABLE_DIR / "phase4_diagnostics.csv")
    influence = pd.read_csv(TABLE_DIR / "phase4_influence_sensitivity.csv")
    lags = pd.read_csv(TABLE_DIR / "phase4_chinook_lag_sensitivity.csv")
    results: list[str] = []

    check(len(validation) == 10, "Ten species/model experiments are registered", results)
    check(len(predictions) == 170, "All 17 rolling-origin years exist for ten experiments", results)
    check(set(predictions["n_train"]) == set(range(12, 29)), "Training windows expand from 12 through 28 years", results)
    check((predictions["train_end_year"] < predictions["test_year"]).all(), "No validation fold trains on its test year or the future", results)
    check(predictions[["actual", "predicted"]].notna().all().all(), "All validation outcomes and predictions are finite", results)
    check((predictions["predicted"] >= 0).all(), "All back-transformed count predictions are nonnegative", results)
    check(len(coefficients) == 22, "All 22 pre-specified model coefficients are present", results)
    check(len(diagnostics) == 6, "All six fitted association models have diagnostics", results)
    check(len(influence) == 22, "Every coefficient has an influential-year sensitivity estimate", results)
    check(set(lags["lag_years"]) == {3, 4, 5}, "Chinook lag sensitivity covers lags 3, 4, and 5", results)
    check(lags.loc[lags["is_primary_lag"], "lag_years"].tolist() == [4], "Chinook lag 4 is the sole primary lag", results)
    check(
        validation.loc[validation["species"] == "Chinook", "scenario_eligible"].sum() == 0,
        "No Chinook model passes the scenario-eligibility gate",
        results,
    )
    check(
        validation.loc[validation["species"] == "Coho", "scenario_eligible"].sum() == 3,
        "Three Coho candidates pass the preliminary baseline gate",
        results,
    )
    check((ROOT / "docs/statistical_analysis_report.md").is_file(), "Statistical report is present", results)
    check((ROOT / "docs/model_registry.md").is_file(), "Model registry is present", results)

    lines = [
        "# Phase 4 validation report",
        "",
        "Status: PASS",
        "",
        f"Checks passed: {len(results)}",
        "",
        *(f"- PASS: {result}" for result in results),
        "",
        "```powershell",
        r".\.venv\Scripts\python.exe .\src\validate_phase4.py",
        "```",
        "",
    ]
    (ROOT / "docs/phase4_validation_report.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )
    print(f"Phase 4 validation PASS: {len(results)} checks.")


if __name__ == "__main__":
    main()
