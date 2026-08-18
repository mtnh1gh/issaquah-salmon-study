# 🐟 Issaquah Creek Salmon Return Study

### Understanding nearly three decades of Chinook and Coho returns through environmental data

**Independent quantitative research | Issaquah Creek, Washington | 1997–2025**

---

## The Question

Each fall, Chinook and Coho salmon return from the Pacific Ocean to Issaquah Creek, swimming through one of the most developed watersheds in the Seattle area.

Their returns vary dramatically from year to year.

**What environmental conditions are associated with those changes — and how much can they actually help us predict future returns?**

This project combines 1997–2025 salmon-return records with streamflow, snowpack, water-temperature, and ocean-condition data to investigate that question using reproducible statistical analysis and predictive modeling.

Rather than assuming that a more complex model would produce a better answer, the study asks a more basic question:

> **Does environmental information predict salmon returns better than simple baselines — and how certain can we be?**

---

## Why I Started This Project

I grew up fishing rivers and lakes across the Pacific Northwest and became interested in how fish respond to changing water, weather, and seasonal conditions.

Later, while volunteering with Friends of the Issaquah Salmon Hatchery (FISH), I learned more about salmon migration, hatchery operations, and the challenges facing local salmon populations.

That led me to a question I could investigate quantitatively: **could long-term environmental data help explain the large year-to-year changes in salmon returning to Issaquah Creek?**

This repository documents my attempt to answer that question — including the parts the data could not answer reliably.

---

## What I Did

I built an end-to-end Python and PowerShell research pipeline that:

- collected and preserved raw public environmental datasets;
- cleaned and standardized data from multiple government sources;
- aligned environmental conditions with Chinook and Coho life-cycle timing;
- analyzed long-term trends and environmental associations;
- built interpretable statistical and predictive models;
- tested those models against simple forecasting baselines;
- used walk-forward validation to prevent future data from leaking into training;
- quantified predictive uncertainty with bootstrap resampling; and
- generated conditional scenarios while explicitly separating them from forecasts.

The pipeline follows a reproducible **Bronze → Silver → Gold** architecture:

```text
Raw source data
      ↓
   Bronze
immutable, checksummed snapshots
      ↓
   Silver
cleaned annual source tables
      ↓
    Gold
joined, cohort-aligned analysis dataset
      ↓
EDA → Modeling → Validation → Uncertainty → Scenarios