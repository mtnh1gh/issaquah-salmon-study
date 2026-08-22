# Issaquah Creek daily temperature proxy models

## Status and intended use

`src/calculate_issaquah_temp.py` generates two complete 1997-2025 daily
temperature **proxy models** for Issaquah Creek at King County station 0631
(SE 56th Street). The values are model estimates calibrated to local grab
samples. They are not continuous logger observations and are not a replacement
for a future continuous in-stream dataset.

The proxies are suitable for exploratory sensitivity analyses when their
modeled value-status labels are retained. They must not be relabeled `observed`,
`measured`, or `derived_from_observed_measurements`.

## Inputs

| Input | Role | Coverage used |
|---|---|---|
| [King County Water Quality station 0631](https://data.kingcounty.gov/resource/vwmt-pvjw.csv) | Calibration target: grab-sample water temperature at Issaquah Creek, SE 56th St | 385 unique sample dates (397 raw samples), 1997-2025 |
| [USGS station 12121600](https://waterdata.usgs.gov/nwis/uv?legacy=1&site_no=12121600) | Daily mean discharge for T1 only | 1996-12-03 through 2025-12-31 |
| [NOAA GHCN-Daily USW00024233](https://www.ncei.noaa.gov/cdo-web/datasets/GHCND/stations/GHCND%3AUSW00024233/detail) | Daily minimum and maximum air temperature | 1996-12-03 through 2025-12-31 |

Sea-Tac is used because it provides the complete long record required by the
study. The closer GHCN Issaquah station does not return temperature records for
1997-2025, and Renton Municipal Airport begins in October 1998.

Raw API responses are cached under
`data/bronze/temperature_proxy/<access-date>/`. `source_manifest.json` records
the exact URLs and SHA-256 hashes. Once a dated source file exists, normal runs
reuse it rather than overwrite it.

## Models

The response is same-date King County grab-sample water temperature in degrees
Celsius. Multiple measurements on one date are averaged before calibration.

Both models use ridge-regularized linear regression with standardized
predictors and the same calibration observations:

| Model | Predictors | Purpose |
|---|---|---|
| T1 — full proxy | Daily air midpoint/range; trailing 3-, 7-, and 30-day air means; `log1p` daily and trailing 7-day flow; annual and semiannual seasonal terms | Full air-flow-season model |
| T2 — independent-of-flow proxy | Daily air midpoint/range; trailing 3-, 7-, and 30-day air means; annual and semiannual seasonal terms | Sensitivity model with no USGS flow variables |

The ridge penalty is selected from `0.01, 0.1, 1, 10, 100` using
leave-one-year-out validation. Each validation fold withholds every local water
temperature observation from one calendar year. The selected 2026-08-22 T1 and
T2 models both use alpha 10.

One missing Sea-Tac TMIN observation on 2024-04-25 is linearly interpolated
between adjacent days and explicitly flagged. The script permits only bounded
internal predictor gaps of three days or fewer; it stops on larger gaps.

## Validation results

| Metric | T1 full proxy | T2 air + season | Held-out monthly climatology |
|---|---:|---:|---:|
| Leave-year-out RMSE | 0.786 C | 0.790 C | 1.534 C |
| Leave-year-out MAE | 0.615 C | 0.619 C | 1.202 C |
| Leave-year-out R-squared | 0.957 | 0.957 | 0.837 |

T1 reduces held-out RMSE by 48.8% and T2 by 48.5% relative to the seasonal
baseline. T2 RMSE is only 0.6% higher than T1 RMSE. Each model's empirical 95%
interval uses its own 2.5th and 97.5th percentiles of leave-year-out residuals:
approximately -1.47 C to +1.45 C for T1 and -1.50 C to +1.50 C for T2. These
intervals describe observed cross-validation error; they do not capture every
source or structural uncertainty.

Each generated series contains 10,592 consecutive dates, no missing predictors
or modeled values, no non-finite values, and no point predictions requiring the
0-30 C physical bounds. T1 flags 295 days and T2 flags 238 days because at least
one applicable measured/derived predictor is outside the range represented on
grab-sample dates.

## Outputs

- T1 outputs retain the original filenames:
  `issaquah_creek_daily_temperature_proxy_1997_2025.csv`,
  `issaquah_creek_annual_temperature_proxy_1997_2025.csv`,
  `issaquah_temperature_proxy_calibration.csv`, and
  `issaquah_temperature_proxy_diagnostics.json`.
- T2 outputs are explicitly named `*_t2_air_seasonal_*` and contain no USGS
  flow columns or flow-derived model features.
- `issaquah_temperature_proxy_model_comparison.csv` provides a compact held-out
  performance comparison between T1 and T2.

Daily files contain the point estimate, empirical interval, local grab
observations where available, modeled seven-day mean, and quality flags. Annual
files contain exploratory summaries. Calibration files retain each unique-date
observation and its held-out-year prediction. Diagnostic JSON files record the
model specification, feature list, coefficients, validation, and limitations.

## Important 7DADMax limitation

In both models, `modeled_7day_mean_proxy_c` is the seven-day average of the
modeled daily grab-temperature proxy. It is **not 7DADMax**, because the
calibration data do not identify daily in-stream maxima. The annual field
`annual_max_modeled_7day_mean_proxy_c` is the highest such modeled proxy window,
not a regulatory or observed maximum 7DADMax value.

If a continuous logger dataset becomes available, replace the response with
observed daily maximum temperature, refit and revalidate the model, and only
then calculate and label 7DADMax.

## Reproduction

To reproduce the accepted snapshot without network access:

```powershell
python src/calculate_issaquah_temp.py --snapshot-date 2026-08-22 --offline
```

To acquire a new dated snapshot and rebuild:

```powershell
python src/calculate_issaquah_temp.py --snapshot-date YYYY-MM-DD
```

The command generates both T1 and T2. The script exits unsuccessfully if source
schemas change, required daily values remain missing, physical checks fail,
yearly calibration coverage is absent, either model contains an invalid feature
set, or either model does not beat the held-out seasonal baseline.
