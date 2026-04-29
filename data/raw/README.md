# Data Download Instructions
## Issaquah Creek Salmon Return Study

This directory holds raw, unmodified source files. Do NOT edit these files.
All cleaning happens in `src/data_pipeline.py`.

---

## Required Files

### 1. `wdfw_issaquah_escapement.csv`
**Source:** WA Dept of Fish & Wildlife — Salmonid Stock Inventory (SaSI)
**URL:** https://wdfw.wa.gov/fishing/salmon-science-management
**Steps:**
1. Navigate to "Escapement" database
2. Filter: Stream = "Issaquah Creek", Species = Chinook, Coho
3. Export all years (1985–present) as CSV
**Expected columns:** Year, Species, Stream, Wild_Adults, Hatchery_Adults, Jacks, Total_Return

---

### 2. `fish_hatchery_releases.csv`
**Source:** RMIS (Regional Mark Information System)
**URL:** https://rmis.psmfc.org
**Steps:**
1. Go to "Release" data query
2. Filter: Hatchery = "Issaquah" or "FISH"
3. Select Chinook and Coho, all years
4. Export as CSV
**Expected columns:** Year, Species, Smolts_Released, Avg_Weight_g, Release_Date

*Alternative:* Request directly from FISH volunteer coordinator.

---

### 3. `king_county_impervious.csv`
**Source:** NLCD (National Land Cover Database) + King County GIS
**URL:** https://www.mrlc.gov (NLCD) | https://kingcounty.gov/services/gis
**Steps:**
1. Download NLCD impervious surface rasters for available years:
   2001, 2004, 2006, 2008, 2011, 2013, 2016, 2019, 2021
2. Clip to Issaquah Creek watershed boundary
3. Calculate % impervious surface per year
4. Save as CSV
**Expected columns:** Year, Watershed_Area_km2, Impervious_km2, Impervious_Pct

*Note:* Only available every 2–3 years; pipeline interpolates to annual.

---

## Auto-Fetched Data (no download needed)

The following are pulled directly by `data_pipeline.py` via API:

| File | Source | API |
|------|--------|-----|
| `usgs_issaquah_creek.csv` | USGS Gauge 12121600 | `dataretrieval` library |
| `snotel_stampede_pass.csv` | NRCS SNOTEL Station 769 | NRCS REST API |
| `noaa_pdo_index.csv` | NOAA PSL PDO dataset | Direct CSV download |

To cache these files locally (recommended for reproducibility):
```python
from src.data_pipeline import fetch_usgs_annual, fetch_snotel_swe, fetch_pdo_index
fetch_usgs_annual().to_csv('data/raw/usgs_issaquah_creek.csv', index=False)
fetch_snotel_swe().to_csv('data/raw/snotel_stampede_pass.csv', index=False)
fetch_pdo_index().to_csv('data/raw/noaa_pdo_index.csv', index=False)
```
