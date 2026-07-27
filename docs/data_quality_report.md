# Data quality report — annual analytical inputs

Updated: 2026-07-26

## Current analytical coverage

The reproducible scripts in `src/` produce:

| Output | Rows | Coverage | Status |
|---|---:|---|---|
| `data/processed/wdfw_issaquah_annual_returns.csv` | 58 | Chinook and Coho, 1997–2025 | Validated |
| `data/processed/issaquah_annual_environment.csv` | 29 | Annual predictors, 1997–2025 | Validated except imperviousness |
| `data/processed/issaquah_creek_master.csv` | 58 | Species-year response and predictors, 1997–2025 | Provisional; releases and imperviousness intentionally blank |

## Response definition

The primary response is the sum of `adult_count` over WDFW `Trap Estimate` events for each return year and species. Hatchery- and wild-origin adults are retained separately and summed to `total_adults`. Jacks are excluded from the primary adult response and retained in separate fields.

This avoids double-counting. Mortality, spawning, surplus, shipping, planting, and egg-take events describe later handling of fish already counted at the trap.

Executable reconciliation checks confirm:

| Year | Species | Hatchery adults | Wild adults | Evidence |
|---:|---|---:|---:|---|
| 2016 | Chinook | 2,442 | 154 | WDFW weekly escapement report |
| 2025 | Chinook | 4,562 | 154 | WDFW final in-season estimate |
| 2025 | Coho | 3,647 | 212 | WDFW final in-season estimate |

Limitations:

- The raw event export contains no `Trap Estimate` rows for 1995 or 1996, so the analytical series begins in 1997.
- WDFW describes in-season figures as preliminary estimates. Revisions should be detected by re-running acquisition and checksum comparison.
- The response represents fish counted at Issaquah Hatchery, not total natural escapement throughout every tributary in the basin.

## Environmental features

| Feature | Definition | Coverage rule |
|---|---|---|
| `flow_water_year_mean_cfs` | Mean daily USGS discharge for water year ending September 30 of return year | 365 or 366 daily values |
| `flow_jul_sep_mean_cfs` | Mean daily discharge, July–September of return year | 92 daily values |
| `flow_jul_sep_min_cfs` | Minimum daily discharge, July–September of return year | 92 daily values |
| `swe_apr01_inches` | NRCS Stampede Pass station 788 start-of-day SWE on April 1 | Exact date |
| `pdo_annual_mean` | Mean of valid NOAA monthly PDO values in return year | 12 months |
| `temp_jun_sep_mean_c` | Arithmetic mean of King County grab samples during June–September | At least 4 samples |

## Temperature station decision

King County station 0631, `Issaquah Creek at SE 56th St`, is selected for the first analytical version.

Reasons:

- It has uninterrupted June–September coverage for every response year from 1997 through 2025.
- It has at least four warm-season samples in every response year.
- The upstream-of-hatchery station has no observations during 2009–2012.
- Station 0631 is also near the USGS discharge station, improving spatial consistency between flow and temperature summaries.

The temperature feature remains a grab-sample index. It must not be described as a continuous record, daily mean, or annual maximum.

## Known missing predictors

`impervious_pct` is blank pending a basin-clipped Annual NLCD Collection 1.2 Fractional Impervious Surface extraction. The official dataset is annual for 1985–2025, so the project should use annual values directly rather than interpolate legacy observation years. A raster-capable project environment is available, but the MRLC WCS timed out and the cloud mosaic requires requester-pays authorization; use the official email-delivered AOI workflow or provide authorized cloud access.

`hatchery_releases` is blank because the RMIS release endpoint requires authorization. It must remain missing until an authenticated export or FISH record set is supplied.

No modeling result should be labeled final while either field is unresolved.

## Reproduction

From the repository root:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\src\build_annual_returns.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\src\build_annual_environment.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\src\build_analysis_table.ps1
```
