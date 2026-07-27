"""Dynamic Phase 6 scenarios using observed trends plus stochastic variability.

These are exploratory trajectories, not authoritative climate forecasts.
"""
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
from scipy import stats
from run_phase4_models import MODEL_FEATURES, fit_linear, predict_linear, standardize_train_test

TABLE_DIR = ROOT / "outputs/tables"; FIGURE_DIR = ROOT / "outputs/figures"
YEARS = np.arange(2026, 2041); SCENARIOS = {"higher_input": 1, "trend_only": 0, "lower_input": -1}; DRAWS = 1000; SEED = 20260727

def main() -> None:
    master = pd.read_csv(ROOT / "data/processed/issaquah_creek_master.csv")
    env = pd.read_csv(ROOT / "data/processed/issaquah_annual_environment.csv").set_index("return_year")
    validation = pd.read_csv(TABLE_DIR / "phase4_model_validation.csv")
    retained = validation[(validation["scenario_eligible"]) & (validation["species"] == "Coho")]["model_id"].tolist()
    hist = env.loc[1997:2025]
    feature_names = sorted({f for m in retained for f in MODEL_FEATURES[m]})
    env_name = {"cohort_flow_water_year_mean_cfs": "flow_water_year_mean_cfs", "cohort_swe_apr01_inches": "swe_apr01_inches", "marine_pdo_mean": "pdo_annual_mean"}
    slopes = {f: stats.theilslopes(hist[env_name.get(f, f)], hist.index).slope for f in feature_names}
    resid_sd = {f: float(np.std(hist[env_name.get(f, f)] - np.polyval(np.polyfit(hist.index, hist[env_name.get(f, f)], 1), hist.index), ddof=1)) for f in feature_names}
    rng = np.random.default_rng(SEED); rows = []
    for model_id in retained:
        data = master[master["species"] == "Coho"].sort_values("return_year"); features = MODEL_FEATURES[model_id]
        x_raw = data[features].to_numpy(float); y = np.log1p(data["total_adults"].to_numpy(float)); x, _, means, scales = standardize_train_test(x_raw, x_raw)
        alpha = 100.0 if model_id == "all_environment_ridge" else 0.0; coef = fit_linear(x, y, alpha)
        held = pd.read_csv(TABLE_DIR / "phase4_rolling_predictions.csv"); held = held[(held.species == "Coho") & (held.model_id == model_id)]
        salmon_error = held.actual.to_numpy(float) - held.predicted.to_numpy(float)
        for scenario, direction in SCENARIOS.items():
            draws = []
            for _ in range(DRAWS):
                values = {}
                for feature in features:
                    source = env_name.get(feature, feature); last = float(hist[source].iloc[-1]); trend = slopes[feature] * (YEARS - 2025)
                    condition = direction * resid_sd[feature] * 0.5
                    annual_noise = rng.normal(0, resid_sd[feature] * 0.35, len(YEARS))
                    values[feature] = last + trend + condition + annual_noise
                predicted = []
                for i in range(len(YEARS)):
                    row = np.array([(values[f][i] - means[j]) / scales[j] for j, f in enumerate(features)])
                    predicted.append(max(0, float(np.expm1(predict_linear(row[None, :], coef)[0])) + rng.choice(salmon_error)))
                draws.append(predicted)
            draws = np.asarray(draws)
            for i, year in enumerate(YEARS):
                rows.append({"species": "Coho", "model_id": model_id, "scenario": scenario, "year": year, "median_adults": np.quantile(draws[:, i], .5), "lower_90": np.quantile(draws[:, i], .05), "upper_90": np.quantile(draws[:, i], .95), "draws": DRAWS, "input_basis": "Theil-Sen observed trend plus residual variability"})
    result = pd.DataFrame(rows); result.to_csv(TABLE_DIR / "phase6_dynamic_projections.csv", index=False)
    ensemble = result.groupby(["scenario", "year"], as_index=False).agg(median_adults=("median_adults", "median"), lower_90=("lower_90", "median"), upper_90=("upper_90", "median")); ensemble.to_csv(TABLE_DIR / "phase6_dynamic_ensemble.csv", index=False)
    fig, ax = plt.subplots(figsize=(11, 6)); colors = {"higher_input": "#55a868", "trend_only": "#4c72b0", "lower_input": "#c44e52"}
    for scenario in SCENARIOS:
        g = ensemble[ensemble.scenario == scenario]; ax.plot(g.year, g.median_adults, label=scenario, color=colors[scenario]); ax.fill_between(g.year, g.lower_90, g.upper_90, color=colors[scenario], alpha=.12)
    ax.set_title("Dynamic illustrative Coho scenarios (not forecasts)"); ax.set_xlabel("Year"); ax.set_ylabel("Adults"); ax.legend(frameon=False); ax.grid(alpha=.2); fig.tight_layout(); fig.savefig(FIGURE_DIR / "phase6_dynamic_projections.png", dpi=180); plt.close(fig)
    report = """# Dynamic Phase 6 scenario projections

These projections address the flat-line limitation by allowing each environmental input to vary annually. Each path extrapolates its observed 1997–2025 Theil–Sen trend, adds a favorable/central/adverse offset, and adds reproducible year-to-year residual variation. Salmon-return residuals are sampled from held-out Phase 4 errors.

This is an exploratory statistical extrapolation, not an authoritative climate projection or certain forecast. No authoritative future input trajectories were available. PDO remains an external uncertainty, and hatchery releases and imperviousness remain unavailable and implicitly constant. The 90% bands are simulation quantiles, not calibrated prediction intervals.

Outputs: `outputs/tables/phase6_dynamic_projections.csv`, `outputs/tables/phase6_dynamic_ensemble.csv`, and `outputs/figures/phase6_dynamic_projections.png`.
"""
    (ROOT / "docs/phase6_dynamic_report.md").write_text(report, encoding="utf-8"); print(f"Dynamic Phase 6 complete: {len(result)} rows.")
if __name__ == "__main__": main()
