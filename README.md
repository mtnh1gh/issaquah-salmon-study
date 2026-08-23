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
```

## Phase 7 frozen hypothesis analysis

Phase 7 uses one deterministic program, `src/run_phase7_hypothesis_tests.py`,
rather than notebook experiments. The program validates the frozen protocol and
inputs, runs A1/A3/A5, A6/A7, every frozen sensitivity (including amendment
D-022), and the species-specific A8 models in the prescribed order. It stages
the entire result package and publishes the completion manifest last.

```powershell
python -m pip install -r requirements.txt
python src/run_phase7_hypothesis_tests.py
```

The exact protocol version and SHA-256 are enforced by the program. Results,
diagnostics, input hashes, software versions, and deterministic seeds are under
`outputs/phase7/`. Start with the machine-readable files before narrative
interpretation:

- `phase7_primary_results.csv` for A1/A3/A5;
- `phase7_mechanism_results.csv` for A6/A7;
- `phase7_sensitivity_results.csv` for alternate-window, T1, jack-inclusive,
  extrapolation, Cook, and temporal-trend sensitivities; and
- `phase7_execution_metadata.json` for protocol, program, input, seed, runtime,
  and package-version provenance.

The narrative is in `phase7_hypothesis_analysis_report.md`; the authoritative
completion marker and artifact hashes are in `phase7_output_manifest.json`.
