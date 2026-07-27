"""Phase 5 uncertainty review for retained Coho candidates."""
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
TABLE_DIR = ROOT / "outputs/tables"
FIGURE_DIR = ROOT / "outputs/figures"
SEED = 20260727
BOOTSTRAPS = 5000

def main() -> None:
    validation = pd.read_csv(TABLE_DIR / "phase4_model_validation.csv")
    predictions = pd.read_csv(TABLE_DIR / "phase4_rolling_predictions.csv")
    retained = validation[(validation["scenario_eligible"]) & (validation["species"] == "Coho")]
    rng = np.random.default_rng(SEED)
    rows, interval_rows = [], []
    for candidate in retained.itertuples():
        group = predictions[(predictions["species"] == candidate.species) & (predictions["model_id"] == candidate.model_id)].sort_values("test_year")
        actual = group["actual"].to_numpy(float); predicted = group["predicted"].to_numpy(float)
        errors = actual - predicted
        boot_mae, boot_rmse = [], []
        for _ in range(BOOTSTRAPS):
            sample = rng.choice(errors, size=len(errors), replace=True)
            boot_mae.append(np.mean(np.abs(sample))); boot_rmse.append(np.sqrt(np.mean(sample**2)))
        rows.append({"species": candidate.species, "model_id": candidate.model_id, "n_validation_years": len(group), "observed_mae": np.mean(np.abs(errors)), "mae_ci_low": np.quantile(boot_mae, .025), "mae_ci_high": np.quantile(boot_mae, .975), "observed_rmse": np.sqrt(np.mean(errors**2)), "rmse_ci_low": np.quantile(boot_rmse, .025), "rmse_ci_high": np.quantile(boot_rmse, .975), "bootstrap_seed": SEED, "bootstrap_repetitions": BOOTSTRAPS})
        low, high = np.quantile(errors, [.025, .975])
        lower = np.maximum(0, predicted + low); upper = np.maximum(lower, predicted + high)
        for year, pred, lo, hi, obs in zip(group["test_year"], predicted, lower, upper, actual):
            interval_rows.append({"species": candidate.species, "model_id": candidate.model_id, "test_year": year, "predicted": pred, "lower_95_empirical": lo, "upper_95_empirical": hi, "actual": obs, "covered": lo <= obs <= hi})
    uncertainty = pd.DataFrame(rows); intervals = pd.DataFrame(interval_rows)
    uncertainty.to_csv(TABLE_DIR / "phase5_uncertainty.csv", index=False); intervals.to_csv(TABLE_DIR / "phase5_prediction_intervals.csv", index=False)
    coverage = intervals.groupby("model_id")["covered"].mean()
    display = uncertainty.sort_values("observed_rmse")
    fig, axis = plt.subplots(figsize=(9, 5)); labels = display["model_id"].str.replace("_", " ")
    axis.errorbar(display["observed_rmse"], labels, xerr=[display["observed_rmse"]-display["rmse_ci_low"], display["rmse_ci_high"]-display["observed_rmse"]], fmt="o", color="#4c72b0", capsize=4)
    axis.set_xlabel("Rolling-origin RMSE (adults), bootstrap 95% interval"); axis.set_title("Phase 5 uncertainty for retained Coho candidates"); axis.grid(axis="x", alpha=.2); fig.tight_layout(); fig.savefig(FIGURE_DIR / "phase5_uncertainty.png", dpi=180); plt.close(fig)
    lines = ["# Phase 5 uncertainty review", "", "Status: completed; no final scenario model approved.", "", "The three Coho candidates that passed the Phase 4 baseline gate were reviewed with paired bootstrap resampling of the 17 rolling-origin errors. These intervals describe validation uncertainty; they are not causal confidence intervals.", "", "| Model | MAE | Bootstrap 95% CI | RMSE | Bootstrap 95% CI | Interval coverage |", "|---|---:|---:|---:|---:|---:|"]
    for row in display.itertuples():
        lines.append(f"| `{row.model_id}` | {row.observed_mae:.0f} | [{row.mae_ci_low:.0f}, {row.mae_ci_high:.0f}] | {row.observed_rmse:.0f} | [{row.rmse_ci_low:.0f}, {row.rmse_ci_high:.0f}] | {coverage[row.model_id]:.1%} |")
    lines += ["", "Empirical intervals use held-out residual quantiles and are descriptive only. With 17 test years, coverage is too imprecise to certify nominal 95% calibration.", "", "PDO is not treated as a controllable intervention; hatchery releases and imperviousness remain unavailable. Phase 6 may construct only explicitly illustrative, cited trajectories.", "", "Reproduction: `python src/run_phase5_uncertainty.py`; `python src/validate_phase5.py`", ""]
    (ROOT / "docs/phase5_uncertainty_report.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Phase 5 uncertainty complete: {len(uncertainty)} retained candidates.")

if __name__ == "__main__": main()
