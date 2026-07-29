# Modeling approach summary

This is a plain-language summary of the modeling method behind `docs/model_registry.md`
and `docs/statistical_analysis_report.md`. Those two files are the authoritative,
script-generated record (see `src/run_phase4_models.py`); this page explains *what
the models are and why*, for a reader who doesn't want to parse the code.

## What kind of model this is — and isn't

Despite the project's "AI-Driven Forecasting" working title, the models retained
through Phase 4 are **classical, hand-implemented multiple linear regression and
ridge regression** — not XGBoost, not a neural network, not any black-box ML
method. Every fit is a closed-form solution (`(XᵀX + αI)⁻¹Xᵀy`, in
`src/run_phase4_models.py::fit_linear`) using only NumPy/SciPy, chosen deliberately
for a 29-observation dataset where an interpretable, auditable coefficient matters
more than marginal predictive gain — and where a complex model would be trivially
overfit. Every projection downstream (Phase 5, Phase 6) reuses these same fitted
coefficients; nothing more sophisticated is introduced later in the pipeline.

## Candidate model specifications

Each species (Chinook, Coho) is modeled independently. The response is annual
`total_adults`, fit on the `log1p` scale (predictions are back-transformed with
`expm1` and floored at zero). Five interpretable feature sets are tried, plus two
naive comparators. The last two rows were added under D-020 to test NPGO and ONI
as additional marine-condition proxies alongside PDO:

| Model ID | Features | Fit method |
|---|---|---|
| `migration_marine_ols` | adult migration-year flow, migration-year temperature, marine-window PDO | ordinary least squares (α=0) |
| `freshwater_marine_ols` | cohort-year flow, cohort-year April 1 SWE, marine-window PDO | ordinary least squares (α=0) |
| `all_environment_ridge` | all five features above | ridge regression, α chosen from {0.1, 1, 10, 100} inside each training window |
| `ocean_index_ols` | marine-window PDO, NPGO, and ONI only (no freshwater/migration terms) | ordinary least squares (α=0) |
| `all_environment_ocean_ridge` | the five `all_environment_ridge` features plus marine-window NPGO and ONI | ridge regression, α chosen from {0.1, 1, 10, 100} inside each training window |
| `expanding_mean` (baseline) | none — predicts the training-period mean | — |
| `previous_year` (baseline) | none — predicts last year's actual value | — |

"Cohort-year" and "migration-year" reflect the two lag structures used to align a
return year with the freshwater/ocean conditions its fish actually experienced:
Coho lag 2, Chinook lag 4 (with lags 3 and 5 checked as a sensitivity range — see
`docs/decision_log.md` D-012, D-013). The marine window for NPGO/ONI is identical
to PDO's: the mean of the annual index from the year after the cohort proxy
through the year before adult return (D-020).

## Validation design

Models are validated with **rolling-origin (walk-forward) time-series
cross-validation** — never scikit-learn's generic k-fold, since that would leak
future years into training:

- Expanding training window starting at a minimum of 12 years, tested sequentially over 17 rolling-origin folds (2009–2025).
- Feature standardization (mean/SD) and ridge α selection are refit *inside* every training window — no statistic from a test year ever touches training.
- A candidate is only marked **scenario-eligible** if it beats *both* naive baselines on *both* MAE and RMSE. This is a deliberately high bar to avoid presenting a merely fitted-looking model as skillful.

### Outcome

- **Chinook: still no candidate qualifies**, including both new ocean-index models. All five environmental models are worse than simply predicting last year's return (best baseline MAE 1,180 vs. every model ≥ 2,038; R² down to -6.36 for the weakest). Chinook results are retained as descriptive association/trend findings only.
- **Coho: 5 of 5 environmental candidates now qualify** (up from 3 of 3 before D-020), each beating both Coho baselines on MAE and RMSE. Adding NPGO/ONI produced the **best Coho model seen in this project so far**: `all_environment_ocean_ridge` (MAE 3,149, RMSE 4,058, R² -0.047) and `ocean_index_ols` (MAE 3,355, RMSE 4,203, R² -0.124) both beat every PDO-only model, including the previous best (`all_environment_ridge`: MAE 3,620, R² -0.168). R² is still negative for every candidate — these are relative improvements over a weak baseline, not absolute predictive accuracy.

Full per-model numbers, residual diagnostics (Shapiro, Durbin-Watson, Cook's distance, VIF), and standardized coefficients are in `docs/model_registry.md` and `docs/statistical_analysis_report.md`.

## Phase 5 — uncertainty quantification

For the five retained Coho models (`src/run_phase5_uncertainty.py`):

- **Paired bootstrap** (5,000 resamples, fixed seed 20260727) of the 17 rolling-origin errors produces 95% confidence intervals around MAE and RMSE.
- **Empirical prediction intervals** are built directly from the 2.5th/97.5th percentiles of held-out residuals, added to each point prediction — not a parametric/Gaussian interval.
- Measured empirical coverage was **88.2%** against a nominal 95% target for every retained model, including the two new ones. With only 17 test years, the report explicitly declines to certify calibration and treats the intervals as descriptive, not statistically guaranteed.

## Phase 6 — scenario projection (2026–2040)

Two independent, complementary scenario methods are produced, both restricted to Coho (no Chinook model passed the Phase 4 gate):

1. **Conditional / static-quantile scenarios** (`src/run_phase6_scenarios.py`): each retained model is evaluated at its predictors held constant at their observed 1997–2025 10th/50th/90th percentiles — three flat "low / central / high" trajectories, banded with the same empirical residual quantiles from Phase 5.
2. **Dynamic scenarios** (`src/run_phase6_dynamic.py`): each predictor's historical trend is extrapolated with a **Theil-Sen slope** (robust to outliers), then perturbed with a favorable/central/adverse offset and reproducible annual Gaussian noise (seed 20260727, 1,000 Monte Carlo draws per scenario-year), with model residuals resampled from Phase 4 held-out errors. Output is a median path with a 90% simulation band.

Both scripts and their generated reports (`docs/phase6_scenario_report.md`,
`docs/phase6_dynamic_report.md`) state explicitly that these are **illustrative
sensitivity trajectories, not forecasts, causal estimates, or policy-effect
estimates** — hatchery releases and imperviousness are held implicitly constant
throughout because those series remain unavailable (D-005, D-011), and PDO is
treated as an external, uncontrollable input rather than a lever.

## Where to look next

- `docs/model_registry.md` — machine-generated per-model spec/metrics registry (the source of truth for exact numbers).
- `docs/statistical_analysis_report.md` — full validation table, coefficients, and diagnostics.
- `docs/phase5_uncertainty_report.md`, `docs/phase6_scenario_report.md`, `docs/phase6_dynamic_report.md` — narrative reports for each later phase.
- `docs/decision_log.md` — why each modeling choice (lag structure, baseline gate, scenario framing) was made.
