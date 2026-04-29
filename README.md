# 🐟 Issaquah Creek Salmon Return Study
### Quantitative Analysis, Impact Assessment & AI-Driven Forecasting
**Summer 2025 | In partnership with [Friends of the Issaquah Salmon Hatchery (FISH)](https://issaquahsalmon.org)**

---

## 🌊 Project Overview

Each fall, Chinook and Coho salmon return from the Pacific Ocean to spawn in Issaquah Creek — swimming through downtown Issaquah past shopping centers, neighborhoods, and the I-90 corridor. In 2025, **4,955 Chinook** and **5,200+ Coho** returned to this creek. But are those numbers going up or down over time — and why?

This project uses Python data science tools to:
1. **Quantify** 40 years of Issaquah Creek salmon return trends alongside environmental stressors
2. **Explain** which factors (urban development, snowpack loss, water temperature, ocean conditions) most impact returns
3. **Predict** future salmon populations under different climate and land-use scenarios through 2040

The results are shared as an open dataset and an awareness report for City of Issaquah, City of Sammamish, and King County decision-makers.

---

## 📁 Repository Structure

```
issaquah-salmon-study/
├── data/
│   ├── raw/               # Original downloaded datasets — never modified
│   └── processed/         # Cleaned, merged master dataset (issaquah_creek_master.csv)
├── notebooks/
│   ├── 01_eda.ipynb       # Exploratory data analysis & trend visualization
│   ├── 02_stats.ipynb     # Statistical analysis & stressor impact ranking
│   └── 03_modeling.ipynb  # XGBoost predictive model & scenario projections
├── src/
│   ├── data_pipeline.py   # Data ingestion & cleaning functions
│   ├── features.py        # Feature engineering utilities
│   └── model.py           # Model training & forecasting utilities
├── outputs/
│   ├── figures/           # All publication-quality charts (PNG)
│   └── report/            # Final awareness report (PDF)
├── requirements.txt
└── README.md
```

---

## 🗃️ Data Sources

| Data | Source | Notes |
|------|--------|-------|
| Salmon returns | [WDFW Escapement Database](https://wdfw.wa.gov/fishing/salmon-science-management) | Issaquah Creek, 1985–present |
| Hatchery releases | [RMIS](https://rmis.psmfc.org) + FISH records | Chinook & Coho smolt releases |
| Streamflow & water temp | [USGS Gauge 12121600](https://waterdata.usgs.gov/nwis/uv?site_no=12121600) | Issaquah Creek at Issaquah, WA |
| Snowpack (SWE) | [NRCS SNOTEL](https://wcc.sc.egov.usda.gov/nwcc/site?sitenum=769) | Stampede Pass & Snoqualmie Pass |
| Ocean conditions | [NOAA PDO Index](https://psl.noaa.gov/pdo/) | Pacific Decadal Oscillation |
| Land use / impervious | [NLCD](https://www.mrlc.gov) + [King County GIS](https://kingcounty.gov/services/gis) | Sammamish watershed |
| Air temperature | [NOAA Climate Data Online](https://www.ncdc.noaa.gov/cdo-web/) | SeaTac & Issaquah stations |

---

## ⚙️ Setup & Reproducibility

```bash
# 1. Clone the repo
git clone https://github.com/YOUR_USERNAME/issaquah-salmon-study.git
cd issaquah-salmon-study

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run notebooks in order
jupyter lab
# Open notebooks/01_eda.ipynb → 02_stats.ipynb → 03_modeling.ipynb
```

> **Note:** Raw data files must be downloaded separately (see `data/raw/README.md` for instructions). All notebooks run end-to-end once data is in place.

---

## 📊 Key Findings *(updated as project completes)*

- [ ] 40-year trend analysis for Chinook and Coho returns
- [ ] Top stressor variables ranked by impact on Issaquah Creek returns
- [ ] XGBoost model performance (R², MAE, RMSE)
- [ ] 2040 projections under three scenarios

---

## 📄 Awareness Report

The final report is available in [`outputs/report/`](outputs/report/) and is written for a non-technical audience including City of Issaquah officials, City of Sammamish council members, and FISH leadership.

---

## 🤝 Acknowledgments

- **Friends of the Issaquah Salmon Hatchery (FISH)** — domain expertise and hatchery data access
- **WDFW** — salmon escapement records
- **USGS** — streamflow and water temperature data
- **NRCS** — SNOTEL snowpack data

---

## 📜 License

Data outputs and code are released under MIT License. Raw data from government sources retains original agency terms of use.
