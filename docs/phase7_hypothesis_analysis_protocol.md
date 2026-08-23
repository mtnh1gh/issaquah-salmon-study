# Phase 7 hypothesis-analysis protocol

Version: 1.0

Status: **FROZEN 2026-08-23, before Phase 7 life-stage association tests**

Scope: Issaquah Creek Chinook and Coho adult returns, 1997-2025

This protocol converts the planning matrix in
`docs/jei_hypothesis_and_phase7_analysis_plan.md` into executable definitions.
Any change to a predictor, outcome, lag, window, test, multiplicity family, or
exclusion rule requires a dated amendment in `docs/decision_log.md` before the
affected Phase 7 result is regenerated. The unamended result must be retained.

The study is observational. All estimates are associations, not causal effects.
The project has previously examined annual salmon and generic warm-season
temperature relationships. This freeze prevents further specification changes
for the life-stage rerun, but it is not represented as a fully prospective
preregistration independent of all prior outcome inspection.

## 1. Frozen data inputs

### Salmon outcomes

Source table: `data/gold/issaquah_creek_master.csv`

Join key: exposure-table `primary_return_year` to master-table `return_year`,
with an exact species match.

| Role | Field | Frozen definition |
|---|---|---|
| Primary | `total_adults` | Annual WDFW `Trap Estimate` adult counts summed across reported hatchery and wild origins; jacks excluded |
| Outcome sensitivity | `adult_plus_jacks` | `total_adults + total_jacks`; same analysis repeated and labeled sensitivity |
| Deferred secondary | `hatchery_adults`, `wild_adults` | Not tested until an origin-comparability audit defines usable years; they cannot replace the primary outcome post hoc |

No response is interpolated or imputed. The primary outcome is analyzed in its
original count units for plots and Spearman tests. Regression uses
`log1p(total_adults)`; the outcome-sensitivity regression uses
`log1p(adult_plus_jacks)`.

### Temperature and matched flow exposures

Source table:
`outputs/temperature_proxy/issaquah_life_stage_temperature_exposure_1995_2025.csv`

| Role | Field | Frozen use |
|---|---|---|
| Primary thermal predictor | `primary_thermal_value_c` | T2 air-temperature-plus-seasonal biological-window mean; identical to `t2_window_mean_proxy_c` |
| Model sensitivity | `sensitivity_thermal_value_c` | T1 air-plus-flow-plus-seasonal window mean; identical to `t1_window_mean_proxy_c` |
| Matched physical predictor | `matched_window_mean_usgs_flow_cfs` | Arithmetic mean of USGS 12121600 daily mean discharge over the identical exposure dates |
| Quality flag | `t2_extrapolation_days` | Number of days in the window outside T2's calibration predictor ranges |

T2 is primary because its held-out performance is close to T1 while remaining
independent of streamflow. This avoids mathematical coupling when flow is tested
against temperature or entered beside temperature. T1 is always reported as a
model-form sensitivity and is never substituted as primary after results are
seen.

### Thermal metrics that are not primary

The following are **exploratory only** for both T1 and T2:

- modeled daily-window maximum;
- modeled maximum within-window seven-day mean;
- counts of modeled days at or above 17.5 C, 19 C, or 21 C; and
- longest modeled spell at or above 17.5 C.

They may be summarized or plotted, but they are outside every confirmatory test
family and cannot determine whether H1 or H2 is supported. They are modeled
grab-temperature proxies, not observed daily maxima, regulatory exceedances, or
7DADMax.

### Hydroclimate inputs

Source table: `data/silver/issaquah_annual_environment.csv`

- `swe_apr01_inches`: April 1 Stampede Pass SNOTEL SWE, treated as a regional
  hydroclimate proxy rather than Issaquah basin snowpack.
- `flow_jul_sep_mean_cfs`: mean USGS 12121600 daily discharge from July 1 through
  September 30 of the same calendar year.

## 2. Frozen temporal alignment

| Analysis | Species | Exposure year | Return/outcome year |
|---|---|---|---|
| A1, A2 | Chinook | same calendar year | `primary_return_year = exposure_year` |
| A3, A4 | Coho | same calendar year | `primary_return_year = exposure_year` |
| A5 | Coho | `return_year - 2` | `primary_return_year = exposure_year + 2` |
| A6 | none | same calendar year | no salmon outcome |
| A7 | none | same exposure year | no salmon outcome |
| A8 | Chinook/Coho | same calendar year | species-specific adult return year |

A5 therefore uses 1995 exposure for the 1997 Coho return and 2023 exposure for
the 2025 return. All A1, A3, and A5 primary tests contain 29 eligible return
years when inputs pass validation.

## 3. Frozen analysis definitions

### Primary salmon-temperature family

| ID | Hypothesis and expected direction | Row filter | Predictor | Outcome |
|---|---|---|---|---|
| A1 / H1a | Warmer Chinook adult-migration conditions are associated with fewer adults; negative | `analysis_id == A1`, `return_year_eligible_for_phase7 == true` | T2 mean, Aug 15-Sep 30 of return year | Chinook `total_adults`, 1997-2025 |
| A3 / H1b | Warmer Coho adult-migration conditions are associated with fewer adults; negative | `analysis_id == A3`, eligible flag true | T2 mean, Sep 15-Oct 31 of return year | Coho `total_adults`, 1997-2025 |
| A5 / H2 | Warmer Coho juvenile/rearing summers are associated with fewer subsequent adults; negative | `analysis_id == A5`, eligible flag true | T2 mean, Jun 1-Sep 30 in `return_year - 2` | Coho `total_adults`, 1997-2025 |

Each analysis has two frozen primary summaries:

1. Spearman rank correlation between the stated predictor and untransformed
   adult count.
2. Simple OLS association
   `log1p(total_adults) ~ 1 + z(primary_thermal_value_c)` with HC3 robust
   standard errors.

`z()` uses the complete analysis sample's arithmetic mean and sample standard
deviation. Report Spearman rho, its interval and adjusted p-value; OLS beta,
HC3 95% confidence interval, and `100 * (exp(beta) - 1)` as the fitted percent
count difference per one-SD warmer window. The regression is supportive; the
rank association is the primary test statistic.

### Window sensitivities

| ID | Frozen alternative | Outcome | Status |
|---|---|---|---|
| A2 | Chinook T2 mean, Aug 15-Oct 31, same return year | Chinook `total_adults` | Window sensitivity to A1 |
| A4 | Coho T2 mean, Sep 15-Nov 30, same return year | Coho `total_adults` | Window sensitivity to A3 |

A2 and A4 use the same Spearman and simple-OLS specifications, but their
p-values are descriptive and do not enter the primary family. A sensitivity
window cannot replace its corresponding primary window.

### Mechanism family

| ID | Frozen rows | Predictor | Outcome | Expected direction |
|---|---|---|---|---|
| A6 / H3 | Environment years 1997-2025 | `swe_apr01_inches` | `flow_jul_sep_mean_cfs` | positive |
| A7 / H4 | A5 exposure rows for all exposure years 1995-2025 | `matched_window_mean_usgs_flow_cfs` | `primary_thermal_value_c` (T2 Jun-Sep mean) | negative |

A6 and A7 use Spearman correlation as the primary statistic. Their supportive
regressions are:

- A6: `log(flow_jul_sep_mean_cfs) ~ 1 + z(swe_apr01_inches)`;
- A7: `primary_thermal_value_c ~ 1 + z(log(matched_window_mean_usgs_flow_cfs))`.

Both use HC3 standard errors. A7 must use T2 temperature; using T1 would make
the response partly constructed from the flow predictor.

### Secondary combined model

A8 is run separately by species on the A1 Chinook rows and A3 Coho rows:

`log1p(total_adults) ~ 1 + z(primary_thermal_value_c) + z(log(matched_window_mean_usgs_flow_cfs))`

Use HC3 standard errors and report coefficients, intervals, adjusted R-squared,
residual plots, variance-inflation factors, and Cook's distance. A8 is secondary
and descriptive; it cannot overturn conclusions from A1 or A3.

## 4. Exact inference procedure

### Rank tests

- Use midranks for ties and the ordinary Pearson correlation of the two rank
  vectors (Spearman rho).
- Use a two-sided Monte Carlo permutation test with 100,000 outcome
  permutations.
- Calculate `p = (1 + count(abs(rho_perm) >= abs(rho_observed))) / 100001`.
- Use deterministic base seed `20260823`, plus the numeric analysis identifier
  (`A1` adds 1, `A3` adds 3, and so on).
- Report the pre-specified expected direction separately; do not convert the
  test to one-sided after seeing the sign.
- Calculate a 95% paired percentile-bootstrap interval for rho using 10,000
  resamples and seed `20260823 + 100 + analysis_number`. Report the number of
  finite bootstrap estimates.

### Multiplicity

- Apply Holm's step-down correction at family alpha 0.05 to the three primary
  salmon-temperature permutation p-values: A1, A3, and A5.
- Apply a separate Holm correction at family alpha 0.05 to A6 and A7.
- A2, A4, A8, T1 substitutions, jack-inclusive outcomes, threshold metrics,
  and influence/extrapolation exclusions are sensitivity or exploratory results;
  label any p-values unadjusted and do not use them for a primary support claim.

No predictor is selected by its p-value. Report exact n, effect size, interval,
raw p-value, adjusted p-value where applicable, and expected/observed direction.

## 5. Frozen missingness, quality, and robustness rules

- Use complete cases only for the fields named by an analysis; never impute an
  outcome or silently fill a predictor.
- Assert one row per species-return year after joining and retain the unmatched
  row report even when it is empty.
- The primary analysis retains T2 extrapolation-flagged windows but reports their
  count. A required sensitivity excludes every row with
  `t2_extrapolation_days > 0`.
- Repeat A1, A3, and A5 with T1 window mean, without changing any other row,
  outcome, or test definition.
- Repeat A1, A3, and A5 with `adult_plus_jacks`.
- For every OLS model, flag Cook's distance above `4/n`; rerun once after
  excluding the single largest-Cook observation. Do not iteratively delete rows.
- For every primary Spearman test, report leave-one-year-out rho minimum,
  maximum, and sign-change count.
- Do not run origin-specific outcomes until the deferred comparability audit is
  frozen in a protocol amendment.

## 6. Reporting and decision language

A primary relationship may be described as "supported by this observational
analysis" only when its observed direction matches the frozen prediction, its
Holm-adjusted permutation p-value is below 0.05, and the effect direction does
not reverse in the required T1 or highest-influence sensitivity. Otherwise use
"weak," "uncertain," or "not supported by these data," with the effect estimate
and interval shown. Failure to meet this rule is not evidence of no biological
effect.

Never describe these analyses as proving thermal stress, disease, mortality,
migration delay, or a causal snowpack-to-salmon pathway. T2 values remain modeled
temperature proxies calibrated to grab samples.

## 7. Execution gate

Before running Phase 7 association code, assert all of the following:

1. proxy coverage is 1995-01-01 through 2025-12-31 with 11,323 daily rows per
   model;
2. A1, A3, and A5 each have exactly 29 eligible return-year rows;
3. A5 maps exposure years 1995-2023 to return years 1997-2025;
4. every primary thermal field identifies T2/window mean;
5. every threshold-count field/status is exploratory only;
6. both T1 and T2 extrapolation audits cover every flagged daily row;
7. `salmon_association_tests_run` remains `false` in the temperature preparation
   gate; and
8. this frozen protocol is committed or its exact SHA-256 is recorded with the
   Phase 7 outputs.

The temperature-proxy build performs input construction and validation only. It
must not import the salmon master table or execute any association test.
