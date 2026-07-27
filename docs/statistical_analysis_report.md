# Statistical analysis report

Phase: 4

Response: `log1p(total_adults)` for fitted association models; validation errors are reported in adult-count units.

The models estimate observational associations, not causal effects. Imperviousness and releases remain excluded because observed values are unavailable.

## Time-aware validation

Each species has 17 rolling-origin test years (2009-2025). Every fold trains only on preceding years. Scaling is fitted inside each fold; the five-feature ridge alpha is selected inside each outer training window.

| Species | Model | MAE | RMSE | R-squared | Beats best baseline MAE | Beats best baseline RMSE | Scenario eligible |
|---|---|---:|---:|---:|---|---|---|
| Chinook | `previous_year` | 1180 | 1414 | 0.209 | False | False | False |
| Chinook | `freshwater_marine_ols` | 2038 | 2402 | -1.283 | False | False | False |
| Chinook | `all_environment_ridge` | 2074 | 2538 | -1.549 | False | False | False |
| Chinook | `expanding_mean` | 2385 | 2693 | -1.870 | False | False | False |
| Chinook | `migration_marine_ols` | 2609 | 4314 | -6.365 | False | False | False |
| Coho | `all_environment_ridge` | 3620 | 4285 | -0.168 | True | True | True |
| Coho | `freshwater_marine_ols` | 3857 | 4805 | -0.469 | True | True | True |
| Coho | `migration_marine_ols` | 3713 | 4878 | -0.514 | True | True | True |
| Coho | `expanding_mean` | 4053 | 4893 | -0.523 | False | False | False |
| Coho | `previous_year` | 4355 | 5875 | -1.195 | False | False | False |

A candidate is scenario-eligible only if it improves both MAE and RMSE over the best corresponding naive baseline. Negative validation R-squared means predictions are worse than predicting the test-period mean and is retained as an honest feasibility result.

## Full-period standardized associations

Coefficients below are multiplicative changes in the fitted median count per one training-period standard deviation, holding the other predictors in that model constant. They are descriptive full-period estimates and are not selected by statistical significance.

| Species | Model | Strongest standardized association | Multiplier per 1 SD |
|---|---|---|---:|
| Chinook | `all_environment_ridge` | Cohort-year April 1 SWE (+0.052 log units) | 1.054x |
| Chinook | `freshwater_marine_ols` | Cohort-year April 1 SWE (+0.273 log units) | 1.314x |
| Chinook | `migration_marine_ols` | Adult migration temperature (-0.148 log units) | 0.863x |
| Coho | `all_environment_ridge` | Marine-window PDO (-0.044 log units) | 0.957x |
| Coho | `freshwater_marine_ols` | Marine-window PDO (-0.204 log units) | 0.816x |
| Coho | `migration_marine_ols` | Marine-window PDO (-0.198 log units) | 0.820x |

## Diagnostics

| Species | Model | Alpha | Shapiro p | Durbin-Watson | Max Cook's D (year) | Max VIF |
|---|---|---:|---:|---:|---:|---:|
| Chinook | `all_environment_ridge` | 100.0 | 0.283 | 1.023 | 0.044 (2001) | 1.36 |
| Chinook | `freshwater_marine_ols` | 0.0 | 0.378 | 1.372 | 0.168 (2007) | 1.20 |
| Chinook | `migration_marine_ols` | 0.0 | 0.379 | 1.346 | 0.340 (1997) | 1.11 |
| Coho | `all_environment_ridge` | 100.0 | 0.139 | 2.154 | 0.123 (2010) | 1.40 |
| Coho | `freshwater_marine_ols` | 0.0 | 0.105 | 2.125 | 0.500 (2010) | 1.16 |
| Coho | `migration_marine_ols` | 0.0 | 0.068 | 2.160 | 0.557 (2010) | 1.07 |

Cook's distance is a screening diagnostic; years exceeding roughly `4/n` warrant sensitivity review. Ridge leverage/Cook values are approximate. VIF describes predictor collinearity, not model validity.

Excluding each model's highest-Cook's-distance year caused 5 coefficient sign changes across 22 coefficients. Detailed estimates are in `outputs/tables/phase4_influence_sensitivity.csv`.

## Chinook lag sensitivity

| Cohort lag | Primary | MAE | RMSE | R-squared |
|---:|---|---:|---:|---:|
| 3 | False | 1600 | 2316 | -1.122 |
| 4 | True | 2038 | 2402 | -1.283 |
| 5 | False | 2282 | 3268 | -3.227 |

Lag sensitivity is evaluated with the same rolling-origin design. Material error differences reinforce that the Chinook cohort alignment is uncertain rather than a tuned biological fact.

## Interpretation limits

- Twenty-nine annual observations per species sharply limit model complexity and validation precision.
- Hatchery production is an unmeasured confounder because actual release records remain blocked.
- Land-use association cannot be estimated without the imperviousness series.
- Same-year temperature is a sparse grab-sample index, not continuous thermal exposure.
- Cohort lags are biological proxies; the Phase 3 Chinook flow association was unstable at lags 3-5.
- No model should be used for 2040 scenarios unless it passes the stated baseline gate and Phase 5 uncertainty review.

## Reproduction

```powershell
.\.venv\Scripts\python.exe .\src\run_phase4_models.py
.\.venv\Scripts\python.exe .\src\validate_phase4.py
```

Runtime: Python 3.14.6, pandas 3.0.5, NumPy 2.5.1, SciPy 1.18.0, Matplotlib 3.11.1.
