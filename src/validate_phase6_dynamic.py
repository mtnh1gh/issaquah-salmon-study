from pathlib import Path
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
def main() -> None:
    x = pd.read_csv(ROOT / "outputs/tables/phase6_dynamic_projections.csv"); e = pd.read_csv(ROOT / "outputs/tables/phase6_dynamic_ensemble.csv")
    assert len(x) == 135 and len(e) == 45 and set(x.year) == set(range(2026, 2041)) and set(x.scenario) == {"higher_input", "trend_only", "lower_input"}
    assert (x.lower_90 >= 0).all() and (x.upper_90 >= x.lower_90).all() and x[["median_adults", "lower_90", "upper_90"]].notna().all().all()
    assert (ROOT / "docs/phase6_dynamic_report.md").is_file() and (ROOT / "outputs/figures/phase6_dynamic_projections.png").is_file()
    print("Dynamic Phase 6 validation PASS: 3 checks.")
if __name__ == "__main__": main()
