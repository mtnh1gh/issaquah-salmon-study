"""Phase 6: illustrative conditional projections, not forecasts or policy effects."""
from __future__ import annotations
import os
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".matplotlib-cache"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from run_phase4_models import MODEL_FEATURES, fit_linear, predict_linear, standardize_train_test

TABLE_DIR = ROOT / "outputs/tables"; FIGURE_DIR = ROOT / "outputs/figures"
SCENARIOS = {"low": 0.10, "central": 0.50, "high": 0.90}

def main() -> None:
    master = pd.read_csv(ROOT / "data/gold/issaquah_creek_master.csv")
    predictions = pd.read_csv(TABLE_DIR / "phase4_rolling_predictions.csv")
    validation = pd.read_csv(TABLE_DIR / "phase4_model_validation.csv")
    retained = validation[(validation["scenario_eligible"]) & (validation["species"] == "Coho")]["model_id"].tolist()
    years = np.arange(2026, 2041)
    rows = []
    for model_id in retained:
        features = MODEL_FEATURES[model_id]
        data = master[master["species"] == "Coho"].sort_values("return_year")
        x_raw = data[features].to_numpy(float); y = np.log1p(data["total_adults"].to_numpy(float))
        x, _, means, scales = standardize_train_test(x_raw, x_raw)
        alpha = 100.0 if model_id == "all_environment_ridge" else 0.0
        coef = fit_linear(x, y, alpha)
        residuals = y - predict_linear(x, coef)
        held = predictions[(predictions["species"] == "Coho") & (predictions["model_id"] == model_id)]
        held_residuals = held["actual"].to_numpy(float) - held["predicted"].to_numpy(float)
        error_low, error_high = np.quantile(held_residuals, [.025, .975])
        for scenario, quantile in SCENARIOS.items():
            values = np.array([data[feature].quantile(quantile) for feature in features])
            standardized = (values - means) / scales
            estimate = max(0.0, float(np.expm1(predict_linear(standardized[None, :], coef)[0])))
            for year in years:
                rows.append({"species": "Coho", "model_id": model_id, "scenario": scenario, "year": year, "predictor_quantile": quantile, "predicted_adults": estimate, "lower_empirical": max(0.0, estimate + error_low), "upper_empirical": max(0.0, estimate + error_high), "input_basis": "1997-2025 observed feature quantile"})
    result = pd.DataFrame(rows)
    result.to_csv(TABLE_DIR / "phase6_conditional_projections.csv", index=False)
    ensemble = result.groupby(["scenario", "year"], as_index=False).agg(predicted_adults=("predicted_adults", "median"), lower_empirical=("lower_empirical", "median"), upper_empirical=("upper_empirical", "median"))
    ensemble["species"] = "Coho"; ensemble["model_set"] = "three retained Phase 4 candidates"; ensemble.to_csv(TABLE_DIR / "phase6_ensemble_projections.csv", index=False)
    fig, axis = plt.subplots(figsize=(11, 6)); colors = {"low": "#c44e52", "central": "#4c72b0", "high": "#55a868"}
    for scenario in SCENARIOS:
        group = ensemble[ensemble["scenario"] == scenario]
        axis.plot(group["year"], group["predicted_adults"], label=scenario, color=colors[scenario])
        axis.fill_between(group["year"], group["lower_empirical"], group["upper_empirical"], color=colors[scenario], alpha=.12)
    axis.set_title("Illustrative conditional Coho projections (not forecasts)"); axis.set_xlabel("Year"); axis.set_ylabel("Adults"); axis.legend(title="Observed quantile inputs", frameon=False); axis.grid(alpha=.2); fig.tight_layout(); fig.savefig(FIGURE_DIR / "phase6_conditional_projections.png", dpi=180); plt.close(fig)
    lines = ["# Phase 6 conditional scenario projections", "", "Status: illustrative only; not forecasts, causal estimates, or policy effects.", "", "The projections apply the three retained Coho association models to constant predictor values at the 10th, 50th, and 90th percentiles of their observed 1997-2025 feature distributions. This is a reproducible sensitivity illustration, not an authoritative climate or management trajectory.", "", "Hatchery releases and imperviousness are unavailable and held implicitly constant. PDO is an external uncertainty input, not a controllable intervention. Prediction bands are empirical held-out residual bounds and are not calibrated forecast intervals.", "", "Outputs: `outputs/tables/phase6_conditional_projections.csv`, `outputs/tables/phase6_ensemble_projections.csv`, and `outputs/figures/phase6_conditional_projections.png`.", "", "No Chinook projection is produced because no Chinook candidate passed the Phase 4 baseline gate.", ""]
    (ROOT / "docs/phase6_scenario_report.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Phase 6 scenarios complete: {len(result)} model-scenario-year rows.")
if __name__ == "__main__": main()
