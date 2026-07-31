"""Final package consistency checks before release or domain review."""
from pathlib import Path
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
def main() -> None:
    required = ["docs/final_awareness_report.md", "docs/eda_report.md", "docs/statistical_analysis_report.md", "docs/phase5_uncertainty_report.md", "docs/phase6_scenario_report.md"]
    assert all((ROOT / path).is_file() for path in required)
    assert len(pd.read_csv(ROOT / "outputs/tables/phase6_conditional_projections.csv")) == 135
    assert len(pd.read_csv(ROOT / "outputs/tables/phase6_ensemble_projections.csv")) == 45
    assert "not forecasts" in (ROOT / "docs/final_awareness_report.md").read_text(encoding="utf-8")
    assert "unmeasured confounder" in (ROOT / "docs/final_awareness_report.md").read_text(encoding="utf-8")
    print("Final package validation PASS: 5 checks.")
if __name__ == "__main__": main()
