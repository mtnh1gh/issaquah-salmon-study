"""Validate Phase 6 conditional scenario outputs."""
from pathlib import Path
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
def main() -> None:
    result = pd.read_csv(ROOT / "outputs/tables/phase6_conditional_projections.csv")
    ensemble = pd.read_csv(ROOT / "outputs/tables/phase6_ensemble_projections.csv")
    assert len(result) == 135 and len(ensemble) == 45
    assert set(result["scenario"]) == {"low", "central", "high"}; assert set(result["year"]) == set(range(2026, 2041))
    assert result[["predicted_adults", "lower_empirical", "upper_empirical"]].notna().all().all()
    assert (result["lower_empirical"] >= 0).all() and (result["upper_empirical"] >= result["lower_empirical"]).all()
    assert (ROOT / "docs/phase6_scenario_report.md").is_file() and (ROOT / "outputs/figures/phase6_conditional_projections.png").is_file()
    print("Phase 6 validation PASS: 5 checks.")
if __name__ == "__main__": main()
