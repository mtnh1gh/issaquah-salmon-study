# Phase 4 validation report

Status: PASS

Checks passed: 15

- PASS: 14 species/model experiments are registered
- PASS: All 17 rolling-origin years exist for 14 experiments
- PASS: Training windows expand from 12 through 28 years
- PASS: No validation fold trains on its test year or the future
- PASS: All validation outcomes and predictions are finite
- PASS: All back-transformed count predictions are nonnegative
- PASS: All 42 pre-specified model coefficients are present
- PASS: All ten fitted association models have diagnostics
- PASS: Every coefficient has an influential-year sensitivity estimate
- PASS: Chinook lag sensitivity covers lags 3, 4, and 5
- PASS: Chinook lag 4 is the sole primary lag
- PASS: No Chinook model passes the scenario-eligibility gate, including the two new ocean-index candidates (D-020)
- PASS: Five Coho candidates pass the preliminary baseline gate after adding the two ocean-index models (D-020)
- PASS: Statistical report is present
- PASS: Model registry is present

```powershell
.\.venv\Scripts\python.exe .\src\validate_phase4.py
```
