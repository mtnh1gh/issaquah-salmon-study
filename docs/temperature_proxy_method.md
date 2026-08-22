# Issaquah Creek daily temperature proxy

## Status and intended use

`src/calculate_issaquah_temp.py` generates a complete 1997-2025 daily
temperature **proxy** for Issaquah Creek at King County station 0631 (SE 56th
Street). The values are model estimates calibrated to local grab samples. They
are not continuous logger observations and are not a replacement for a future
continuous in-stream dataset.

The proxy is suitable for exploratory sensitivity analyses when every modeled
value retains the status `modeled_proxy_calibrated_to_grab_samples`. It must not
be relabeled `observed`, `measured`, or `derived_from_observed_measurements`.

## Inputs

| Input | Role | Coverage used |
|---|---|---|
| [King County Water Quality station 0631](https://data.kingcounty.gov/resource/vwmt-pvjw.csv) | Calibration target: grab-sample water temperature at Issaquah Creek, SE 56th St | 385 unique sample dates (397 raw samples), 1997-2025 |
| [USGS station 12121600](https://waterdata.usgs.gov/nwis/uv?legacy=1&site_no=12121600) | Daily mean discharge | 1996-12-03 through 2025-12-31 |
| [NOAA GHCN-Daily USW00024233](https://www.ncei.noaa.gov/cdo-web/datasets/GHCND/stations/GHCND%3AUSW00024233/detail) | Daily minimum and maximum air temperature | 1996-12-03 through 2025-12-31 |

Sea-Tac is used because it provides the complete long record required by the
study. The closer GHCN Issaquah station does not return temperature records for
1997-2025, and Renton Municipal Airport begins in October 1998.

Raw API responses are cached under
`data/bronze/temperature_proxy/<access-date>/`. `source_manifest.json` records
the exact URLs and SHA-256 hashes. Once a dated source file exists, normal runs
reuse it rather than overwrite it.

## Model

The response is same-date King County grab-sample water temperature in degrees
Celsius. Multiple measurements on one date are averaged before calibration.

The model is ridge-regularized linear regression with standardized predictors:

- daily air midpoint and air-temperature range;
- trailing 3-, 7-, and 30-day air midpoint means;
- `log1p` daily flow and its trailing 7-day mean; and
- annual and semiannual sine/cosine seasonal terms.

The ridge penalty is selected from `0.01, 0.1, 1, 10, 100` using
leave-one-year-out validation. Each validation fold withholds every local water
temperature observation from one calendar year. The selected 2026-08-22 model
uses alpha 10.

One missing Sea-Tac TMIN observation on 2024-04-25 is linearly interpolated
between adjacent days and explicitly flagged. The script permits only bounded
internal predictor gaps of three days or fewer; it stops on larger gaps.

## Validation results

| Metric | Hybrid model | Held-out monthly climatology |
|---|---:|---:|
| Leave-year-out RMSE | 0.786 C | 1.534 C |
| Leave-year-out MAE | 0.615 C | 1.202 C |
| Leave-year-out R-squared | 0.957 | 0.837 |

The hybrid model reduces held-out RMSE by 48.8% relative to the seasonal
baseline. Its empirical 95% interval uses the 2.5th and 97.5th percentiles of
leave-year-out residuals (approximately -1.47 C and +1.45 C). This interval
describes observed cross-validation error; it does not capture every source or
structural uncertainty.

The generated series contains 10,592 consecutive dates, no missing predictors
or modeled values, no non-finite values, and no point predictions requiring the
0-30 C physical bounds. A total of 295 days are flagged because at least one
air/flow predictor is outside the range represented on grab-sample dates.

## Outputs

- `outputs/temperature_proxy/issaquah_creek_daily_temperature_proxy_1997_2025.csv`
  contains daily predictors, the point estimate, empirical interval, local grab
  observations where available, the modeled seven-day mean, and quality flags.
- `outputs/temperature_proxy/issaquah_creek_annual_temperature_proxy_1997_2025.csv`
  contains annual exploratory summaries.
- `outputs/temperature_proxy/issaquah_temperature_proxy_calibration.csv`
  contains every unique-date calibration observation and its held-out-year
  prediction.
- `outputs/temperature_proxy/issaquah_temperature_proxy_diagnostics.json`
  records model selection, coefficients, validation metrics, coverage, and
  limitations.

## Important 7DADMax limitation

`modeled_7day_mean_proxy_c` is the seven-day average of the modeled daily
grab-temperature proxy. It is **not 7DADMax**, because the calibration data do
not identify daily in-stream maxima. The annual field
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

The script exits unsuccessfully if source schemas change, required daily values
remain missing, physical checks fail, yearly calibration coverage is absent, or
the hybrid model does not beat the held-out seasonal baseline.
