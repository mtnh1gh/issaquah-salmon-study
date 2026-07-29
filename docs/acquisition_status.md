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

The documented RMIS API is available at `https://phish.rmis.org/release`, but a read-only request returned HTTP 401 (`No authorization token`). Its published API specification declares API-key/JWT authentication. The cached OpenAPI schema and probe response are retained under `data/bronze/rmis/2026-07-19/`.

Required next action:

1. Query release records for Issaquah Hatchery and relevant Issaquah Creek release locations, separately by Chinook and Coho.
2. Export fields for release year/date, species/stock, life stage, release number, release location, marks, and data owner.
3. Save the unmodified export under `data/bronze/rmis/<access-date>/` and add it to both registers.
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

## Candidate-data exploration — 2026-07-29

Prompted by a request to identify additional data that could strengthen the analysis. This pass acquired two new clean numeric candidate sources and cached three supporting/qualitative documents; nothing here has been added to `src/feature_registry.csv` as `included_in_model: yes` or wired into the Phase 3–6 scripts — that requires the same decision/approval step every other feature went through.

### RMIS hatchery releases — re-confirmed blocked, no anonymous path exists

Re-checked whether an unauthenticated path exists beyond the API probe in D-005. The RMPC public site's `data-selection/rmis-files/`, `data-selection/rmis-queries/`, and `data-selection/find-tag/` pages were inspected directly: every one of them routes exclusively to the same login-gated `rmis.org` system (`rmis_login.php`) for both the `cwt` and `rar` systems, with no anonymous query or bulk-file path. The Issaquah hatchery's own public site (`issaquahfish.org/operations/`) was also checked as an alternative; it states only a static typical annual production figure ("roughly 3,500,000 Chinook and 1,000,000 coho," "about half a million yearling coho and 3 million juvenile Chinook" released each spring) with no year-by-year records or dates. **No path to an annual, cohort-aligned release series was found without direct RMIS authorization or a bespoke data request to FISH/WDFW.** R-003 and D-005 stand as written.

### New candidate ocean-condition indices — acquired, not yet integrated

Two additional marine-condition proxies were downloaded as clean numeric series, cached under `data/bronze/npgo/2026-07-29/` and `data/bronze/noaa_oni/2026-07-29/`, and registered in both `docs/source_register.csv` and `docs/data_inventory.csv`:

- **NPGO** (North Pacific Gyre Oscillation), monthly, 1950–2025 — often reported as a stronger Pacific NW salmon-survival correlate than PDO in the literature, since it captures gyre-scale circulation/productivity rather than just SST.
- **ONI** (Oceanic Nino Index), seasonal, 1950–2026 — a distinct El Nino/La Nina signal, uncorrelated enough with PDO/NPGO to be worth testing separately rather than assumed redundant.

Both need the same seasonal-aggregation-and-lag-definition decision that PDO already went through (see D-with-pending-number below) before either can enter `feature_registry.csv` as an active predictor.

### New supporting documents — pinniped predation and harvest management

Three PDF reports were cached as qualitative/supporting evidence, the same tier as the legacy WDFW escapement PDFs (D-003) — none contain a machine-extracted numeric series, since no PDF-parsing tool is available in this environment:

- `data/bronze/pinniped_predation/2026-07-29/wdfw_pinniped_predation_salish_sea_outer_coast.pdf` — statewide WDFW pinniped-predation assessment.
- `data/bronze/pinniped_predation/2026-07-29/ballard_locks_pinniped_mgmt_recommendations_2024.pdf` — WRIA 8 (the same Cedar-Sammamish watershed group as Issaquah Creek) technical workshop recommendations specifically on pinniped predation at the Ballard Locks, the choke point every Issaquah Creek adult return must pass through en route from Puget Sound via Lake Washington. **Fetched without TLS certificate verification** — the source server presented a King County multi-domain certificate that does not list `govlink.org` as a subject alternative name. The cached SHA-256 fixes what was retrieved, but treat this document as unverified pending a re-fetch from a certificate-valid mirror.
- `data/bronze/harvest_management/2026-07-29/wdfw_tribal_2025_management_objectives_chinook_coho.pdf` and `wdfw_puget_sound_chinook_comprehensive_mgmt_plan.pdf` — WDFW/tribal co-manager harvest and exploitation-rate framework documents for Puget Sound Chinook/Coho, relevant because escapement counts already net out pre-terminal harvest, a source of return variance not represented in any current feature.

A Columbia River/Bonneville-focused USACE pinniped report was also fetched during this pass and then discarded after review showed it covers a different watershed (hundreds of miles away, unrelated to Lake Washington/Issaquah Creek) — noted here so the omission isn't mistaken for an oversight.

### Recommended next decision-log entries

None of the above have decision-log entries yet because none has been approved as an active feature — that step is intentionally left for the project lead, matching how every other feature in `feature_registry.csv` was added only after an explicit accepted decision.
