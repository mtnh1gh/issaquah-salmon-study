"""
model.py
Issaquah Creek Salmon Return Study — Summer 2025
------------------------------------------------
XGBoost model training, cross-validation, evaluation,
feature importance, and scenario-based forecasting through 2040.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
from pathlib import Path

from sklearn.model_selection import TimeSeriesSplit, cross_val_score
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
import xgboost as xgb

ROOT = Path(__file__).resolve().parent.parent
FIG_DIR = ROOT / "outputs" / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)

COLORS = {
    "chinook":    "#1F4E79",
    "coho":       "#2E75B6",
    "optimistic": "#375623",
    "baseline":   "#BF8F00",
    "pessimistic":"#C00000",
    "actual":     "#1F4E79",
    "predicted":  "#ED7D31",
}


# ── 1. Train / Test Split ─────────────────────────────────────────────────────

def temporal_split(X: pd.DataFrame, y: pd.Series,
                   train_end_year: int = 2010,
                   year_col: str = "water_year") -> tuple:
    """
    Split data by time: train on 1985–2010, test on 2011–present.
    This respects the temporal structure (no future data leaking into training).
    """
    # Recover water_year from index or column
    if year_col in X.columns:
        years = X[year_col]
        X = X.drop(columns=[year_col])
    else:
        raise ValueError(f"Column '{year_col}' not found in X")

    train_mask = years <= train_end_year
    test_mask  = years > train_end_year

    return (
        X[train_mask], X[test_mask],
        y[train_mask], y[test_mask],
        years[train_mask], years[test_mask],
    )


# ── 2. Baseline Linear Model ──────────────────────────────────────────────────

def train_linear_baseline(X_train, y_train, X_test, y_test) -> dict:
    """
    Ridge regression baseline — interpretable, good sanity check.
    Features are scaled; coefficients indicate relative importance.
    """
    scaler = StandardScaler()
    X_tr_scaled = scaler.fit_transform(X_train)
    X_te_scaled = scaler.transform(X_test)

    model = Ridge(alpha=1.0)
    model.fit(X_tr_scaled, y_train)
    preds = model.predict(X_te_scaled)

    metrics = evaluate_model(y_test, preds, label="Linear Baseline")
    coef_df = pd.DataFrame({
        "feature":     X_train.columns,
        "coefficient": model.coef_,
    }).sort_values("coefficient", key=abs, ascending=False)

    return {"model": model, "scaler": scaler, "metrics": metrics,
            "predictions": preds, "coefficients": coef_df}


# ── 3. XGBoost Model ──────────────────────────────────────────────────────────

XGBOOST_PARAMS = {
    "n_estimators":     300,
    "max_depth":        4,
    "learning_rate":    0.05,
    "subsample":        0.8,
    "colsample_bytree": 0.8,
    "min_child_weight": 3,
    "reg_alpha":        0.1,   # L1 regularization
    "reg_lambda":       1.0,   # L2 regularization
    "random_state":     42,
    "n_jobs":           -1,
}


def train_xgboost(X_train, y_train, X_test, y_test,
                  params: dict = None) -> dict:
    """
    Train XGBoost regressor with time-series cross-validation.

    Time-series CV: never uses future data to predict past.
    5 folds rolling forward across the training window.
    """
    if params is None:
        params = XGBOOST_PARAMS

    model = xgb.XGBRegressor(**params)

    # Time-series cross-validation on training set
    tscv = TimeSeriesSplit(n_splits=5)
    cv_scores = cross_val_score(
        model, X_train, y_train,
        cv=tscv, scoring="r2"
    )
    print(f"  CV R² scores: {cv_scores.round(3)}")
    print(f"  CV R² mean: {cv_scores.mean():.3f} ± {cv_scores.std():.3f}")

    # Final fit on full training set
    model.fit(
        X_train, y_train,
        eval_set=[(X_test, y_test)],
        verbose=False,
    )

    preds = model.predict(X_test)
    metrics = evaluate_model(y_test, preds, label="XGBoost")

    # Feature importance DataFrame
    importance_df = pd.DataFrame({
        "feature":    X_train.columns,
        "importance": model.feature_importances_,
    }).sort_values("importance", ascending=False).reset_index(drop=True)

    return {
        "model":       model,
        "metrics":     metrics,
        "predictions": preds,
        "cv_scores":   cv_scores,
        "importance":  importance_df,
    }


# ── 4. Evaluation Metrics ─────────────────────────────────────────────────────

def evaluate_model(y_true, y_pred, label: str = "") -> dict:
    """Compute MAE, RMSE, and R² — print and return."""
    mae  = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    r2   = r2_score(y_true, y_pred)

    print(f"\n  {label} — Test Set Performance:")
    print(f"    MAE  : {mae:,.0f} fish")
    print(f"    RMSE : {rmse:,.0f} fish")
    print(f"    R²   : {r2:.3f}")

    return {"mae": mae, "rmse": rmse, "r2": r2, "label": label}


# ── 5. Feature Importance Plot ────────────────────────────────────────────────

def plot_feature_importance(importance_df: pd.DataFrame,
                             top_n: int = 15,
                             title: str = "Feature Importance — XGBoost",
                             filename: str = "feature_importance.png") -> None:
    """Horizontal bar chart of top N most important features."""
    top = importance_df.head(top_n).copy()

    # Clean up feature names for display
    name_map = {
        "swe_apr1_in": "April 1 Snowpack (SWE)",
        "swe_anomaly_pct": "Snowpack Anomaly %",
        "pdo_winter_mean": "PDO Winter Index",
        "pdo_lag1_winter": "PDO Index (1-yr lag)",
        "pdo_lag2_winter_mean": "PDO Index (2-yr lag)",
        "min_summer_flow_cfs": "Min Summer Streamflow",
        "days_above_18c": "Days Above 18°C",
        "max_summer_temp_c": "Max Summer Water Temp",
        "impervious_pct": "Impervious Surface %",
        "impervious_5yr_growth": "5-yr Impervious Growth",
        "climate_stress_index": "Climate Stress Index",
        "chinook_smolts_lag4": "Chinook Smolts (4-yr lag)",
        "coho_smolts_lag3": "Coho Smolts (3-yr lag)",
    }
    top["display_name"] = top["feature"].map(name_map).fillna(top["feature"])

    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.barh(
        top["display_name"][::-1],
        top["importance"][::-1],
        color=COLORS["chinook"],
        edgecolor="white",
        linewidth=0.5,
    )
    ax.set_xlabel("Feature Importance Score", fontsize=11)
    ax.set_title(title, fontsize=13, fontweight="bold", pad=12)
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(axis="y", labelsize=10)

    # Annotate values
    for bar, val in zip(bars, top["importance"][::-1]):
        ax.text(val + 0.002, bar.get_y() + bar.get_height() / 2,
                f"{val:.3f}", va="center", fontsize=9, color="#444")

    plt.tight_layout()
    path = FIG_DIR / filename
    plt.savefig(path, dpi=150, bbox_inches="tight")
    print(f"  Saved → {path}")
    plt.show()


# ── 6. Actual vs. Predicted Plot ─────────────────────────────────────────────

def plot_actual_vs_predicted(years_train, y_train, train_preds,
                              years_test,  y_test,  test_preds,
                              species: str = "Chinook",
                              filename: str = "actual_vs_predicted.png") -> None:
    """Time-series chart overlaying actual returns with model predictions."""
    fig, ax = plt.subplots(figsize=(12, 5))

    # Actuals
    ax.plot(list(years_train) + list(years_test),
            list(y_train) + list(y_test),
            color=COLORS["actual"], linewidth=2, label="Actual Returns", zorder=3)

    # Training fit
    ax.plot(years_train, train_preds,
            color=COLORS["predicted"], linewidth=1.5,
            linestyle="--", alpha=0.7, label="Model (Training Fit)")

    # Test predictions
    ax.plot(years_test, test_preds,
            color=COLORS["pessimistic"], linewidth=2,
            linestyle="--", label="Model (Test Predictions)", zorder=4)

    # Train/test boundary
    split_yr = max(years_train)
    ax.axvline(split_yr, color="#999", linestyle=":", linewidth=1.5)
    ax.text(split_yr + 0.3, ax.get_ylim()[1] * 0.95,
            "← Train  |  Test →", fontsize=9, color="#666")

    ax.set_xlabel("Water Year", fontsize=11)
    ax.set_ylabel(f"{species} Returns (fish)", fontsize=11)
    ax.set_title(f"Issaquah Creek {species} Returns — Actual vs. Predicted",
                 fontsize=13, fontweight="bold")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))
    ax.legend(fontsize=10)
    ax.spines[["top", "right"]].set_visible(False)

    plt.tight_layout()
    path = FIG_DIR / filename
    plt.savefig(path, dpi=150, bbox_inches="tight")
    print(f"  Saved → {path}")
    plt.show()


# ── 7. Scenario Projections ───────────────────────────────────────────────────

# Scenario definitions — adjustments relative to 2021–2025 mean conditions
# Tied to realistic Issaquah/Sammamish trajectories
SCENARIOS = {
    "optimistic": {
        "label": "Optimistic\n(Growth slows, stormwater improves)",
        "color": COLORS["optimistic"],
        "description": "Sammamish/Issaquah development slows; stormwater BMPs adopted; snowpack stable",
        "adjustments": {
            "swe_apr1_in":          +5.0,   # inches — snowpack stabilizes
            "swe_anomaly_pct":      +8.0,
            "days_above_18c":        0.0,   # no further warming
            "max_summer_temp_c":     0.0,
            "impervious_pct":       +1.0,   # slow growth (vs. historical +3%)
            "impervious_5yr_growth": +0.2,
            "pdo_winter_mean":      -0.3,   # slight cool-phase bias
        }
    },
    "baseline": {
        "label": "Baseline\n(Current trends continue)",
        "color": COLORS["baseline"],
        "description": "Development and climate continue on current trajectory",
        "adjustments": {
            "swe_apr1_in":          -2.0,   # modest snowpack loss
            "swe_anomaly_pct":      -5.0,
            "days_above_18c":        3.0,   # gradual warming
            "max_summer_temp_c":    +0.3,
            "impervious_pct":       +3.0,   # ~1% per 3 years
            "impervious_5yr_growth": +0.8,
            "pdo_winter_mean":       0.0,
        }
    },
    "pessimistic": {
        "label": "Pessimistic\n(Accelerated development + warming)",
        "color": COLORS["pessimistic"],
        "description": "Rapid Sammamish growth; snowpack -20%; sustained warm-water years",
        "adjustments": {
            "swe_apr1_in":          -12.0,  # ~20% below historical mean
            "swe_anomaly_pct":      -20.0,
            "days_above_18c":        12.0,
            "max_summer_temp_c":    +1.5,
            "impervious_pct":       +6.0,
            "impervious_5yr_growth": +2.0,
            "pdo_winter_mean":      +0.4,   # warm-phase ocean
        }
    },
}


def build_scenario_inputs(last_known_row: pd.Series,
                           model_features: list[str],
                           projection_years: list[int],
                           scenario_name: str) -> pd.DataFrame:
    """
    Build a feature DataFrame for projection years under a given scenario.

    Starts from the last known data point and applies cumulative annual
    adjustments per the scenario definition.

    Parameters
    ----------
    last_known_row  : final row of the training/test feature DataFrame
    model_features  : list of feature column names the model expects
    projection_years: e.g. list(range(2026, 2041))
    scenario_name   : "optimistic", "baseline", or "pessimistic"
    """
    adjustments = SCENARIOS[scenario_name]["adjustments"]
    n_years = len(projection_years)

    rows = []
    current = last_known_row[model_features].copy()

    for i, yr in enumerate(projection_years):
        # Apply cumulative annual delta for each adjusted feature
        row = current.copy()
        for feat, annual_delta in adjustments.items():
            if feat in row.index:
                row[feat] = row[feat] + annual_delta * (i + 1)
        rows.append(row.values)

    return pd.DataFrame(rows, columns=model_features, index=projection_years)


def run_scenario_projections(model,
                              last_known_row: pd.Series,
                              model_features: list[str],
                              projection_years: list[int] = None,
                              species: str = "Chinook") -> dict:
    """
    Generate return projections for all three scenarios.

    Returns dict: scenario_name → pd.Series of projected returns
    """
    if projection_years is None:
        projection_years = list(range(2026, 2041))

    projections = {}
    for name in SCENARIOS:
        X_proj = build_scenario_inputs(
            last_known_row, model_features, projection_years, name
        )
        preds = model.predict(X_proj)
        preds = np.clip(preds, 0, None)   # returns can't be negative
        projections[name] = pd.Series(preds, index=projection_years)
        print(f"  {name}: {preds.mean():,.0f} avg projected {species} returns (2026–2040)")

    return projections


def plot_scenario_projections(historical_years, historical_returns,
                               projections: dict,
                               species: str = "Chinook",
                               filename: str = "scenario_projections.png") -> None:
    """
    Plot historical returns + three scenario projections with uncertainty bands.
    Includes 2025 anchor point and a clean community-readable layout.
    """
    fig, ax = plt.subplots(figsize=(13, 6))

    # Historical line
    ax.plot(historical_years, historical_returns,
            color=COLORS["actual"], linewidth=2.5,
            label="Historical Returns", zorder=5)

    # 2025 anchor dot
    if 2025 in historical_years.values:
        val_2025 = historical_returns[historical_years == 2025].iloc[0]
        ax.scatter([2025], [val_2025], color=COLORS["actual"],
                   s=80, zorder=6, label=f"2025 Actual ({val_2025:,.0f})")

    # Scenario lines
    for name, series in projections.items():
        sc = SCENARIOS[name]
        ax.plot(series.index, series.values,
                color=sc["color"], linewidth=2,
                linestyle="--" if name != "baseline" else "-",
                label=sc["label"], zorder=4)
        # End label
        ax.text(series.index[-1] + 0.3, series.values[-1],
                f"{series.values[-1]:,.0f}",
                color=sc["color"], fontsize=9, va="center")

    # Projection zone shading
    proj_start = min(list(projections.values())[0].index)
    ax.axvspan(proj_start, proj_start + len(list(projections.values())[0]) - 1,
               alpha=0.05, color="#1F4E79", label="Projection Period")
    ax.axvline(proj_start - 0.5, color="#888", linestyle=":", linewidth=1.5)

    ax.set_xlabel("Water Year", fontsize=11)
    ax.set_ylabel(f"{species} Returns (fish)", fontsize=11)
    ax.set_title(
        f"Issaquah Creek {species} Salmon — Historical Returns & 2040 Scenarios\n"
        f"Friends of the Issaquah Salmon Hatchery (FISH) | Summer 2025 Research Project",
        fontsize=12, fontweight="bold"
    )
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))
    ax.legend(loc="upper left", fontsize=9, framealpha=0.9)
    ax.spines[["top", "right"]].set_visible(False)

    plt.tight_layout()
    path = FIG_DIR / filename
    plt.savefig(path, dpi=150, bbox_inches="tight")
    print(f"  Saved → {path}")
    plt.show()
