"""Validate the Phase 3 exploratory-analysis outputs."""

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
TABLE_DIR = ROOT / "outputs/tables"
FIGURE_DIR = ROOT / "outputs/figures"


def check(condition: bool, message: str, results: list[str]) -> None:
    if not condition:
        raise AssertionError(message)
    results.append(message)


def main() -> None:
    trends = pd.read_csv(TABLE_DIR / "trend_tests.csv")
    correlations = pd.read_csv(TABLE_DIR / "return_predictor_correlations.csv")
    lags = pd.read_csv(TABLE_DIR / "lag_sensitivity.csv")
    missingness = pd.read_csv(TABLE_DIR / "master_missingness.csv")
    results: list[str] = []

    check(len(trends) == 11, "Trend table has 11 pre-specified tests", results)
    check(len(correlations) == 14, "Correlation table has 14 pre-specified tests", results)
    check(len(lags) == 12, "Lag table has 12 pre-specified tests", results)
    check(set(correlations["n"]) == {29}, "Every primary correlation uses all 29 return years", results)
    check(correlations["p_fdr_bh"].between(0, 1).all(), "All adjusted correlation p-values are valid", results)
    check(trends["p_fdr_bh"].between(0, 1).all(), "All adjusted trend p-values are valid", results)
    check(
        set(missingness.loc[missingness["missing_count"] == 58, "variable"])
        == {"impervious_pct", "hatchery_releases"},
        "Only the two documented blocked fields are entirely unavailable",
        results,
    )
    expected_figures = {
        "annual_salmon_returns.png",
        "wild_origin_returns_2010_onward.png",
        "environmental_trends.png",
        "return_predictor_correlations.png",
    }
    present_figures = {path.name for path in FIGURE_DIR.glob("*.png")}
    check(
        expected_figures <= present_figures,
        "All four expected figures are present",
        results,
    )
    check((ROOT / "docs/eda_report.md").is_file(), "Exploratory analysis report is present", results)

    report = ROOT / "docs/phase3_validation_report.md"
    lines = [
        "# Phase 3 validation report",
        "",
        "Status: PASS",
        "",
        f"Checks passed: {len(results)}",
        "",
        *(f"- PASS: {result}" for result in results),
        "",
        "Run after regenerating the EDA outputs:",
        "",
        "```powershell",
        r".\.venv\Scripts\python.exe .\src\validate_phase3.py",
        "```",
        "",
    ]
    report.write_text("\n".join(lines), encoding="utf-8")
    print(f"Phase 3 validation PASS: {len(results)} checks.")


if __name__ == "__main__":
    main()
