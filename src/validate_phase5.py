"""Validate Phase 5 uncertainty outputs."""
from pathlib import Path
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
TABLE_DIR = ROOT / "outputs/tables"
def main() -> None:
    uncertainty = pd.read_csv(TABLE_DIR / "phase5_uncertainty.csv"); intervals = pd.read_csv(TABLE_DIR / "phase5_prediction_intervals.csv")
    assert len(uncertainty) == 3; assert len(intervals) == 51; assert set(uncertainty["n_validation_years"]) == {17}
    assert uncertainty[["mae_ci_low", "mae_ci_high", "rmse_ci_low", "rmse_ci_high"]].notna().all().all()
    assert (intervals["lower_95_empirical"] >= 0).all(); assert (intervals["upper_95_empirical"] >= intervals["lower_95_empirical"]).all()
    assert (ROOT / "docs/phase5_uncertainty_report.md").is_file(); assert (ROOT / "outputs/figures/phase5_uncertainty.png").is_file()
    print("Phase 5 validation PASS: 7 checks.")
if __name__ == "__main__": main()
