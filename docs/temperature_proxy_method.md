# Issaquah Creek daily temperature proxy models

## Status and intended use

`src/calculate_issaquah_temp.py` generates two complete 1995-2025 daily water-
temperature proxy models for Issaquah Creek at King County station 0631 (SE 56th
Street). Starting in 1995 supplies the Coho A5 exposure years needed for every
1997-2025 adult return year.

The values are ridge-regression estimates calibrated to local grab samples.
They are not continuous logger observations, daily maxima, or regulatory
7DADMax. Modeled value-status labels must be retained.

For Phase 7:

- **Primary thermal variable:** T2 biological-window mean, stored as
  `primary_thermal_value_c` / `t2_window_mean_proxy_c`.
- **Model sensitivity:** T1 mean over the identical dates.
- **Exploratory only:** threshold-day counts, warm-spell length, modeled daily
  maximum, and modeled maximum seven-day mean.

The frozen statistical definitions are in
[`phase7_hypothesis_analysis_protocol.md`](phase7_hypothesis_analysis_protocol.md).

## Inputs

| Input | Role | Coverage used |
|---|---|---|
| [King County Water Quality station 0631](https://data.kingcounty.gov/resource/vwmt-pvjw.csv) | Calibration target: same-date grab-sample water temperature | 415 unique dates (431 raw samples), 1995-2025 |
| [USGS station 12121600](https://waterdata.usgs.gov/nwis/uv?legacy=1&site_no=12121600) | Daily mean discharge for T1 and matched-window flow summaries | 1994-12-03 through 2025-12-31 |
| [NOAA GHCN-Daily USW00024233](https://www.ncei.noaa.gov/cdo-web/datasets/GHCND/stations/GHCND%3AUSW00024233/detail) | Daily minimum and maximum regional air temperature | 1994-12-03 through 2025-12-31 |

The 29-day lead-in supports trailing predictors on 1995-01-01. Sea-Tac is used
because it supplies the required complete long record; it remains a regional
air-temperature proxy rather than a watershed weather station. One missing
Sea-Tac TMIN observation on 2024-04-25 is linearly interpolated between adjacent
days and explicitly flagged. Gaps longer than three days stop the build.

Raw responses are cached under `data/bronze/temperature_proxy/<access-date>/`.
The accepted extension is the immutable 2026-08-23 snapshot; its manifest stores
the exact URLs and SHA-256 hashes.

## Models and Phase 7 designation

Both models predict same-date King County grab-sample temperature. Multiple
measurements on one date are averaged before calibration. Predictors are
standardized, and the ridge penalty is selected from `0.01, 0.1, 1, 10, 100`
using leave-one-year-out validation.

| Model | Predictors | Phase 7 role |
|---|---|---|
| T2 - independent of flow | Daily air midpoint/range; trailing 3-, 7-, and 30-day air means; annual and semiannual seasonal terms | **Primary model; window mean only** |
| T1 - full proxy | T2 predictors plus `log1p` daily and trailing seven-day streamflow | Sensitivity model |

T2 is primary because it performs similarly to T1 and avoids mathematical
coupling when streamflow is tested against temperature or entered beside it.
Both selected alpha 10 in the accepted 2026-08-23 build.

## Validation results

| Metric | T2 primary | T1 sensitivity | Held-out monthly climatology |
|---|---:|---:|---:|
| Leave-year-out RMSE | 0.788 C | 0.781 C | 1.527 C |
| Leave-year-out MAE | 0.618 C | 0.610 C | 1.198 C |
| Leave-year-out R-squared | 0.955 | 0.956 | 0.832 |

T2 RMSE is 0.9% higher than T1. T2 and T1 improve RMSE over the held-out
climatology by 48.4% and 48.9%, respectively. This small difference does not
outweigh T2's independence from flow for the Phase 7 design.

### Primary hypothesis-window validation

These are subsets of the already-held-out predictions; models are not refit by
window and no salmon outcome is read or tested.

| Window | Analysis | Grab dates | T2 RMSE / MAE | T1 RMSE / MAE | T2 minus T1 RMSE |
|---|---|---:|---:|---:|---:|
| Jun 1-Sep 30 | A5 Coho juvenile/rearing | 135 | 0.970 / 0.764 C | 0.973 / 0.773 C | -0.003 C |
| Aug 15-Sep 30 | A1 Chinook adult migration | 42 | 0.771 / 0.620 C | 0.766 / 0.616 C | +0.005 C |
| Sep 15-Oct 31 | A3 Coho adult migration | 43 | 0.696 / 0.542 C | 0.685 / 0.530 C | +0.011 C |

All 31 calibration years are represented. Both models beat the window-specific
held-out monthly climatology in every window. The performance differences are
small relative to held-out error.

## Extrapolation audits

Each daily file flags a day when at least one measured or derived predictor is
outside its range on calibration grab dates. The two detailed audits use the
same normalized-distance severity definitions and preserve offending features,
dates, season/window membership, T1/T2 estimates, and same-day observations.

| Audit | Flagged days | Percent of 11,323 days | June-Oct flags | Same-day grabs on flags |
|---|---:|---:|---:|---:|
| T2 primary | 248 | 2.19% | 54 | 0 |
| T1 sensitivity | 304 | 2.68% | 102 | 0 |

For T2's 54 June-October flags, 45 are within 5% of the calibration span, eight
are 5-20% beyond, and one is over 20% beyond. The sole over-20% date is
2021-06-28 during the regional heat dome; its largest air-predictor departure is
26.3% of that predictor's calibration span. T2 predicts 19.788 C and T1 predicts
19.779 C. Agreement between models does not validate the unobserved water
temperature.

T2 has fewer flags because it contains no flow predictors. Audit severity is a
descriptive input-domain screen, not a confidence level or observed-error test.

## Life-stage exposure table

The table contains 31 exposure years multiplied by five Phase 7 windows (155
rows). Three primary analyses and two frozen window sensitivities are explicit:

| Analysis | Species/life stage | Window | Alignment | Role |
|---|---|---|---|---|
| A1 | Chinook adult migration | Aug 15-Sep 30 | same return year | Primary |
| A2 | Chinook adult migration | Aug 15-Oct 31 | same return year | Window sensitivity |
| A3 | Coho adult migration | Sep 15-Oct 31 | same return year | Primary |
| A4 | Coho adult migration | Sep 15-Nov 30 | same return year | Window sensitivity |
| A5 | Coho juvenile/rearing | Jun 1-Sep 30 | exposure year = return year - 2 | Primary |

For each analysis, exactly 29 rows are marked
`return_year_eligible_for_phase7 == true`. A5 maps 1995-2023 exposures to every
1997-2025 Coho return. Extra environmental rows remain available for physical
mechanism checks but cannot be joined to nonexistent response years.

Every row contains the T2 primary mean, T1 sensitivity mean, matched-window
USGS flow, model-specific extrapolation counts, and exploratory nonmean thermal
summaries. Field names and status columns make the analysis boundary machine-
readable. `issaquah_temperature_proxy_preassociation_validation.json` records
the construction gate and `salmon_association_tests_run: false`.

## Outputs

- T2 primary daily and annual files:
  `issaquah_creek_daily_temperature_proxy_t2_air_seasonal_1995_2025.csv` and
  `issaquah_creek_annual_temperature_proxy_t2_air_seasonal_1995_2025.csv`.
- T1 sensitivity daily and annual files:
  `issaquah_creek_daily_temperature_proxy_1995_2025.csv` and
  `issaquah_creek_annual_temperature_proxy_1995_2025.csv`.
- Model calibrations, diagnostics, held-out comparison, and primary-window
  validation remain separate model-labeled artifacts.
- `issaquah_temperature_proxy_t2_extrapolation_audit.csv` and JSON summary are
  the detailed primary-model domain audit; T1 has parallel sensitivity files.
- `issaquah_life_stage_temperature_exposure_1995_2025.csv` is the Phase 7 input
  table; its companion pre-association JSON records the gate.

## 7DADMax and threshold limitation

`modeled_7day_mean_proxy_c` is a seven-day average of modeled grab-temperature
proxies. It is not 7DADMax because the calibration target does not identify
daily in-stream maxima. Threshold counts likewise count modeled mean-like proxy
values, not observed regulatory exceedances. Phase 7 therefore treats every
threshold count and all other nonmean thermal summaries as exploratory only.

If a suitable continuous logger dataset becomes available, the response must be
redefined as observed daily maximum, the model refit and revalidated, and only
then may a metric be labeled 7DADMax.

## Reproduction

Rebuild the accepted snapshot without network access:

```powershell
python src/calculate_issaquah_temp.py --snapshot-date 2026-08-23 --offline
```

The script fails on source/schema changes, unresolved daily gaps, physical-check
failures, missing calibration years, invalid model features, failure to beat the
held-out baseline, incomplete T1/T2 audits, incomplete exposure windows, or loss
of any required 1997-2025 return-year alignment.
