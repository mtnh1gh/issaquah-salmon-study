"""Reproducible Phase 3 exploratory analysis from the validated master data."""

from __future__ import annotations

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


MASTER_PATH = ROOT / "data/processed/issaquah_creek_master.csv"
ENV_PATH = ROOT / "data/processed/issaquah_annual_environment.csv"
TABLE_DIR = ROOT / "outputs/tables"
FIGURE_DIR = ROOT / "outputs/figures"
REPORT_PATH = ROOT / "docs/eda_report.md"
RNG_SEED = 20260726

PREDICTORS = [
    "flow_jul_sep_mean_cfs",
    "temp_jun_sep_mean_c",
    "cohort_flow_water_year_mean_cfs",
    "cohort_swe_apr01_inches",
    "marine_pdo_mean",
]

LABELS = {
    "flow_jul_sep_mean_cfs": "Adult migration flow",
    "temp_jun_sep_mean_c": "Adult migration temperature",
    "cohort_flow_water_year_mean_cfs": "Cohort-year flow",
    "cohort_swe_apr01_inches": "Cohort-year April 1 SWE",
    "cohort_temp_jun_sep_mean_c": "Cohort-year temperature",
    "marine_pdo_mean": "Marine-window PDO",
    "flow_water_year_mean_cfs": "Water-year flow",
    "swe_apr01_inches": "April 1 SWE",
    "pdo_annual_mean": "Annual PDO",
    "total_adults": "Total adults",
    "hatchery_adults": "Hatchery-origin adults",
    "wild_adults": "Wild-origin adults",
}


def bh_adjust(pvalues: pd.Series) -> pd.Series:
    """Benjamini-Hochberg false-discovery-rate adjustment."""
    values = pvalues.to_numpy(dtype=float)
    order = np.argsort(values)
    ranked = values[order]
    adjusted = ranked * len(values) / np.arange(1, len(values) + 1)
    adjusted = np.minimum.accumulate(adjusted[::-1])[::-1]
    result = np.empty_like(adjusted)
    result[order] = np.minimum(adjusted, 1.0)
    return pd.Series(result, index=pvalues.index)


def block_bootstrap_spearman(
    x: np.ndarray,
    y: np.ndarray,
    block_length: int = 3,
    repetitions: int = 2000,
    seed: int = RNG_SEED,
) -> tuple[float, float]:
    """Approximate autocorrelation-aware CI using paired moving-block bootstrap."""
    valid = np.isfinite(x) & np.isfinite(y)
    x, y = x[valid], y[valid]
    n = len(x)
    if n < 8:
        return np.nan, np.nan
    rng = np.random.default_rng(seed)
    starts = np.arange(0, n - block_length + 1)
    estimates: list[float] = []
    block_count = int(np.ceil(n / block_length))
    for _ in range(repetitions):
        selected = rng.choice(starts, size=block_count, replace=True)
        indices = np.concatenate(
            [np.arange(start, start + block_length) for start in selected]
        )[:n]
        rho = stats.spearmanr(x[indices], y[indices]).statistic
        if np.isfinite(rho):
            estimates.append(float(rho))
    if not estimates:
        return np.nan, np.nan
    return tuple(np.quantile(estimates, [0.025, 0.975]))


def trend_row(group: pd.DataFrame, variable: str, series: str) -> dict[str, object]:
    clean = group[["return_year", variable]].dropna()
    tau = stats.kendalltau(clean["return_year"], clean[variable])
    slope = stats.theilslopes(clean[variable], clean["return_year"], alpha=0.95)
    first_five = clean.nsmallest(5, "return_year")[variable].mean()
    last_five = clean.nlargest(5, "return_year")[variable].mean()
    return {
        "series": series,
        "variable": variable,
        "n": len(clean),
        "first_year": int(clean["return_year"].min()),
        "last_year": int(clean["return_year"].max()),
        "kendall_tau": tau.statistic,
        "p_value": tau.pvalue,
        "theil_sen_slope_per_year": slope.slope,
        "slope_ci_low": slope.low_slope,
        "slope_ci_high": slope.high_slope,
        "first_5_year_mean": first_five,
        "last_5_year_mean": last_five,
        "last_vs_first_5_pct": (
            (last_five / first_five - 1) * 100 if first_five != 0 else np.nan
        ),
    }


def make_trend_table(master: pd.DataFrame, env: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for species, group in master.groupby("species", sort=True):
        total = trend_row(group, "total_adults", species)
        total["test_family"] = "response"
        rows.append(total)
        # Wild-origin rows are comparable only from the first year with explicit wild data.
        wild = group[group["return_year"] >= 2010]
        wild_result = trend_row(wild, "wild_adults", f"{species} (2010+)")
        wild_result["test_family"] = "response"
        rows.append(wild_result)
    for variable in [
        "flow_water_year_mean_cfs",
        "flow_jul_sep_mean_cfs",
        "swe_apr01_inches",
        "pdo_annual_mean",
        "temp_jun_sep_mean_c",
    ]:
        response_period = env[env["return_year"].between(1997, 2025)]
        environmental = trend_row(response_period, variable, "Environmental")
        environmental["test_family"] = "environment"
        rows.append(environmental)
    result = pd.DataFrame(rows)
    result["p_fdr_bh"] = result.groupby("test_family", group_keys=False)[
        "p_value"
    ].apply(bh_adjust)
    return result


def make_correlations(master: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for species, group in master.groupby("species", sort=True):
        ordered = group.sort_values("return_year")
        for index, predictor in enumerate(PREDICTORS):
            clean = ordered[["total_adults", predictor]].dropna()
            test = stats.spearmanr(clean["total_adults"], clean[predictor])
            low, high = block_bootstrap_spearman(
                clean["total_adults"].to_numpy(float),
                clean[predictor].to_numpy(float),
                seed=RNG_SEED + index + (100 if species == "Coho" else 200),
            )
            rows.append(
                {
                    "species": species,
                    "response": "total_adults",
                    "predictor": predictor,
                    "n": len(clean),
                    "spearman_rho": test.statistic,
                    "p_value": test.pvalue,
                    "block_bootstrap_ci_low": low,
                    "block_bootstrap_ci_high": high,
                    "block_length_years": 3,
                }
            )
    result = pd.DataFrame(rows)
    result["p_fdr_bh"] = bh_adjust(result["p_value"])
    result["passes_fdr_0_05"] = result["p_fdr_bh"] <= 0.05
    return result


def lag_sensitivity(master: pd.DataFrame, env: pd.DataFrame) -> pd.DataFrame:
    env_lookup = env.set_index("return_year")
    rows: list[dict[str, object]] = []
    lag_sets = {"Coho": [2], "Chinook": [3, 4, 5]}
    cohort_variables = [
        "flow_water_year_mean_cfs",
        "swe_apr01_inches",
        "temp_jun_sep_mean_c",
    ]
    for species, lags in lag_sets.items():
        response = master[master["species"] == species].sort_values("return_year")
        for lag in lags:
            for variable in cohort_variables:
                values = response["return_year"].map(
                    lambda year: env_lookup.at[year - lag, variable]
                    if year - lag in env_lookup.index
                    else np.nan
                )
                test = stats.spearmanr(response["total_adults"], values, nan_policy="omit")
                rows.append(
                    {
                        "species": species,
                        "lag_years": lag,
                        "predictor": f"cohort_{variable}",
                        "n": int(values.notna().sum()),
                        "spearman_rho": test.statistic,
                        "p_value": test.pvalue,
                    }
                )
    result = pd.DataFrame(rows)
    result["p_fdr_bh"] = bh_adjust(result["p_value"])
    return result


def make_missingness(master: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "variable": master.columns,
            "missing_count": [master[column].isna().sum() for column in master.columns],
            "missing_pct": [
                master[column].isna().mean() * 100 for column in master.columns
            ],
        }
    )


def plot_returns(master: pd.DataFrame) -> None:
    colors = {"Chinook": "#c44e52", "Coho": "#4c72b0"}
    fig, axes = plt.subplots(2, 1, figsize=(11, 8), sharex=True)
    for axis, species in zip(axes, ["Chinook", "Coho"]):
        group = master[master["species"] == species].sort_values("return_year")
        axis.plot(
            group["return_year"],
            group["total_adults"],
            marker="o",
            linewidth=2,
            color=colors[species],
            label="Total adults",
        )
        axis.plot(
            group["return_year"],
            group["hatchery_adults"],
            linewidth=1.4,
            alpha=0.75,
            color="#555555",
            label="Hatchery origin",
        )
        wild = group[group["return_year"] >= 2010]
        axis.plot(
            wild["return_year"],
            wild["wild_adults"],
            linewidth=1.4,
            color="#55a868",
            label="Wild origin (comparable 2010+)",
        )
        axis.axvline(2010, color="#888888", linestyle=":", linewidth=1)
        axis.set_title(species)
        axis.set_ylabel("Adults counted")
        axis.grid(alpha=0.2)
        axis.legend(loc="upper right", frameon=False)
    axes[-1].set_xlabel("Return year")
    fig.suptitle("Issaquah Hatchery adult returns")
    fig.tight_layout()
    fig.savefig(FIGURE_DIR / "annual_salmon_returns.png", dpi=180)
    plt.close(fig)

    fig, axes = plt.subplots(2, 1, figsize=(11, 7), sharex=True)
    for axis, species in zip(axes, ["Chinook", "Coho"]):
        wild = master[
            (master["species"] == species) & (master["return_year"] >= 2010)
        ].sort_values("return_year")
        axis.plot(
            wild["return_year"],
            wild["wild_adults"],
            marker="o",
            linewidth=2,
            color=colors[species],
        )
        axis.set_title(species)
        axis.set_ylabel("Wild-origin adults")
        axis.grid(alpha=0.2)
    axes[-1].set_xlabel("Return year")
    fig.suptitle("Wild-origin adult returns (comparable period)")
    fig.tight_layout()
    fig.savefig(FIGURE_DIR / "wild_origin_returns_2010_onward.png", dpi=180)
    plt.close(fig)


def plot_environment(env: pd.DataFrame) -> None:
    plot_data = env[env["return_year"].between(1997, 2025)]
    panels = [
        ("flow_jul_sep_mean_cfs", "July–September flow (ft³/s)"),
        ("temp_jun_sep_mean_c", "June–September temperature (°C)"),
        ("swe_apr01_inches", "April 1 SWE (inches)"),
        ("pdo_annual_mean", "Annual PDO index"),
    ]
    fig, axes = plt.subplots(2, 2, figsize=(12, 8), sharex=True)
    for axis, (variable, label) in zip(axes.flat, panels):
        axis.plot(plot_data["return_year"], plot_data[variable], marker="o", ms=3)
        slope = stats.theilslopes(plot_data[variable], plot_data["return_year"]).slope
        intercept = np.median(
            plot_data[variable] - slope * plot_data["return_year"]
        )
        axis.plot(
            plot_data["return_year"],
            intercept + slope * plot_data["return_year"],
            linestyle="--",
            color="#c44e52",
            label="Theil–Sen trend",
        )
        axis.set_title(label)
        axis.grid(alpha=0.2)
    axes[-1, 0].set_xlabel("Year")
    axes[-1, 1].set_xlabel("Year")
    fig.suptitle("Environmental indicators, response period")
    fig.tight_layout()
    fig.savefig(FIGURE_DIR / "environmental_trends.png", dpi=180)
    plt.close(fig)


def plot_correlations(correlations: pd.DataFrame) -> None:
    matrix = correlations.pivot(
        index="predictor", columns="species", values="spearman_rho"
    ).reindex(PREDICTORS)
    fig, axis = plt.subplots(figsize=(7, 5))
    image = axis.imshow(matrix.to_numpy(), cmap="RdBu_r", vmin=-1, vmax=1)
    axis.set_xticks(range(len(matrix.columns)), matrix.columns)
    axis.set_yticks(
        range(len(matrix.index)), [LABELS.get(item, item) for item in matrix.index]
    )
    for row in range(matrix.shape[0]):
        for column in range(matrix.shape[1]):
            value = matrix.iloc[row, column]
            axis.text(column, row, f"{value:.2f}", ha="center", va="center")
    axis.set_title("Spearman associations with total adult returns")
    fig.colorbar(image, ax=axis, label="Spearman ρ")
    fig.tight_layout()
    fig.savefig(FIGURE_DIR / "return_predictor_correlations.png", dpi=180)
    plt.close(fig)


def write_report(
    master: pd.DataFrame,
    trends: pd.DataFrame,
    correlations: pd.DataFrame,
    lags: pd.DataFrame,
    missingness: pd.DataFrame,
) -> None:
    response_trends = trends[
        (trends["variable"] == "total_adults")
        & (~trends["series"].str.contains("2010"))
    ]
    strongest = correlations.iloc[
        correlations["spearman_rho"].abs().sort_values(ascending=False).index
    ].groupby("species", sort=True).head(2)
    unavailable = missingness[missingness["missing_count"] == len(master)]
    environmental_trends = trends[
        (trends["test_family"] == "environment") & (trends["p_fdr_bh"] <= 0.05)
    ]
    chinook_lag_flow = lags[
        (lags["species"] == "Chinook")
        & (lags["predictor"] == "cohort_flow_water_year_mean_cfs")
    ]
    lines = [
        "# Exploratory analysis report",
        "",
        "Phase: 3",
        "",
        "Coverage: 1997–2025; 29 annual observations per species.",
        "",
        "All findings are exploratory associations under `docs/analysis_protocol.md`; they are not causal effects.",
        "",
        "## Return trends",
        "",
        "| Species | Kendall tau | Raw p-value | BH-adjusted p | Theil–Sen adults/year | Last 5 vs first 5 |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in response_trends.itertuples():
        lines.append(
            f"| {row.series} | {row.kendall_tau:.3f} | {row.p_value:.3f} | "
            f"{row.p_fdr_bh:.3f} | {row.theil_sen_slope_per_year:.1f} | "
            f"{row.last_vs_first_5_pct:.1f}% |"
        )
    lines += [
        "",
        "Wild-origin series are plotted and tested only from 2010 because earlier records do not contain explicit wild-origin trap rows.",
        "",
        "Neither species has a monotonic total-adult trend that passes the pre-specified multiple-testing threshold. The difference between first/last five-year means is descriptive and sensitive to highly variable return years.",
        "",
        "## Environmental trends",
        "",
        "| Indicator | Kendall tau | BH-adjusted p | Theil–Sen change/year |",
        "|---|---:|---:|---:|",
    ]
    for row in environmental_trends.itertuples():
        lines.append(
            f"| {LABELS.get(row.variable, row.variable)} | {row.kendall_tau:.3f} | "
            f"{row.p_fdr_bh:.3f} | {row.theil_sen_slope_per_year:.3f} |"
        )
    lines += [
        "",
        "These monotonic environmental trends are indicators over the study period; they do not establish that the trend caused salmon-return variation.",
        "",
        "## Strongest pre-specified correlations",
        "",
        "| Species | Predictor | Spearman rho | Block-bootstrap 95% CI | Raw p | BH-adjusted p |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for row in strongest.itertuples():
        lines.append(
            f"| {row.species} | {LABELS.get(row.predictor, row.predictor)} | "
            f"{row.spearman_rho:.3f} | [{row.block_bootstrap_ci_low:.3f}, "
            f"{row.block_bootstrap_ci_high:.3f}] | {row.p_value:.3f} | "
            f"{row.p_fdr_bh:.3f} |"
        )
    lines += [
        "",
        "The moving-block bootstrap uses three-year blocks to partially reflect temporal dependence. With only 29 years, intervals are expected to be wide.",
        "",
        "## Lag sensitivity",
        "",
        "Chinook cohort indicators were checked at lags 3, 4, and 5; Coho used the locked primary lag 2. A candidate that changes sign or magnitude materially across Chinook lags is not considered stable.",
        "",
        "Chinook cohort-year flow is not stable across lags: "
        + ", ".join(
            f"lag {int(row.lag_years)}: rho={row.spearman_rho:.3f}"
            for row in chinook_lag_flow.itertuples()
        )
        + ".",
        "",
        f"Detailed results: `outputs/tables/lag_sensitivity.csv` ({len(lags)} tests).",
        "",
        "## Missingness and exclusions",
        "",
    ]
    for row in unavailable.itertuples():
        lines.append(
            f"- `{row.variable}` is unavailable in all {len(master)} rows and remains excluded."
        )
    lines += [
        "",
        "No core response or available environmental feature is missing. Releases and imperviousness are not zero-filled.",
        "",
        "## Interpretation limits",
        "",
        "- Hatchery releases remain an unmeasured production confounder.",
        "- Direct imperviousness is unavailable, so no urban-development period comparison is run.",
        "- Multiple-testing adjustment is Benjamini–Hochberg across each output table.",
        "- Correlation does not identify biological mechanism or causation.",
        "- Phase 4 should retain only a small, pre-specified predictor set and time-aware validation.",
        "",
        "## Reproduction",
        "",
        "```powershell",
        r".\.venv\Scripts\python.exe .\src\run_eda.py",
        "```",
        "",
        f"Runtime: Python {platform.python_version()}, pandas {pd.__version__}, "
        f"NumPy {np.__version__}, SciPy {scipy.__version__}, "
        f"Matplotlib {matplotlib.__version__}.",
    ]
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    master = pd.read_csv(MASTER_PATH)
    env = pd.read_csv(ENV_PATH)

    trends = make_trend_table(master, env)
    correlations = make_correlations(master)
    lags = lag_sensitivity(master, env)
    missingness = make_missingness(master)

    trends.to_csv(TABLE_DIR / "trend_tests.csv", index=False)
    correlations.to_csv(TABLE_DIR / "return_predictor_correlations.csv", index=False)
    lags.to_csv(TABLE_DIR / "lag_sensitivity.csv", index=False)
    missingness.to_csv(TABLE_DIR / "master_missingness.csv", index=False)
    master.groupby("species")[
        ["total_adults", "hatchery_adults", "wild_adults", "total_jacks"]
    ].agg(["count", "mean", "median", "min", "max"]).round(3).to_csv(
        TABLE_DIR / "response_summary.csv"
    )

    plot_returns(master)
    plot_environment(env)
    plot_correlations(correlations)
    write_report(master, trends, correlations, lags, missingness)
    print(
        f"Phase 3 EDA complete: {len(trends)} trends, "
        f"{len(correlations)} correlations, {len(lags)} lag tests."
    )


if __name__ == "__main__":
    main()
