# Bronze layer — raw source snapshots
## Issaquah Creek Salmon Return Study

This directory holds immutable, as-fetched source data. Do NOT edit files here —
never overwrite a snapshot; a re-acquisition gets a new `<accessed-on-date>/` folder.
Cleaning and standardization happen downstream, producing `data/silver/`.

Each source lives under `<source>/<access-date>/`. Every file is registered with
its SHA-256 checksum, access date, and status in `docs/source_register.csv` and
`docs/data_inventory.csv` — those two files are the authoritative index of what
was acquired, when, and from where.

| Folder | Source | Contents |
|---|---|---|
| `usgs/` | USGS NWIS gauge 12121600 | Daily discharge (parameter 00060) |
| `nrcs/` | NRCS SNOTEL station 788 (Stampede Pass) | Daily snow water equivalent |
| `noaa/` | NOAA PSL | PDO monthly index (ERSSTv5) |
| `king_county/` | King County Water Quality | Issaquah Creek temperature grab samples |
| `wdfw/` | WDFW open data | Hatchery adult salmon return events, Issaquah subset |
| `rmis/` | PSMFC RMIS | Hatchery release API probe (blocked — see `docs/decision_log.md` D-005) |
| `king_county_gis/` | King County GIS | Issaquah Creek watershed basin boundary + metadata |
| `nlcd/` | USGS/MRLC | Annual NLCD Fractional Impervious Surface metadata (raster extraction pending) |
| `wdfw_legacy_reports/` | WDFW PDFs | Supporting-only annual/weekly escapement reports — not the analytical response source (D-003) |

See `docs/acquisition_status.md` for what's acquired vs. still blocked, and
`docs/decision_log.md` for the rationale behind each source selection.
