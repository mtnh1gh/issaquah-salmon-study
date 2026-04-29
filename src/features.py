"""
features.py
Issaquah Creek Salmon Return Study — Summer 2025
------------------------------------------------
Feature engineering: transforms raw merged data into
model-ready features with domain-informed lag structures.

Key insight: salmon returning in year Y spent 1–5 years at sea.
Chinook typically spend 3–5 years at ocean; Coho spend 2–3 years.
So ocean and snowpack conditions 2–4 years prior can matter.
"""

import pandas as pd
import numpy as np


# ── 1. Rolling / Smoothed Returns ─────────────────────────────────────────────

def add_rolling_returns(df: pd.DataFrame, windows: list[int] = [3, 5]) -> pd.DataFrame:
    """
    Add rolling average return counts to smooth interannual noise.
    Also adds percent change from prior year for trend detection.
    """
    df = df.copy()
    for species in ["chinook", "coho"]:
        col = f"{species}_total"
        if col not in df.columns:
            continue
        for w in windows:
            df[f"{species}_roll{w}"] = (
                df[col].rolling(w, min_periods=max(1, w // 2)).mean().round(0)
            )
        df[f"{species}_yoy_pct"] = df[col].pct_change().mul(100).round(1)
    return df


# ── 2. Lag Features ────────────────────────────────────────────────────────────

def add_lag_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Create lagged versions of ocean and climate variables.

    Ecological rationale:
      - PDO lag 1–3: ocean conditions during smolt outmigration years
      - SWE lag 0–1: snowpack affects summer flows in return year AND prior year
      - Water temp lag 1: prior-year summer temps affect juvenile survival
      - Smolt release lag: Chinook released year Y return ~3–5 yrs later,
        Coho ~2–3 yrs later — so release lag 2, 3 are key predictors

    Lag N = value from N years before the return year.
    """
    df = df.copy()

    lag_config = {
        "pdo_winter_mean":   [1, 2, 3],
        "swe_apr1_in":       [0, 1],
        "swe_anomaly_pct":   [0, 1],
        "min_summer_flow_cfs": [0, 1],
        "max_summer_temp_c": [0, 1],
        "days_above_18c":    [0, 1],
        "chinook_smolts":    [3, 4, 5],   # Chinook ocean residence
        "coho_smolts":       [2, 3],      # Coho ocean residence
    }

    for col, lags in lag_config.items():
        if col not in df.columns:
            continue
        for lag in lags:
            if lag == 0:
                continue   # already present as-is
            df[f"{col}_lag{lag}"] = df[col].shift(lag)

    return df


# ── 3. Urban Development Features ────────────────────────────────────────────

def add_urban_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Derive urban stress indicators from impervious surface data.

    - impervious_5yr_growth: cumulative growth over 5 years (captures
      the lag between construction and creek impact)
    - urbanization_era: categorical — pre-2000 (slow growth),
      2000-2012 (Sammamish plateau boom), 2012+ (continued expansion)
    """
    df = df.copy()

    if "impervious_pct" in df.columns:
        df["impervious_5yr_growth"] = df["impervious_pct"].diff(5).round(3)

        # Categorical era for segmented analysis
        df["urbanization_era"] = pd.cut(
            df["water_year"],
            bins=[0, 2000, 2012, 9999],
            labels=["pre_2000", "2000_2012", "post_2012"],
        )

    return df


# ── 4. Climate Stress Index ───────────────────────────────────────────────────

def add_climate_stress_index(df: pd.DataFrame) -> pd.DataFrame:
    """
    Composite climate stress index combining snowpack deficit and
    warm water days into a single normalized signal.

    CSI = 0.5 * (1 - normalized_SWE) + 0.5 * normalized_hot_days
    Higher CSI = worse climate conditions for salmon.
    Range: 0 (good) to 1 (severe stress)
    """
    df = df.copy()

    cols_needed = ["swe_apr1_in", "days_above_18c"]
    if not all(c in df.columns for c in cols_needed):
        return df

    swe_norm = 1 - (
        (df["swe_apr1_in"] - df["swe_apr1_in"].min()) /
        (df["swe_apr1_in"].max() - df["swe_apr1_in"].min())
    )
    hot_norm = (
        (df["days_above_18c"] - df["days_above_18c"].min()) /
        (df["days_above_18c"].max() - df["days_above_18c"].min())
    )
    df["climate_stress_index"] = (0.5 * swe_norm + 0.5 * hot_norm).round(3)
    return df


# ── 5. Smolt-to-Adult Return Ratio ───────────────────────────────────────────

def add_sar_estimates(df: pd.DataFrame) -> pd.DataFrame:
    """
    Estimate Smolt-to-Adult Return (SAR) ratio for each species.

    SAR = adults returning in year Y / smolts released in year Y - lag
    Uses dominant return age: Chinook lag 4, Coho lag 3.

    SAR is a key ecosystem health metric — typical healthy range: 1–4%.
    Below 1% = population stress. Above 4% = excellent conditions.
    """
    df = df.copy()

    if "chinook_total" in df.columns and "chinook_smolts_lag4" in df.columns:
        df["chinook_sar_pct"] = (
            df["chinook_total"] / df["chinook_smolts_lag4"] * 100
        ).round(3)

    if "coho_total" in df.columns and "coho_smolts_lag3" in df.columns:
        df["coho_sar_pct"] = (
            df["coho_total"] / df["coho_smolts_lag3"] * 100
        ).round(3)

    return df


# ── 6. Anomaly Features ───────────────────────────────────────────────────────

def add_anomaly_features(df: pd.DataFrame,
                          baseline_start: int = 1985,
                          baseline_end:   int = 2005) -> pd.DataFrame:
    """
    Express key variables as anomalies (Z-scores) relative to
    the 1985–2005 baseline period.

    This makes it easier to compare magnitude of deviations
    across variables with different units.
    """
    df = df.copy()
    anomaly_cols = [
        "chinook_total", "coho_total",
        "swe_apr1_in", "mean_flow_cfs",
        "mean_water_temp_c", "pdo_winter_mean",
    ]

    base = df[df["water_year"].between(baseline_start, baseline_end)]

    for col in anomaly_cols:
        if col not in df.columns:
            continue
        mu  = base[col].mean()
        sig = base[col].std()
        if sig > 0:
            df[f"{col}_zscore"] = ((df[col] - mu) / sig).round(3)

    return df


# ── 7. Master Feature Builder ─────────────────────────────────────────────────

def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Run all feature engineering steps in the correct order.

    Call this on the output of data_pipeline.build_master_dataset()
    before any statistical analysis or model training.

    Returns a feature-rich DataFrame ready for modeling.
    """
    df = add_rolling_returns(df)
    df = add_lag_features(df)
    df = add_urban_features(df)
    df = add_climate_stress_index(df)
    df = add_sar_estimates(df)
    df = add_anomaly_features(df)

    print(f"Feature engineering complete: {len(df.columns)} total columns")
    print(f"  Rows with complete data: {df.dropna().shape[0]} / {len(df)}")

    return df


def get_model_features(df: pd.DataFrame, target: str = "chinook_total") -> tuple:
    """
    Return X (features) and y (target) ready for scikit-learn / XGBoost.

    Drops rows with NaN in either X or y.
    Excludes return-year variables that would cause data leakage.

    Parameters
    ----------
    target : "chinook_total" or "coho_total"

    Returns
    -------
    X : pd.DataFrame of predictor features
    y : pd.Series of target values
    feature_names : list of column names used
    """
    # Columns to exclude from features (target leakage or non-predictive)
    exclude = [
        "chinook_total", "coho_total",
        "chinook_wild",  "coho_wild",
        "chinook_roll3", "chinook_roll5",
        "coho_roll3",    "coho_roll5",
        "chinook_yoy_pct", "coho_yoy_pct",
        "chinook_sar_pct", "coho_sar_pct",
        "urbanization_era",   # categorical — encode separately if needed
        "water_year",         # not a causal predictor
    ]

    feature_cols = [
        c for c in df.columns
        if c not in exclude and c != target
        and pd.api.types.is_numeric_dtype(df[c])
    ]

    model_df = df[feature_cols + [target]].dropna()
    X = model_df[feature_cols]
    y = model_df[target]

    return X, y, feature_cols
