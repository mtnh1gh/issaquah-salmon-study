# Exploratory analysis report

Phase: 3

Coverage: 1997–2025; 29 annual observations per species.

All findings are exploratory associations under `docs/analysis_protocol.md`; they are not causal effects.

## Return trends

| Species | Kendall tau | Raw p-value | BH-adjusted p | Theil–Sen adults/year | Last 5 vs first 5 |
|---|---:|---:|---:|---:|---:|
| Chinook | -0.118 | 0.381 | 0.857 | -50.6 | 9.7% |
| Coho | -0.044 | 0.752 | 0.857 | -37.8 | -54.5% |

Wild-origin series are plotted and tested only from 2010 because earlier records do not contain explicit wild-origin trap rows.

Neither species has a monotonic total-adult trend that passes the pre-specified multiple-testing threshold. The difference between first/last five-year means is descriptive and sensitive to highly variable return years.

## Environmental trends

| Indicator | Kendall tau | BH-adjusted p | Theil–Sen change/year |
|---|---:|---:|---:|
| April 1 SWE | -0.351 | 0.024 | -0.887 |
| Annual PDO | -0.315 | 0.028 | -0.055 |
| Annual NPGO | -0.522 | 0.000 | -0.129 |
| Adult migration temperature | 0.338 | 0.024 | 0.050 |

These monotonic environmental trends are indicators over the study period; they do not establish that the trend caused salmon-return variation.

## Strongest pre-specified correlations

| Species | Predictor | Spearman rho | Block-bootstrap 95% CI | Raw p | BH-adjusted p |
|---|---|---:|---:|---:|---:|
| Coho | Marine-window ONI | -0.509 | [-0.740, -0.189] | 0.005 | 0.067 |
| Coho | Marine-window PDO | -0.360 | [-0.685, 0.016] | 0.055 | 0.385 |
| Chinook | Adult migration flow | -0.321 | [-0.559, 0.046] | 0.089 | 0.397 |
| Chinook | Adult migration temperature | -0.300 | [-0.593, -0.014] | 0.113 | 0.397 |

The moving-block bootstrap uses three-year blocks to partially reflect temporal dependence. With only 29 years, intervals are expected to be wide.

## Lag sensitivity

Chinook cohort indicators were checked at lags 3, 4, and 5; Coho used the locked primary lag 2. A candidate that changes sign or magnitude materially across Chinook lags is not considered stable.

Chinook cohort-year flow is not stable across lags: lag 3: rho=-0.420, lag 4: rho=0.015, lag 5: rho=0.220.

Detailed results: `outputs/tables/lag_sensitivity.csv` (12 tests).

## Missingness and exclusions

- `impervious_pct` is unavailable in all 58 rows and remains excluded.
- `hatchery_releases` is unavailable in all 58 rows and remains excluded.

No core response or available environmental feature is missing. Releases and imperviousness are not zero-filled.

## Interpretation limits

- Hatchery releases remain an unmeasured production confounder.
- Direct imperviousness is unavailable, so no urban-development period comparison is run.
- Multiple-testing adjustment is Benjamini–Hochberg across each output table.
- Correlation does not identify biological mechanism or causation.
- Phase 4 should retain only a small, pre-specified predictor set and time-aware validation.

## Reproduction

```powershell
.\.venv\Scripts\python.exe .\src\run_eda.py
```

Runtime: Python 3.13.7, pandas 3.0.5, NumPy 2.3.2, SciPy 1.18.0, Matplotlib 3.11.1.
