"""Phase 4 interpretable association models with rolling-origin validation."""

from __future__ import annotations

import hashlib
import os
import platform
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".matplotlib-cache"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scipy
from scipy import stats


MASTER_PATH = ROOT / "data/gold/issaquah_creek_master.csv"
ENV_PATH = ROOT / "data/silver/issaquah_annual_environment.csv"
TABLE_DIR = ROOT / "outputs/tables"
FIGURE_DIR = ROOT / "outputs/figures"
REPORT_PATH = ROOT / "docs/statistical_analysis_report.md"
MIN_TRAIN_YEARS = 12
ALPHAS = (0.1, 1.0, 10.0, 100.0)

MODEL_FEATURES = {
    "migration_marine_ols": [
        "flow_jul_sep_mean_cfs",
        "temp_jun_sep_mean_c",
        "marine_pdo_mean",
    ],
    "freshwater_marine_ols": [
        "cohort_flow_water_year_mean_cfs",
        "cohort_swe_apr01_inches",
        "marine_pdo_mean",
    ],
    "all_environment_ridge": [
        "flow_jul_sep_mean_cfs",
        "temp_jun_sep_mean_c",
        "cohort_flow_water_year_mean_cfs",
        "cohort_swe_apr01_inches",
        "marine_pdo_mean",
    ],
}

LABELS = {
    "flow_jul_sep_mean_cfs": "Adult migration flow",
    "temp_jun_sep_mean_c": "Adult migration temperature",
    "cohort_flow_water_year_mean_cfs": "Cohort-year flow",
    "cohort_swe_apr01_inches": "Cohort-year April 1 SWE",
    "marine_pdo_mean": "Marine-window PDO",
}


def standardize_train_test(
    train: np.ndarray, test: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    mean = train.mean(axis=0)
    scale = train.std(axis=0, ddof=0)
    scale[scale == 0] = 1.0
    return (train - mean) / scale, (test - mean) / scale, mean, scale


def fit_linear(x: np.ndarray, y: np.ndarray, alpha: float = 0.0) -> np.ndarray:
    design = np.column_stack([np.ones(len(x)), x])
    penalty = np.eye(design.shape[1]) * alpha
    penalty[0, 0] = 0.0
    return np.linalg.pinv(design.T @ design + penalty) @ design.T @ y


def predict_linear(x: np.ndarray, coefficients: np.ndarray) -> np.ndarray:
    return np.column_stack([np.ones(len(x)), x]) @ coefficients


def metrics(actual: np.ndarray, predicted: np.ndarray) -> dict[str, float]:
    errors = actual - predicted
    denominator = np.sum((actual - actual.mean()) ** 2)
    return {
        "mae": float(np.mean(np.abs(errors))),
        "rmse": float(np.sqrt(np.mean(errors**2))),
        "r2": float(1 - np.sum(errors**2) / denominator),
    }


def inner_select_alpha(x: np.ndarray, y: np.ndarray) -> float:
    """Select ridge alpha using only the current outer training window."""
    if len(y) < 9:
        return 10.0
    start = max(6, len(y) - 6)
    scores: dict[float, list[float]] = {alpha: [] for alpha in ALPHAS}
    for test_index in range(start, len(y)):
        x_train, x_test = x[:test_index], x[test_index : test_index + 1]
        y_train = y[:test_index]
        x_train_z, x_test_z, _, _ = standardize_train_test(x_train, x_test)
        for alpha in ALPHAS:
            coef = fit_linear(x_train_z, np.log1p(y_train), alpha)
            prediction = np.expm1(predict_linear(x_test_z, coef))[0]
            scores[alpha].append(abs(y[test_index] - max(0.0, prediction)))
    return min(ALPHAS, key=lambda alpha: (np.mean(scores[alpha]), alpha))


def rolling_predictions(master: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for species, group in master.groupby("species", sort=True):
        data = group.sort_values("return_year").reset_index(drop=True)
        for test_index in range(MIN_TRAIN_YEARS, len(data)):
            train = data.iloc[:test_index]
            test = data.iloc[test_index : test_index + 1]
            actual = float(test["total_adults"].iloc[0])
            common = {
                "species": species,
                "test_year": int(test["return_year"].iloc[0]),
                "train_start_year": int(train["return_year"].iloc[0]),
                "train_end_year": int(train["return_year"].iloc[-1]),
                "n_train": len(train),
                "actual": actual,
            }
            rows.append(
                {
                    **common,
                    "model_id": "expanding_mean",
                    "alpha": np.nan,
                    "predicted": float(train["total_adults"].mean()),
                }
            )
            rows.append(
                {
                    **common,
                    "model_id": "previous_year",
                    "alpha": np.nan,
                    "predicted": float(train["total_adults"].iloc[-1]),
                }
            )
            for model_id, features in MODEL_FEATURES.items():
                x_train = train[features].to_numpy(float)
                x_test = test[features].to_numpy(float)
                x_train_z, x_test_z, _, _ = standardize_train_test(x_train, x_test)
                alpha = (
                    inner_select_alpha(
                        data.loc[: test_index - 1, features].to_numpy(float),
                        train["total_adults"].to_numpy(float),
                    )
                    if model_id == "all_environment_ridge"
                    else 0.0
                )
                coefficients = fit_linear(
                    x_train_z, np.log1p(train["total_adults"].to_numpy(float)), alpha
                )
                predicted = np.expm1(predict_linear(x_test_z, coefficients))[0]
                rows.append(
                    {
                        **common,
                        "model_id": model_id,
                        "alpha": alpha,
                        "predicted": max(0.0, float(predicted)),
                    }
                )
    return pd.DataFrame(rows)


def summarize_validation(predictions: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (species, model_id), group in predictions.groupby(
        ["species", "model_id"], sort=True
    ):
        result = metrics(group["actual"].to_numpy(), group["predicted"].to_numpy())
        rows.append(
            {
                "species": species,
                "model_id": model_id,
                "n_test_years": len(group),
                "test_start_year": int(group["test_year"].min()),
                "test_end_year": int(group["test_year"].max()),
                **result,
            }
        )
    result = pd.DataFrame(rows)
    baseline = (
        result[result["model_id"].isin(["expanding_mean", "previous_year"])]
        .groupby("species")[["mae", "rmse"]]
        .min()
        .rename(columns={"mae": "best_baseline_mae", "rmse": "best_baseline_rmse"})
    )
    result = result.merge(baseline, on="species")
    result["beats_best_baseline_mae"] = result["mae"] < result["best_baseline_mae"]
    result["beats_best_baseline_rmse"] = result["rmse"] < result["best_baseline_rmse"]
    result["scenario_eligible"] = (
        ~result["model_id"].isin(["expanding_mean", "previous_year"])
        & result["beats_best_baseline_mae"]
        & result["beats_best_baseline_rmse"]
    )
    return result


def vif_values(x: np.ndarray) -> np.ndarray:
    correlation = np.corrcoef(x, rowvar=False)
    return np.diag(np.linalg.pinv(correlation))


def final_model_tables(
    master: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    coefficient_rows: list[dict[str, object]] = []
    diagnostic_rows: list[dict[str, object]] = []
    for species, group in master.groupby("species", sort=True):
        data = group.sort_values("return_year")
        y = np.log1p(data["total_adults"].to_numpy(float))
        for model_id, features in MODEL_FEATURES.items():
            x_raw = data[features].to_numpy(float)
            x, _, means, scales = standardize_train_test(x_raw, x_raw)
            alpha = inner_select_alpha(x_raw, data["total_adults"].to_numpy(float)) if model_id == "all_environment_ridge" else 0.0
            coefficients = fit_linear(x, y, alpha)
            fitted = predict_linear(x, coefficients)
            residuals = y - fitted
            design = np.column_stack([np.ones(len(x)), x])
            hat = design @ np.linalg.pinv(design.T @ design + np.diag([0.0] + [alpha] * len(features))) @ design.T
            leverage = np.clip(np.diag(hat), 0, 0.999999)
            mse = np.sum(residuals**2) / max(1, len(y) - len(features) - 1)
            cooks = (residuals**2 / ((len(features) + 1) * mse)) * (
                leverage / (1 - leverage) ** 2
            )
            shapiro = stats.shapiro(residuals)
            durbin_watson = np.sum(np.diff(residuals) ** 2) / np.sum(residuals**2)
            vifs = vif_values(x_raw)
            diagnostic_rows.append(
                {
                    "species": species,
                    "model_id": model_id,
                    "n": len(data),
                    "parameters_including_intercept": len(features) + 1,
                    "alpha": alpha,
                    "residual_shapiro_w": shapiro.statistic,
                    "residual_shapiro_p": shapiro.pvalue,
                    "durbin_watson": durbin_watson,
                    "max_cooks_distance": cooks.max(),
                    "max_cooks_year": int(
                        data.iloc[int(np.argmax(cooks))]["return_year"]
                    ),
                    "max_vif": vifs.max(),
                }
            )
            for feature, coefficient, mean, scale, vif in zip(
                features, coefficients[1:], means, scales, vifs
            ):
                coefficient_rows.append(
                    {
                        "species": species,
                        "model_id": model_id,
                        "feature": feature,
                        "standardized_log_coefficient": coefficient,
                        "multiplicative_change_per_1sd": np.exp(coefficient),
                        "training_mean": mean,
                        "training_sd": scale,
                        "vif": vif,
                        "alpha": alpha,
                    }
                )
    return pd.DataFrame(coefficient_rows), pd.DataFrame(diagnostic_rows)


def influence_sensitivity(
    master: pd.DataFrame, coefficients: pd.DataFrame, diagnostics: pd.DataFrame
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for diagnostic in diagnostics.itertuples():
        features = MODEL_FEATURES[diagnostic.model_id]
        data = master[
            (master["species"] == diagnostic.species)
            & (master["return_year"] != diagnostic.max_cooks_year)
        ].sort_values("return_year")
        x_raw = data[features].to_numpy(float)
        x, _, _, _ = standardize_train_test(x_raw, x_raw)
        y = np.log1p(data["total_adults"].to_numpy(float))
        alpha = (
            inner_select_alpha(x_raw, data["total_adults"].to_numpy(float))
            if diagnostic.model_id == "all_environment_ridge"
            else 0.0
        )
        reduced = fit_linear(x, y, alpha)[1:]
        full = coefficients[
            (coefficients["species"] == diagnostic.species)
            & (coefficients["model_id"] == diagnostic.model_id)
        ].set_index("feature")
        for feature, estimate in zip(features, reduced):
            original = float(full.at[feature, "standardized_log_coefficient"])
            rows.append(
                {
                    "species": diagnostic.species,
                    "model_id": diagnostic.model_id,
                    "excluded_year": diagnostic.max_cooks_year,
                    "feature": feature,
                    "full_coefficient": original,
                    "excluded_year_coefficient": estimate,
                    "absolute_change": abs(estimate - original),
                    "sign_changed": bool(np.sign(estimate) != np.sign(original)),
                }
            )
    return pd.DataFrame(rows)


def chinook_lag_sensitivity(master: pd.DataFrame, env: pd.DataFrame) -> pd.DataFrame:
    """Repeat the freshwater/marine model at the locked Chinook lag alternatives."""
    chinook = master[master["species"] == "Chinook"].sort_values("return_year").copy()
    env_lookup = env.set_index("return_year")
    rows: list[dict[str, object]] = []
    for lag in (3, 4, 5):
        data = chinook.copy()
        data["lag_flow"] = data["return_year"].map(
            lambda year: env_lookup.at[year - lag, "flow_water_year_mean_cfs"]
        )
        data["lag_swe"] = data["return_year"].map(
            lambda year: env_lookup.at[year - lag, "swe_apr01_inches"]
        )
        data["lag_pdo"] = data["return_year"].map(
            lambda year: env_lookup.loc[
                year - lag + 1 : year - 1, "pdo_annual_mean"
            ].mean()
        )
        prediction_rows = []
        for test_index in range(MIN_TRAIN_YEARS, len(data)):
            train = data.iloc[:test_index]
            test = data.iloc[test_index : test_index + 1]
            features = ["lag_flow", "lag_swe", "lag_pdo"]
            x_train, x_test, _, _ = standardize_train_test(
                train[features].to_numpy(float), test[features].to_numpy(float)
            )
            coef = fit_linear(
                x_train, np.log1p(train["total_adults"].to_numpy(float))
            )
            prediction_rows.append(
                {
                    "actual": float(test["total_adults"].iloc[0]),
                    "predicted": max(
                        0.0, float(np.expm1(predict_linear(x_test, coef))[0])
                    ),
                }
            )
        values = pd.DataFrame(prediction_rows)
        result = metrics(values["actual"].to_numpy(), values["predicted"].to_numpy())
        rows.append(
            {
                "species": "Chinook",
                "model_id": "freshwater_marine_ols",
                "lag_years": lag,
                "is_primary_lag": lag == 4,
                "n_test_years": len(values),
                **result,
            }
        )
    return pd.DataFrame(rows)


def plot_validation(predictions: pd.DataFrame, summary: pd.DataFrame) -> None:
    candidates = summary[
        ~summary["model_id"].isin(["expanding_mean", "previous_year"])
    ].sort_values(["species", "rmse"])
    best_ids = candidates.groupby("species").first()["model_id"].to_dict()
    fig, axes = plt.subplots(2, 1, figsize=(11, 8), sharex=True)
    colors = {"Chinook": "#c44e52", "Coho": "#4c72b0"}
    for axis, species in zip(axes, ["Chinook", "Coho"]):
        model_id = best_ids[species]
        selected = predictions[
            (predictions["species"] == species)
            & (predictions["model_id"] == model_id)
        ]
        baseline = predictions[
            (predictions["species"] == species)
            & (predictions["model_id"] == "expanding_mean")
        ]
        axis.plot(selected["test_year"], selected["actual"], marker="o", color="black", label="Observed")
        axis.plot(selected["test_year"], selected["predicted"], marker="o", color=colors[species], label=model_id)
        axis.plot(baseline["test_year"], baseline["predicted"], linestyle="--", color="#777777", label="Expanding mean")
        axis.set_title(species)
        axis.set_ylabel("Total adults")
        axis.grid(alpha=0.2)
        axis.legend(frameon=False, ncol=3)
    axes[-1].set_xlabel("Rolling-origin test year")
    fig.suptitle("Time-aware validation: best candidate by RMSE")
    fig.tight_layout()
    fig.savefig(FIGURE_DIR / "phase4_rolling_predictions.png", dpi=180)
    plt.close(fig)

    display = summary.copy()
    display["label"] = display["species"] + ": " + display["model_id"]
    display = display.sort_values(["species", "rmse"])
    fig, axis = plt.subplots(figsize=(10, 6))
    colors = ["#4c72b0" if value else "#aaaaaa" for value in display["scenario_eligible"]]
    axis.barh(display["label"], display["rmse"], color=colors)
    axis.invert_yaxis()
    axis.set_xlabel("Rolling-origin RMSE (adults)")
    axis.set_title("Validation error; blue requires improvement on both baseline metrics")
    axis.grid(axis="x", alpha=0.2)
    fig.tight_layout()
    fig.savefig(FIGURE_DIR / "phase4_model_comparison.png", dpi=180)
    plt.close(fig)


def write_report(
    summary: pd.DataFrame,
    coefficients: pd.DataFrame,
    diagnostics: pd.DataFrame,
    influence: pd.DataFrame,
    lag_sensitivity: pd.DataFrame,
) -> None:
    lines = [
        "# Statistical analysis report",
        "",
        "Phase: 4",
        "",
        "Response: `log1p(total_adults)` for fitted association models; validation errors are reported in adult-count units.",
        "",
        "The models estimate observational associations, not causal effects. Imperviousness and releases remain excluded because observed values are unavailable.",
        "",
        "## Time-aware validation",
        "",
        f"Each species has {29 - MIN_TRAIN_YEARS} rolling-origin test years (2009-2025). Every fold trains only on preceding years. Scaling is fitted inside each fold; the five-feature ridge alpha is selected inside each outer training window.",
        "",
        "| Species | Model | MAE | RMSE | R-squared | Beats best baseline MAE | Beats best baseline RMSE | Scenario eligible |",
        "|---|---|---:|---:|---:|---|---|---|",
    ]
    for row in summary.sort_values(["species", "rmse"]).itertuples():
        lines.append(
            f"| {row.species} | `{row.model_id}` | {row.mae:.0f} | {row.rmse:.0f} | "
            f"{row.r2:.3f} | {row.beats_best_baseline_mae} | "
            f"{row.beats_best_baseline_rmse} | {row.scenario_eligible} |"
        )
    lines += [
        "",
        "A candidate is scenario-eligible only if it improves both MAE and RMSE over the best corresponding naive baseline. Negative validation R-squared means predictions are worse than predicting the test-period mean and is retained as an honest feasibility result.",
        "",
        "## Full-period standardized associations",
        "",
        "Coefficients below are multiplicative changes in the fitted median count per one training-period standard deviation, holding the other predictors in that model constant. They are descriptive full-period estimates and are not selected by statistical significance.",
        "",
        "| Species | Model | Strongest standardized association | Multiplier per 1 SD |",
        "|---|---|---|---:|",
    ]
    strongest = coefficients.loc[
        coefficients.groupby(["species", "model_id"])[
            "standardized_log_coefficient"
        ].apply(lambda values: values.abs().idxmax())
    ]
    for row in strongest.sort_values(["species", "model_id"]).itertuples():
        lines.append(
            f"| {row.species} | `{row.model_id}` | {LABELS[row.feature]} "
            f"({row.standardized_log_coefficient:+.3f} log units) | "
            f"{row.multiplicative_change_per_1sd:.3f}x |"
        )
    lines += [
        "",
        "## Diagnostics",
        "",
        "| Species | Model | Alpha | Shapiro p | Durbin-Watson | Max Cook's D (year) | Max VIF |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for row in diagnostics.sort_values(["species", "model_id"]).itertuples():
        lines.append(
            f"| {row.species} | `{row.model_id}` | {row.alpha:.1f} | "
            f"{row.residual_shapiro_p:.3f} | {row.durbin_watson:.3f} | "
            f"{row.max_cooks_distance:.3f} ({row.max_cooks_year}) | {row.max_vif:.2f} |"
        )
    lines += [
        "",
        "Cook's distance is a screening diagnostic; years exceeding roughly `4/n` warrant sensitivity review. Ridge leverage/Cook values are approximate. VIF describes predictor collinearity, not model validity.",
        "",
        f"Excluding each model's highest-Cook's-distance year caused {int(influence['sign_changed'].sum())} coefficient sign changes across {len(influence)} coefficients. Detailed estimates are in `outputs/tables/phase4_influence_sensitivity.csv`.",
        "",
        "## Chinook lag sensitivity",
        "",
        "| Cohort lag | Primary | MAE | RMSE | R-squared |",
        "|---:|---|---:|---:|---:|",
    ]
    for row in lag_sensitivity.itertuples():
        lines.append(
            f"| {row.lag_years} | {row.is_primary_lag} | {row.mae:.0f} | "
            f"{row.rmse:.0f} | {row.r2:.3f} |"
        )
    lines += [
        "",
        "Lag sensitivity is evaluated with the same rolling-origin design. Material error differences reinforce that the Chinook cohort alignment is uncertain rather than a tuned biological fact.",
        "",
        "## Interpretation limits",
        "",
        "- Twenty-nine annual observations per species sharply limit model complexity and validation precision.",
        "- Hatchery production is an unmeasured confounder because actual release records remain blocked.",
        "- Land-use association cannot be estimated without the imperviousness series.",
        "- Same-year temperature is a sparse grab-sample index, not continuous thermal exposure.",
        "- Cohort lags are biological proxies; the Phase 3 Chinook flow association was unstable at lags 3-5.",
        "- No model should be used for 2040 scenarios unless it passes the stated baseline gate and Phase 5 uncertainty review.",
        "",
        "## Reproduction",
        "",
        "```powershell",
        r".\.venv\Scripts\python.exe .\src\run_phase4_models.py",
        r".\.venv\Scripts\python.exe .\src\validate_phase4.py",
        "```",
        "",
        f"Runtime: Python {platform.python_version()}, pandas {pd.__version__}, NumPy {np.__version__}, SciPy {scipy.__version__}, Matplotlib {matplotlib.__version__}.",
    ]
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_registry(summary: pd.DataFrame, diagnostics: pd.DataFrame) -> None:
    master_hash = hashlib.sha256(MASTER_PATH.read_bytes()).hexdigest().upper()
    lines = [
        "# Model registry",
        "",
        "See `docs/model_summary.md` for a plain-language explanation of these models, the validation design, and how they feed the Phase 5/6 uncertainty and scenario work.",
        "",
        "Phase 4 experiments generated 2026-07-27.",
        "",
        f"Data-version ID: `issaquah_creek_master.csv`; SHA-256 `{master_hash}`.",
        "",
        "Feature-registry version: `docs/feature_registry.csv` at the Phase 4 commit.",
        "",
    ]
    for row in summary.sort_values(["species", "model_id"]).itertuples():
        diagnostic = diagnostics[
            (diagnostics["species"] == row.species)
            & (diagnostics["model_id"] == row.model_id)
        ]
        lines += [
            f"## P4-{row.species.upper()}-{row.model_id.upper()}",
            "",
            f"- Species/response: {row.species}; annual `total_adults`.",
            "- Training years: expanding windows beginning 1997; final full-period fit 1997-2025.",
            f"- Validation folds: {row.n_test_years} rolling-origin tests, {row.test_start_year}-{row.test_end_year}.",
            "- Preprocessing: predictor standardization fitted separately inside each training fold; modeled response uses `log1p` for association candidates.",
            f"- Algorithm/hyperparameters: `{row.model_id}`"
            + (
                "; ridge alpha selected within each outer training window from 0.1, 1, 10, 100."
                if row.model_id == "all_environment_ridge"
                else "."
            ),
            "- Random seed: not applicable; deterministic fitting.",
            "- Naive comparators: expanding-window historical mean and previous-year persistence.",
            f"- MAE: {row.mae:.3f}; RMSE: {row.rmse:.3f}; validation R-squared: {row.r2:.4f}.",
            "- Uncertainty method: rolling-origin out-of-sample error distribution; no forecast interval approved in Phase 4.",
            (
                f"- Residual/influence diagnostics: Shapiro p={diagnostic.iloc[0]['residual_shapiro_p']:.3f}; "
                f"Durbin-Watson={diagnostic.iloc[0]['durbin_watson']:.3f}; "
                f"maximum Cook's D={diagnostic.iloc[0]['max_cooks_distance']:.3f}."
                if not diagnostic.empty
                else "- Residual/influence diagnostics: not applicable to naive baseline."
            ),
            "- Lag sensitivity: Coho lag 2 primary; Chinook lag 4 primary, with Phase 3 lags 3/5 sensitivity showing unstable cohort-flow association.",
            f"- Scenario eligible: {'yes' if row.scenario_eligible else 'no'}.",
            f"- Decision: {'retain' if row.scenario_eligible else 'reject' if row.model_id not in ['expanding_mean', 'previous_year'] else 'comparator'}.",
            "- Git commit: generated before commit; commit identifier is the repository history containing this registry.",
            "",
        ]
    (ROOT / "docs/model_registry.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    master = pd.read_csv(MASTER_PATH)
    env = pd.read_csv(ENV_PATH)
    predictions = rolling_predictions(master)
    summary = summarize_validation(predictions)
    coefficients, diagnostics = final_model_tables(master)
    influence = influence_sensitivity(master, coefficients, diagnostics)
    lag_sensitivity = chinook_lag_sensitivity(master, env)

    predictions.to_csv(TABLE_DIR / "phase4_rolling_predictions.csv", index=False)
    summary.to_csv(TABLE_DIR / "phase4_model_validation.csv", index=False)
    coefficients.to_csv(TABLE_DIR / "phase4_coefficients.csv", index=False)
    diagnostics.to_csv(TABLE_DIR / "phase4_diagnostics.csv", index=False)
    influence.to_csv(TABLE_DIR / "phase4_influence_sensitivity.csv", index=False)
    lag_sensitivity.to_csv(TABLE_DIR / "phase4_chinook_lag_sensitivity.csv", index=False)
    plot_validation(predictions, summary)
    write_report(summary, coefficients, diagnostics, influence, lag_sensitivity)
    write_registry(summary, diagnostics)
    print(
        f"Phase 4 complete: {len(summary)} experiments, "
        f"{int(summary['scenario_eligible'].sum())} scenario-eligible candidates."
    )


if __name__ == "__main__":
    main()
