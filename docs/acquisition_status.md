# Week 2 acquisition status — 2026-07-19

## Completed public-source snapshots

| Status | Source | Result |
|---|---|---|
| Acquired and structurally validated | USGS daily discharge, station 12121600 | 14,245 daily values for parameter `00060`, 1986-10-01 through 2025-09-30. |
| Acquired and structurally validated | NRCS Stampede Pass SNOTEL 788 daily SWE | 15,524 daily records, 1982-10-01 through 2025-04-01. |
| Acquired and structurally validated | NOAA PDO ERSSTv5 monthly index | Original monthly series cached; valid values currently extend through 2026-06; `-9999` is a missing-value marker. |
| Acquired and structurally validated | WDFW Hatchery Adult Salmon Returns, Issaquah subset | 3,958 public event records (2,073 Chinook; 1,885 Coho), 1995-09-25 through 2025-11-18; raw CSV and schema metadata are cached. |
| Acquired and structurally validated | King County Issaquah Creek water temperature | 1,218 grab samples, 1972-01-04 through 2026-05-13: 674 at SE 56th St and 544 upstream of hatchery. |

All raw paths, checksums, source URLs, and limitations are recorded in `docs/source_register.csv` and `docs/data_inventory.csv`.

## Critical-path items still required

### 1. WDFW annual response series — definition pending

The raw machine-readable event series is now available for both species and spans 31 calendar years. It contains several handling-event categories, so it is not yet an annual response table: summing all rows would double count fish.

Required next action:

1. Approve a non-overlapping return/escapement definition using the event categories and origin designations.
2. Record jacks treatment and the reporting-year convention.
3. Reconcile a small sample of annual totals to the WDFW annual reports before aggregation.
4. Produce the annual response table only after those checks.

### 2. RMIS/FISH hatchery releases — API access blocked

The documented RMIS API is available at `https://phish.rmis.org/release`, but a read-only request returned HTTP 401 (`No authorization token`). Its published API specification declares API-key/JWT authentication. The cached OpenAPI schema and probe response are retained under `data/raw/rmis/2026-07-19/`.

Required next action:

1. Query release records for Issaquah Hatchery and relevant Issaquah Creek release locations, separately by Chinook and Coho.
2. Export fields for release year/date, species/stock, life stage, release number, release location, marks, and data owner.
3. Save the unmodified export under `data/raw/rmis/<access-date>/` and add it to both registers.
4. Do not merge releases until the cohort/life-stage lag table is approved.

### 3. Water temperature — source acquired; feature definition pending

USGS station 12121600 still supplies discharge only. A King County public water-quality export now supplies temperature grab samples at two relevant Issaquah Creek sites. Select the station, required within-year sample coverage, and seasonal/annual aggregation before including temperature as a predictor; the source is not a continuous temperature record.

### 4. Imperviousness and watershed boundary — not started

Acquire/approve the Issaquah Creek watershed boundary first. Only then obtain land-cover rasters and calculate imperviousness with the documented GIS procedure.

## Week 2 gate status

**Conditional / not yet passed.** Public environmental inputs and the raw primary response source are now available. The response definition/reconciliation and hatchery-release series are still required before cleaning or modeling.

## Data collection continuation — 2026-07-26

The watershed-boundary prerequisite for land-use collection is complete. The King County GIS `TOPO_BASIN_KC_AREA` feature named `Issaquah Creek` was exported as a one-feature GeoJSON in EPSG:4326, along with complete ArcGIS layer and item metadata.

Validation results:

- Polygon feature count: 1
- Basin: Issaquah Creek
- Watershed: Sammamish River
- WRIA: 8, Cedar-Sammamish
- Provider-reported area: 1,626,744,001 square feet (58.351 square miles; 37,344.9 acres)
- Raw snapshot and both metadata files have SHA-256 checksums in `docs/data_inventory.csv`

The boundary is approved for analytical clipping under decision D-008. King County's item terms restrict reproduction or redistribution of the digital product without express written authorization, so the raw polygon should not be included in a published data release without permission.

Next collection action: identify the authoritative annual NLCD fractional-impervious product, select observation years that support the annual study design, and acquire only the raster coverage needed for this approved basin.

## Response and feature preparation — 2026-07-26

The WDFW response-definition gate is now passed for the available period. Annual adult returns are calculated only from `Trap Estimate` events, with hatchery and wild origins retained separately and jacks excluded from the primary response. Published WDFW figures for 2016 and 2025 are enforced as reconciliation checks in the build script.

King County station 0631 at SE 56th St is selected for the initial June–September temperature index. It supplies at least four grab samples in every response year; the upstream station is not selected because it has no 2009–2012 observations.

Annual environmental summaries have been built for 1992–2025, with five pre-response years retained to support cohort lags. The provisional master table covers 1997–2025 and includes explicit cohort alignment, provenance, and value-status fields. It deliberately leaves imperviousness and hatchery releases blank.

The Phase 2 validation gate passed all 14 critical checks: schema, keys, coverage, row counts, physical ranges, response reconciliation, WDFW published totals, temporal alignment, core missingness, blocker flags, temperature coverage, provenance, and feature-registry integrity. A repeated cached-input rebuild produced byte-identical processed outputs.

Annual NLCD Collection 1.2 Fractional Impervious Surface is the approved land-use source. Official metadata are cached and an isolated raster-capable environment was prepared. Raster extraction is still pending because the MRLC WCS capabilities request timed out after two minutes and the official cloud mosaic returned requester-pays access responses. The remaining supported path is the provider's email-delivered AOI download or authorized requester-pays cloud access.
