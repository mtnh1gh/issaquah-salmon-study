# 🐟 Issaquah Creek Salmon Return Study
### Quantitative Analysis, Impact Assessment & AI-Driven Forecasting
**Summer 2025 | In partnership with [Friends of the Issaquah Salmon Hatchery (FISH)](https://issaquahsalmon.org)**

---

## 🌊 Project Overview

Each fall, Chinook and Coho salmon return from the Pacific Ocean to spawn in Issaquah Creek — swimming through downtown Issaquah past shopping centers, neighborhoods, and the I-90 corridor. In 2025, **4,955 Chinook** and **5,200+ Coho** returned to this creek. But are those numbers going up or down over time — and why?

This project uses Python and PowerShell data pipelines to:
1. **Quantify** salmon return trends (1997–2025) alongside environmental stressors
2. **Test** which factors (streamflow, snowpack, water temperature, ocean conditions) are associated with Issaquah Creek returns
3. **Illustrate** conditional Coho return sensitivity through 2040 under observed-predictor scenarios

Every acquisition, cleaning step, and modeling decision is logged in `docs/` with an explicit gate process (Phase 2 data validation → Phase 3 EDA → Phase 4 statistical modeling → Phase 5 uncertainty → Phase 6 scenarios), so results can be reproduced and audited end to end. The results are shared as an open dataset and a draft awareness report for City of Issaquah, City of Sammamish, and King County decision-makers, pending domain-partner review (see `docs/decision_log.md`, D-017).

---

## 📁 Repository Structure

Data flows through a **Bronze → Silver → Gold** pipeline:

```
issaquah-salmon-study/
├── data/
│   ├── bronze/             # Raw, immutable, checksummed source snapshots (data/bronze/<source>/<date>/)
│   ├── silver/              # Cleaned, source-conformed annual tables
│   └── gold/                 # Joined, cohort-aligned, model-ready master table
├── docs/                     # Source/decision/validation registers + analysis & final reports
├── src/
│   ├── build_*.ps1           # Bronze -> Silver -> Gold build scripts
│   ├── run_*.py               # Phase 3-6 EDA, modeling, uncertainty, and scenario scripts
│   └── validate_*.py/.ps1    # Per-phase validation gates
├── outputs/
│   ├── figures/               # Publication-quality charts (PNG)
│   └── tables/                 # Analysis and model result tables (CSV)
├── requirements.txt
└── README.md
```

See `docs/project_scope_and_execution_plan.md` for the full pipeline architecture and phase gates, and `docs/decision_log.md` for the rationale behind every material data/method decision (including D-018, formalizing this Bronze/Silver/Gold layout).

---

## 🗃️ Data Sources

| Data | Source | Notes |
|------|--------|-------|
| Salmon returns | [WDFW Hatchery Adult Salmon Returns](https://data.wa.gov/resource/9q4e-xhag.csv) | Issaquah Hatchery / Issaquah Creek stock, 1995–2025; annual response built from `Trap Estimate` events only (D-009) |
| Streamflow | [USGS Gauge 12121600](https://waterdata.usgs.gov/nwis/uv?site_no=12121600) | Discharge only — this gauge does not report water temperature (D-001) |
| Water temperature | [King County Water Quality](https://data.kingcounty.gov/resource/vwmt-pvjw.csv) | Grab samples, Issaquah Creek at SE 56th St, June–Sept index (D-010) |
| Snowpack (SWE) | [NRCS SNOTEL Station 788](https://wcc.sc.egov.usda.gov/nwcc/site?sitenum=788) | Stampede Pass, April 1 SWE |
| Ocean conditions | [NOAA PDO Index (ERSSTv5)](https://psl.noaa.gov/pdo/) | Pacific Decadal Oscillation, monthly |
| Hatchery releases | RMIS | **Blocked** — API requires authorization not yet obtained (D-005); excluded from the master table |
| Land use / imperviousness | [Annual NLCD Fractional Impervious Surface](https://doi.org/10.5066/P94UXNTS) | **Pending** — metadata cached, raster extraction blocked on tooling access (D-011); excluded from the master table |

---

## ⚙️ Setup & Reproducibility

```bash
# 1. Clone the repo
git clone https://github.com/mtnh1gh/issaquah-salmon-study.git
cd issaquah-salmon-study

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt
```

Rebuild the pipeline in order (PowerShell):

```powershell
src/build_annual_returns.ps1       # data/bronze -> data/silver (WDFW response table)
src/build_annual_environment.ps1   # data/bronze -> data/silver (environmental predictors)
src/build_analysis_table.ps1       # data/silver -> data/gold (joined master table)
src/validate_phase2.ps1            # re-run the 14 critical Phase 2 checks
```

Then run the analysis phases (Python):

```bash
python src/run_eda.py               # Phase 3 — trends, correlations, lag sensitivity
python src/run_phase4_models.py     # Phase 4 — association models vs. naive baselines
python src/run_phase5_uncertainty.py
python src/run_phase6_scenarios.py
python src/run_phase6_dynamic.py
```

Each build script re-derives a byte-identical output from its cached Bronze inputs (D-012) — nothing here calls a live API at run time.

---

## 📊 Key Findings

Full detail in `docs/eda_report.md`, `docs/statistical_analysis_report.md`, `docs/model_registry.md`, and the synthesized `docs/final_awareness_report.md`. See `docs/model_summary.md` for a plain-language walkthrough of the modeling method (feature sets, validation design, and how the 2026–2040 scenarios are generated).

- **No statistically significant 40-year trend** in either species after correcting for multiple testing (Chinook Mann-Kendall τ = -0.118, Coho τ = -0.044; both adjusted p = 0.857), despite real shifts in the underlying environment (April 1 snowpack down, summer water temperature up, PDO regime shift).
- **No Chinook model beats a naive "same as last year" baseline** — treat Chinook results as descriptive trend/association findings only, not a forecasting model.
- **3 of 6 Coho models modestly outperform naive baselines on error** (MAE), but R² remains negative — skill relative to a weak baseline, not absolute predictive accuracy.
- **2030/2040 projections exist only for Coho**, explicitly framed as illustrative sensitivity to observed-predictor quantiles, not a forecast (88.2% empirical interval coverage vs. nominal 95%).

---

## 📄 Awareness Report

The draft report for non-technical stakeholders (City of Issaquah, City of Sammamish, FISH leadership) is `docs/final_awareness_report.md`, backed by the figures in `outputs/figures/` and tables in `outputs/tables/`. Per `docs/decision_log.md` (D-017), it is a reproducible draft pending domain-partner review — not a final management decision document.

---

## 🤝 Acknowledgments

- **Friends of the Issaquah Salmon Hatchery (FISH)** — domain expertise and hatchery data access
- **WDFW** — salmon escapement records
- **USGS** — streamflow data
- **NRCS** — SNOTEL snowpack data
- **King County** — water quality and GIS data

---

## 📜 License

Data outputs and code are released under MIT License. Raw data from government sources retains original agency terms of use. The King County watershed boundary is subject to redistribution restrictions (see `docs/decision_log.md`, D-008).
