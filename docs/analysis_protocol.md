# Analysis protocol

Version: 1.1

Locked: 2026-07-26; amended 2026-07-29 (D-020: NPGO/ONI added as pre-specified marine-window predictors)

Scope: Issaquah Creek Chinook and Coho adult returns, 1997–2025

Changes to this protocol require a dated decision-log entry before results are regenerated.

## Study questions

1. How have Issaquah Hatchery adult Chinook and Coho returns changed since 1997?
2. Which measured environmental indicators are associated with annual return variation?
3. How stable are those associations under biologically plausible cohort lags?
4. Can a parsimonious model improve time-aware predictions over a naive historical baseline?

The study is observational. Association estimates are not causal effects.

## Responses

| Role | Variable | Definition |
|---|---|---|
| Primary | `total_adults` | Sum of WDFW `Trap Estimate` adult counts across hatchery and wild origins, by return year and species |
| Secondary | `wild_adults` | Wild-origin component of the primary adult count |
| Secondary | `hatchery_adults` | Hatchery-origin component of the primary adult count |
| Sensitivity only | `adult_plus_jacks` | Adults plus separately reported jacks |

Handling events such as mortality, spawning, surplus, shipping, and egg take are excluded because they occur after trap entry and would double-count fish. Response values are never interpolated or imputed.

## Spatial boundary and source hierarchy

The analytical boundary is the King County `TOPO_BASIN_KC_AREA` feature named `Issaquah Creek`, WRIA 8. The restricted raw polygon remains local; its checksum and metadata are registered.

Source priority is:

1. WDFW event records for adult returns.
2. Authorized RMIS or permitted FISH records for actual releases; otherwise omit releases.
3. USGS station 12121600 for discharge.
4. King County station 0631 for the warm-season grab-sample temperature index.
5. NRCS Stampede Pass SNOTEL 788 for SWE.
6. NOAA PSL ERSSTv5 PDO.
7. NOAA/GaTech NPGO index and NOAA CPC ONI, as of D-020 -- additional marine-condition proxies, tested alongside rather than in place of PDO.
8. Annual NLCD Collection 1.2 Fractional Impervious Surface; otherwise omit imperviousness.

No substitute from another watershed or a planned hatchery-production target may be represented as an observed value.

## Temporal alignment

Return year is the calendar year of WDFW trap entry. Hydrologic water year ends September 30 of the named year.

| Species | Primary cohort proxy | Required sensitivity |
|---|---|---|
| Coho | `return_year - 2` | Report that a single lag is an approximation of a variable age distribution |
| Chinook | `return_year - 4` | Repeat association results at lags 3 and 5 |

Same-year July–September flow and June–September temperature are adult migration indicators. Cohort-year flow, SWE, and temperature are freshwater-condition proxies. `marine_pdo_mean` averages annual PDO from the year after the cohort proxy through the year before adult return. As of D-020, `marine_npgo_mean` and `marine_oni_mean` use the identical marine window and aggregation logic, applied to the NPGO and ONI indices respectively.

Hatchery releases, if obtained, must be matched to plausible return cohorts and analyzed separately from the environmental proxy lag. No return-per-release quantity will be calculated from planned production targets.

## Pre-specified predictors

The initial association set is deliberately small:

- Same-year `flow_jul_sep_mean_cfs` or `flow_jul_sep_min_cfs`—not both in the same small model.
- Same-year `temp_jun_sep_mean_c`.
- `cohort_swe_apr01_inches`.
- `cohort_flow_water_year_mean_cfs`.
- `marine_pdo_mean`.
- `marine_npgo_mean` and `marine_oni_mean` (D-020) -- additional ocean-condition proxies, tested both alone and alongside PDO; not substituted for it in the already-decided models.
- `impervious_pct` only if acquired and validated.
- `hatchery_releases` only if actual releases are acquired and cohort-aligned.

Continuous predictors may be standardized within each training fold. Count responses may use `log1p` in sensitivity models, but reported trends retain original units. Correlated alternatives are not entered together without diagnostics.

## Missing data

- Never impute a response.
- Never silently fill a predictor.
- Annual environmental summaries require their documented coverage thresholds.
- Exclude unavailable imperviousness and releases from the initial model; do not replace them with zeros.
- Any future interpolation must have a separate value-status flag and an analysis excluding interpolated rows.

## Analysis and validation

1. Begin with descriptive plots and species-specific trend estimates.
2. Use rank correlations and parsimonious regressions as associations.
3. Limit model size because there are 29 response years per species.
4. Use expanding-window or rolling-origin validation; never random train/test splitting.
5. Compare against a training-fold mean/median or previous-year naive predictor.
6. Fit scaling, feature selection, and tuning inside each training fold.
7. Report MAE and RMSE; report R² only with context.
8. Use residual and influence diagnostics and lag sensitivity.
9. Treat XGBoost as exploratory only if it improves time-aware validation consistently.

Uncertainty will use confidence intervals appropriate to the fitted trend/association model and empirical prediction intervals from time-aware residuals where feasible.

## Scenarios and claims

Scenarios are conditional illustrations, not predictions of policy or climate. Each input must cite an observed range or authoritative projection. Without releases and imperviousness, scenarios are limited to measured flow, temperature, SWE, and PDO ranges and must hold unmeasured hatchery production and land use implicitly constant.

Final language must distinguish:

- observed trend,
- statistical association,
- conditional prediction,
- illustrative scenario.
