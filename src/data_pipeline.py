"""
data_pipeline.py
Issaquah Creek Salmon Return Study — Summer 2025
------------------------------------------------
Functions to load, validate, and merge all data sources into
a single master DataFrame indexed by water year (Oct–Sep).

Water year convention: WY 2000 = Oct 1999 – Sep 2000
(USGS / NRCS standard for Pacific Northwest hydrology)
"""

import pandas as pd
import numpy as np
import requests
import dataretrieval.nwis as nwis
from pathlib import Path
from datetime import datetime

# ── Paths ────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

# ── Constants ────────────────────────────────────────────────────────────────
START_YEAR = 1985          # First reliable WDFW escapement year for Issaquah
END_YEAR   = 2025          # Most recent complete data year
STUDY_YEARS = list(range(START_YEAR, END_YEAR + 1))

# USGS stream gauge on Issaquah Creek at Issaquah, WA
USGS_GAUGE = "12121600"

# NRCS SNOTEL stations closest to Issaquah Creek watershed
SNOTEL_STATIONS = {
    "stampede_pass": "769",
    "snoqualmie_pass": "781",
}

# 2025 baseline — from FISH annual report
BASELINE_2025 = {
    "chinook_total_return": 4955,
    "chinook_natural_spawners": 134,
    "coho_total_return": 5200,       # 5,200+ — use as floor
    "coho_natural_spawners": 1438,   # 1,438+ — use as floor
    "chinook_smolts_released": 3_500_000,
    "coho_smolts_released": 1_000_000,
}


# ── 1. WDFW Salmon Escapement ─────────────────────────────────────────────────

def load_wdfw_escapement(filepath: str | Path) -> pd.DataFrame:
    """
    Load WDFW escapement (return) data for Issaquah Creek.

    Expected CSV columns (WDFW standard export):
        Year, Species, Stream, Wild_Adults, Hatchery_Adults, Jacks, Total_Return

    Download from:
        https://wdfw.wa.gov/fishing/salmon-science-management
        → Salmonid Stock Inventory (SaSI) → Escapement database
        Filter: Stream = "Issaquah Creek"

    Returns
    -------
    pd.DataFrame with columns:
        water_year, chinook_total, chinook_wild, coho_total, coho_wild
    """
    df = pd.read_csv(filepath)
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")

    # Pivot: one row per year with Chinook and Coho columns
    chinook = df[df["species"].str.lower().str.contains("chinook|king")].copy()
    coho    = df[df["species"].str.lower().str.contains("coho|silver")].copy()

    def agg_species(sdf, prefix):
        sdf = sdf.groupby("year").agg(
            total_return=("total_return", "sum"),
            wild_adults=("wild_adults",  "sum"),
        ).reset_index()
        sdf.columns = ["water_year", f"{prefix}_total", f"{prefix}_wild"]
        return sdf

    merged = agg_species(chinook, "chinook").merge(
        agg_species(coho, "coho"), on="water_year", how="outer"
    )
    merged = merged[merged["water_year"].between(START_YEAR, END_YEAR)]
    return merged.sort_values("water_year").reset_index(drop=True)


def load_fish_hatchery_releases(filepath: str | Path) -> pd.DataFrame:
    """
    Load FISH hatchery smolt release records.

    Expected CSV columns:
        Year, Species, Smolts_Released, Avg_Weight_g, Release_Date

    Can also be sourced from RMIS:
        https://rmis.psmfc.org  → Release data → Hatchery = Issaquah

    Returns
    -------
    pd.DataFrame with columns:
        water_year, chinook_smolts, coho_smolts
    """
    df = pd.read_csv(filepath)
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")

    chinook = df[df["species"].str.lower().str.contains("chinook|king")]
    coho    = df[df["species"].str.lower().str.contains("coho|silver")]

    result = pd.DataFrame({"water_year": STUDY_YEARS})
    result = result.merge(
        chinook.rename(columns={"year": "water_year", "smolts_released": "chinook_smolts"})[["water_year", "chinook_smolts"]],
        on="water_year", how="left"
    ).merge(
        coho.rename(columns={"year": "water_year", "smolts_released": "coho_smolts"})[["water_year", "coho_smolts"]],
        on="water_year", how="left"
    )
    return result


# ── 2. USGS Streamflow & Water Temperature ───────────────────────────────────

def fetch_usgs_annual(start_year: int = START_YEAR,
                      end_year: int   = END_YEAR) -> pd.DataFrame:
    """
    Pull mean daily discharge (cfs) and water temperature (°C)
    from USGS gauge 12121600 — Issaquah Creek at Issaquah, WA.

    Uses the dataretrieval library (USGS NWIS API wrapper).
    Parameters:
        00060 = discharge (cfs)
        00010 = water temperature (°C)

    Returns
    -------
    pd.DataFrame with columns:
        water_year, mean_flow_cfs, min_summer_flow_cfs,
        mean_water_temp_c, max_summer_temp_c, days_above_18c
    """
    print(f"  Fetching USGS gauge {USGS_GAUGE}...")
    df, _ = nwis.get_dv(
        sites=USGS_GAUGE,
        parameterCd=["00060", "00010"],
        start=f"{start_year - 1}-10-01",   # start of first water year
        end=f"{end_year}-09-30",
    )

    df = df.reset_index()
    df["date"] = pd.to_datetime(df["datetime"])

    # Assign water year: Oct–Sep, so Oct–Dec of calendar year Y → water year Y+1
    df["water_year"] = df["date"].apply(
        lambda d: d.year + 1 if d.month >= 10 else d.year
    )

    # Column name patterns vary; find them robustly
    flow_col = [c for c in df.columns if "00060" in c and "cd" not in c]
    temp_col = [c for c in df.columns if "00010" in c and "cd" not in c]

    results = []
    for wy in range(start_year, end_year + 1):
        wy_df = df[df["water_year"] == wy]
        # Summer low-flow window: Jul–Sep
        summer = wy_df[wy_df["date"].dt.month.isin([7, 8, 9])]

        row = {"water_year": wy}
        if flow_col and len(wy_df) > 0:
            row["mean_flow_cfs"]        = wy_df[flow_col[0]].mean()
            row["min_summer_flow_cfs"]  = summer[flow_col[0]].min() if len(summer) > 0 else np.nan
        if temp_col and len(wy_df) > 0:
            row["mean_water_temp_c"]    = wy_df[temp_col[0]].mean()
            row["max_summer_temp_c"]    = summer[temp_col[0]].max() if len(summer) > 0 else np.nan
            row["days_above_18c"]       = (wy_df[temp_col[0]] > 18).sum()  # salmon thermal stress

        results.append(row)

    return pd.DataFrame(results)


# ── 3. NRCS SNOTEL Snowpack ──────────────────────────────────────────────────

def fetch_snotel_swe(station_id: str = "769",
                     start_year: int = START_YEAR,
                     end_year:   int = END_YEAR) -> pd.DataFrame:
    """
    Fetch annual April 1 Snow Water Equivalent (SWE) from NRCS SNOTEL.

    April 1 SWE is the standard Pacific Northwest snowpack metric —
    it strongly predicts summer baseflow and water temperature.

    Station 769 = Stampede Pass (closest to upper Issaquah watershed)
    Station 781 = Snoqualmie Pass (secondary)

    Uses the NRCS REST API (no key required).

    Returns
    -------
    pd.DataFrame with columns:
        water_year, swe_apr1_in, swe_anomaly_pct
    """
    print(f"  Fetching SNOTEL station {station_id}...")
    url = (
        f"https://wcc.sc.egov.usda.gov/reportGenerator/view_csv/customSingleStationReport/"
        f"annual/start_of_period/{station_id}:WA:SNTL%7Cid=%22%22%7Cname/"
        f"1980-04-01,{end_year}-04-01/WTEQ::value"
    )
    try:
        resp = requests.get(url, timeout=30)
        lines = [l for l in resp.text.splitlines() if not l.startswith("#") and l.strip()]
        rows = []
        for line in lines[1:]:        # skip header
            parts = line.split(",")
            if len(parts) >= 2:
                try:
                    yr  = int(parts[0].strip()[:4])
                    swe = float(parts[1].strip())
                    rows.append({"water_year": yr, "swe_apr1_in": swe})
                except ValueError:
                    continue
        swe_df = pd.DataFrame(rows)
    except Exception as e:
        print(f"    Warning: SNOTEL fetch failed ({e}). Using placeholder.")
        swe_df = pd.DataFrame({
            "water_year": STUDY_YEARS,
            "swe_apr1_in": [np.nan] * len(STUDY_YEARS)
        })

    # Compute anomaly vs. 1981–2010 climatological mean
    base = swe_df[swe_df["water_year"].between(1981, 2010)]["swe_apr1_in"].mean()
    swe_df["swe_anomaly_pct"] = ((swe_df["swe_apr1_in"] - base) / base * 100).round(1)
    return swe_df[swe_df["water_year"].between(start_year, end_year)].reset_index(drop=True)


# ── 4. NOAA PDO Ocean Conditions ─────────────────────────────────────────────

def fetch_pdo_index(start_year: int = START_YEAR,
                    end_year:   int = END_YEAR) -> pd.DataFrame:
    """
    Fetch the Pacific Decadal Oscillation (PDO) monthly index from NOAA.

    PDO is a key predictor of salmon survival at sea:
      Negative PDO = cool, productive North Pacific → better salmon returns
      Positive PDO = warm water → reduced prey, lower survival

    We compute two features:
      - pdo_winter_mean: Nov–Mar mean (ocean conditions during smolt outmigration year)
      - pdo_lag1_winter: prior-year winter PDO (ocean conditions during ocean entry)

    Source: https://psl.noaa.gov/pdo/

    Returns
    -------
    pd.DataFrame with columns:
        water_year, pdo_winter_mean, pdo_lag1_winter
    """
    print("  Fetching NOAA PDO index...")
    url = "https://psl.noaa.gov/pdo/data/pdo.timeseries.ersstv5.csv"
    try:
        df = pd.read_csv(url, skiprows=1, header=None,
                         names=["date", "pdo"], na_values=["-99.99"])
        df["date"] = pd.to_datetime(df["date"], format="%Y%m", errors="coerce")
        df = df.dropna(subset=["date"])
        df["year"]  = df["date"].dt.year
        df["month"] = df["date"].dt.month

        # Winter PDO: Nov of prior year through Mar of current year
        # Assign to the calendar year of Jan–Mar
        results = []
        for yr in range(start_year - 1, end_year + 1):
            winter = df[
                ((df["year"] == yr - 1) & (df["month"].isin([11, 12]))) |
                ((df["year"] == yr)     & (df["month"].isin([1, 2, 3])))
            ]["pdo"].mean()
            results.append({"year": yr, "pdo_winter_mean": round(winter, 3)})

        pdo_yr = pd.DataFrame(results)
        pdo_yr["pdo_lag1_winter"] = pdo_yr["pdo_winter_mean"].shift(1)
        pdo_yr = pdo_yr.rename(columns={"year": "water_year"})
        return pdo_yr[pdo_yr["water_year"].between(start_year, end_year)].reset_index(drop=True)

    except Exception as e:
        print(f"    Warning: PDO fetch failed ({e}). Using placeholder.")
        return pd.DataFrame({
            "water_year":      STUDY_YEARS,
            "pdo_winter_mean": [np.nan] * len(STUDY_YEARS),
            "pdo_lag1_winter": [np.nan] * len(STUDY_YEARS),
        })


# ── 5. Urban Development / Impervious Surface ────────────────────────────────

def load_impervious_surface(filepath: str | Path) -> pd.DataFrame:
    """
    Load impervious surface coverage (%) for the Issaquah/Sammamish watershed.

    Source options:
      - NLCD (National Land Cover Database) — available for 2001, 2004, 2006,
        2008, 2011, 2013, 2016, 2019, 2021: https://www.mrlc.gov
      - King County GIS impervious surface layer:
        https://kingcounty.gov/services/gis/GISData

    Expected CSV columns:
        Year, Watershed_Area_km2, Impervious_km2, Impervious_Pct

    Returns
    -------
    pd.DataFrame interpolated to annual values:
        water_year, impervious_pct, impervious_pct_change
    """
    df = pd.read_csv(filepath)
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")
    df = df.rename(columns={"year": "water_year"})

    # NLCD is only available every 2–3 years — interpolate to annual
    full_years = pd.DataFrame({"water_year": STUDY_YEARS})
    df = full_years.merge(df[["water_year", "impervious_pct"]], on="water_year", how="left")
    df["impervious_pct"] = df["impervious_pct"].interpolate(method="linear")

    # Year-over-year change (urbanization rate)
    df["impervious_pct_change"] = df["impervious_pct"].diff().round(3)
    return df


# ── 6. Master Dataset Assembly ───────────────────────────────────────────────

def build_master_dataset(
    escapement_file:      str | Path,
    hatchery_file:        str | Path,
    impervious_file:      str | Path,
    fetch_live_data:      bool = True,
) -> pd.DataFrame:
    """
    Assemble all data sources into a single master DataFrame.

    Parameters
    ----------
    escapement_file   : path to WDFW escapement CSV
    hatchery_file     : path to FISH hatchery release CSV
    impervious_file   : path to impervious surface CSV
    fetch_live_data   : if True, pull USGS, SNOTEL, PDO from live APIs
                        if False, attempt to load from raw/ cached files

    Returns
    -------
    pd.DataFrame indexed by water_year with all stressor and response variables
    Saved to: data/processed/issaquah_creek_master.csv
    """
    print("Building master dataset...")

    base = pd.DataFrame({"water_year": STUDY_YEARS})

    # Response variables (what we're trying to explain / predict)
    print("  Loading WDFW escapement...")
    escapement = load_wdfw_escapement(escapement_file)
    base = base.merge(escapement, on="water_year", how="left")

    # Hatchery releases (predictor — affects return expectations)
    print("  Loading FISH hatchery releases...")
    hatchery = load_fish_hatchery_releases(hatchery_file)
    base = base.merge(hatchery, on="water_year", how="left")

    # Environmental predictors
    if fetch_live_data:
        usgs   = fetch_usgs_annual()
        snotel = fetch_snotel_swe()
        pdo    = fetch_pdo_index()
    else:
        usgs   = pd.read_csv(RAW_DIR / "usgs_issaquah_creek.csv")
        snotel = pd.read_csv(RAW_DIR / "snotel_stampede_pass.csv")
        pdo    = pd.read_csv(RAW_DIR / "noaa_pdo_index.csv")

    for df in [usgs, snotel, pdo]:
        base = base.merge(df, on="water_year", how="left")

    # Urban development
    print("  Loading impervious surface data...")
    imperv = load_impervious_surface(impervious_file)
    base = base.merge(imperv, on="water_year", how="left")

    # ── Data quality report ──────────────────────────────────────────────────
    print("\nData quality summary:")
    print(base.isnull().sum().to_string())
    print(f"\nTotal rows: {len(base)}  |  Years: {base['water_year'].min()}–{base['water_year'].max()}")

    # Save
    out_path = PROCESSED_DIR / "issaquah_creek_master.csv"
    base.to_csv(out_path, index=False)
    print(f"\nSaved master dataset → {out_path}")

    return base


# ── 7. Data Validation ───────────────────────────────────────────────────────

def validate_master(df: pd.DataFrame) -> dict:
    """
    Run sanity checks on the master dataset.
    Returns a dict of check results. Prints warnings for failures.
    """
    checks = {}

    # Year coverage
    checks["year_range_ok"] = (
        df["water_year"].min() <= START_YEAR and
        df["water_year"].max() >= END_YEAR - 1
    )

    # 2025 anchor check (if present)
    row_2025 = df[df["water_year"] == 2025]
    if len(row_2025) > 0:
        chin = row_2025["chinook_total"].iloc[0]
        checks["2025_chinook_plausible"] = (4500 <= chin <= 5500)

    # No all-NaN columns
    all_nan_cols = [c for c in df.columns if df[c].isnull().all()]
    checks["no_all_nan_columns"] = len(all_nan_cols) == 0
    if all_nan_cols:
        print(f"  WARNING: All-NaN columns found: {all_nan_cols}")

    # Reasonable value ranges
    if "chinook_total" in df.columns:
        checks["chinook_range_ok"] = df["chinook_total"].dropna().between(100, 50000).all()
    if "swe_apr1_in" in df.columns:
        checks["swe_range_ok"] = df["swe_apr1_in"].dropna().between(0, 120).all()

    for check, result in checks.items():
        status = "✓" if result else "✗"
        print(f"  {status} {check}: {result}")

    return checks


if __name__ == "__main__":
    # Example: build dataset with live API fetches
    # (escapement and impervious CSV files must be downloaded first)
    print("Issaquah Creek Salmon Return Study — Data Pipeline")
    print("=" * 55)
    print("To build the master dataset, call:")
    print("  from src.data_pipeline import build_master_dataset")
    print("  df = build_master_dataset(")
    print("      escapement_file='data/raw/wdfw_issaquah_escapement.csv',")
    print("      hatchery_file='data/raw/fish_hatchery_releases.csv',")
    print("      impervious_file='data/raw/king_county_impervious.csv',")
    print("  )")
