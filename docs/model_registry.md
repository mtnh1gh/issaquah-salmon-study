# Model registry

See `docs/model_summary.md` for a plain-language explanation of these models, the validation design, and how they feed the Phase 5/6 uncertainty and scenario work.

Phase 4 experiments generated 2026-07-27.

Data-version ID: `issaquah_creek_master.csv`; SHA-256 `0AFAC071E4C5D2BF1C3631E073DEA3CE829776903A928B7BF71A3F0ACC15D92C`.

Feature-registry version: `docs/feature_registry.csv` at the Phase 4 commit.

## P4-CHINOOK-ALL_ENVIRONMENT_RIDGE

- Species/response: Chinook; annual `total_adults`.
- Training years: expanding windows beginning 1997; final full-period fit 1997-2025.
- Validation folds: 17 rolling-origin tests, 2009-2025.
- Preprocessing: predictor standardization fitted separately inside each training fold; modeled response uses `log1p` for association candidates.
- Algorithm/hyperparameters: `all_environment_ridge`; ridge alpha selected within each outer training window from 0.1, 1, 10, 100.
- Random seed: not applicable; deterministic fitting.
- Naive comparators: expanding-window historical mean and previous-year persistence.
- MAE: 2074.045; RMSE: 2537.969; validation R-squared: -1.5489.
- Uncertainty method: rolling-origin out-of-sample error distribution; no forecast interval approved in Phase 4.
- Residual/influence diagnostics: Shapiro p=0.283; Durbin-Watson=1.023; maximum Cook's D=0.044.
- Lag sensitivity: Coho lag 2 primary; Chinook lag 4 primary, with Phase 3 lags 3/5 sensitivity showing unstable cohort-flow association.
- Scenario eligible: no.
- Decision: reject.
- Git commit: generated before commit; commit identifier is the repository history containing this registry.

## P4-CHINOOK-EXPANDING_MEAN

- Species/response: Chinook; annual `total_adults`.
- Training years: expanding windows beginning 1997; final full-period fit 1997-2025.
- Validation folds: 17 rolling-origin tests, 2009-2025.
- Preprocessing: predictor standardization fitted separately inside each training fold; modeled response uses `log1p` for association candidates.
- Algorithm/hyperparameters: `expanding_mean`.
- Random seed: not applicable; deterministic fitting.
- Naive comparators: expanding-window historical mean and previous-year persistence.
- MAE: 2384.930; RMSE: 2693.263; validation R-squared: -1.8704.
- Uncertainty method: rolling-origin out-of-sample error distribution; no forecast interval approved in Phase 4.
- Residual/influence diagnostics: not applicable to naive baseline.
- Lag sensitivity: Coho lag 2 primary; Chinook lag 4 primary, with Phase 3 lags 3/5 sensitivity showing unstable cohort-flow association.
- Scenario eligible: no.
- Decision: comparator.
- Git commit: generated before commit; commit identifier is the repository history containing this registry.

## P4-CHINOOK-FRESHWATER_MARINE_OLS

- Species/response: Chinook; annual `total_adults`.
- Training years: expanding windows beginning 1997; final full-period fit 1997-2025.
- Validation folds: 17 rolling-origin tests, 2009-2025.
- Preprocessing: predictor standardization fitted separately inside each training fold; modeled response uses `log1p` for association candidates.
- Algorithm/hyperparameters: `freshwater_marine_ols`.
- Random seed: not applicable; deterministic fitting.
- Naive comparators: expanding-window historical mean and previous-year persistence.
- MAE: 2038.072; RMSE: 2402.176; validation R-squared: -1.2835.
- Uncertainty method: rolling-origin out-of-sample error distribution; no forecast interval approved in Phase 4.
- Residual/influence diagnostics: Shapiro p=0.378; Durbin-Watson=1.372; maximum Cook's D=0.168.
- Lag sensitivity: Coho lag 2 primary; Chinook lag 4 primary, with Phase 3 lags 3/5 sensitivity showing unstable cohort-flow association.
- Scenario eligible: no.
- Decision: reject.
- Git commit: generated before commit; commit identifier is the repository history containing this registry.

## P4-CHINOOK-MIGRATION_MARINE_OLS

- Species/response: Chinook; annual `total_adults`.
- Training years: expanding windows beginning 1997; final full-period fit 1997-2025.
- Validation folds: 17 rolling-origin tests, 2009-2025.
- Preprocessing: predictor standardization fitted separately inside each training fold; modeled response uses `log1p` for association candidates.
- Algorithm/hyperparameters: `migration_marine_ols`.
- Random seed: not applicable; deterministic fitting.
- Naive comparators: expanding-window historical mean and previous-year persistence.
- MAE: 2609.236; RMSE: 4314.042; validation R-squared: -6.3647.
- Uncertainty method: rolling-origin out-of-sample error distribution; no forecast interval approved in Phase 4.
- Residual/influence diagnostics: Shapiro p=0.379; Durbin-Watson=1.346; maximum Cook's D=0.340.
- Lag sensitivity: Coho lag 2 primary; Chinook lag 4 primary, with Phase 3 lags 3/5 sensitivity showing unstable cohort-flow association.
- Scenario eligible: no.
- Decision: reject.
- Git commit: generated before commit; commit identifier is the repository history containing this registry.

## P4-CHINOOK-PREVIOUS_YEAR

- Species/response: Chinook; annual `total_adults`.
- Training years: expanding windows beginning 1997; final full-period fit 1997-2025.
- Validation folds: 17 rolling-origin tests, 2009-2025.
- Preprocessing: predictor standardization fitted separately inside each training fold; modeled response uses `log1p` for association candidates.
- Algorithm/hyperparameters: `previous_year`.
- Random seed: not applicable; deterministic fitting.
- Naive comparators: expanding-window historical mean and previous-year persistence.
- MAE: 1180.059; RMSE: 1414.040; validation R-squared: 0.2088.
- Uncertainty method: rolling-origin out-of-sample error distribution; no forecast interval approved in Phase 4.
- Residual/influence diagnostics: not applicable to naive baseline.
- Lag sensitivity: Coho lag 2 primary; Chinook lag 4 primary, with Phase 3 lags 3/5 sensitivity showing unstable cohort-flow association.
- Scenario eligible: no.
- Decision: comparator.
- Git commit: generated before commit; commit identifier is the repository history containing this registry.

## P4-COHO-ALL_ENVIRONMENT_RIDGE

- Species/response: Coho; annual `total_adults`.
- Training years: expanding windows beginning 1997; final full-period fit 1997-2025.
- Validation folds: 17 rolling-origin tests, 2009-2025.
- Preprocessing: predictor standardization fitted separately inside each training fold; modeled response uses `log1p` for association candidates.
- Algorithm/hyperparameters: `all_environment_ridge`; ridge alpha selected within each outer training window from 0.1, 1, 10, 100.
- Random seed: not applicable; deterministic fitting.
- Naive comparators: expanding-window historical mean and previous-year persistence.
- MAE: 3619.558; RMSE: 4284.507; validation R-squared: -0.1678.
- Uncertainty method: rolling-origin out-of-sample error distribution; no forecast interval approved in Phase 4.
- Residual/influence diagnostics: Shapiro p=0.139; Durbin-Watson=2.154; maximum Cook's D=0.123.
- Lag sensitivity: Coho lag 2 primary; Chinook lag 4 primary, with Phase 3 lags 3/5 sensitivity showing unstable cohort-flow association.
- Scenario eligible: yes.
- Decision: retain.
- Git commit: generated before commit; commit identifier is the repository history containing this registry.

## P4-COHO-EXPANDING_MEAN

- Species/response: Coho; annual `total_adults`.
- Training years: expanding windows beginning 1997; final full-period fit 1997-2025.
- Validation folds: 17 rolling-origin tests, 2009-2025.
- Preprocessing: predictor standardization fitted separately inside each training fold; modeled response uses `log1p` for association candidates.
- Algorithm/hyperparameters: `expanding_mean`.
- Random seed: not applicable; deterministic fitting.
- Naive comparators: expanding-window historical mean and previous-year persistence.
- MAE: 4053.290; RMSE: 4892.921; validation R-squared: -0.5230.
- Uncertainty method: rolling-origin out-of-sample error distribution; no forecast interval approved in Phase 4.
- Residual/influence diagnostics: not applicable to naive baseline.
- Lag sensitivity: Coho lag 2 primary; Chinook lag 4 primary, with Phase 3 lags 3/5 sensitivity showing unstable cohort-flow association.
- Scenario eligible: no.
- Decision: comparator.
- Git commit: generated before commit; commit identifier is the repository history containing this registry.

## P4-COHO-FRESHWATER_MARINE_OLS

- Species/response: Coho; annual `total_adults`.
- Training years: expanding windows beginning 1997; final full-period fit 1997-2025.
- Validation folds: 17 rolling-origin tests, 2009-2025.
- Preprocessing: predictor standardization fitted separately inside each training fold; modeled response uses `log1p` for association candidates.
- Algorithm/hyperparameters: `freshwater_marine_ols`.
- Random seed: not applicable; deterministic fitting.
- Naive comparators: expanding-window historical mean and previous-year persistence.
- MAE: 3856.804; RMSE: 4805.304; validation R-squared: -0.4689.
- Uncertainty method: rolling-origin out-of-sample error distribution; no forecast interval approved in Phase 4.
- Residual/influence diagnostics: Shapiro p=0.105; Durbin-Watson=2.125; maximum Cook's D=0.500.
- Lag sensitivity: Coho lag 2 primary; Chinook lag 4 primary, with Phase 3 lags 3/5 sensitivity showing unstable cohort-flow association.
- Scenario eligible: yes.
- Decision: retain.
- Git commit: generated before commit; commit identifier is the repository history containing this registry.

## P4-COHO-MIGRATION_MARINE_OLS

- Species/response: Coho; annual `total_adults`.
- Training years: expanding windows beginning 1997; final full-period fit 1997-2025.
- Validation folds: 17 rolling-origin tests, 2009-2025.
- Preprocessing: predictor standardization fitted separately inside each training fold; modeled response uses `log1p` for association candidates.
- Algorithm/hyperparameters: `migration_marine_ols`.
- Random seed: not applicable; deterministic fitting.
- Naive comparators: expanding-window historical mean and previous-year persistence.
- MAE: 3712.991; RMSE: 4878.487; validation R-squared: -0.5140.
- Uncertainty method: rolling-origin out-of-sample error distribution; no forecast interval approved in Phase 4.
- Residual/influence diagnostics: Shapiro p=0.068; Durbin-Watson=2.160; maximum Cook's D=0.557.
- Lag sensitivity: Coho lag 2 primary; Chinook lag 4 primary, with Phase 3 lags 3/5 sensitivity showing unstable cohort-flow association.
- Scenario eligible: yes.
- Decision: retain.
- Git commit: generated before commit; commit identifier is the repository history containing this registry.

## P4-COHO-PREVIOUS_YEAR

- Species/response: Coho; annual `total_adults`.
- Training years: expanding windows beginning 1997; final full-period fit 1997-2025.
- Validation folds: 17 rolling-origin tests, 2009-2025.
- Preprocessing: predictor standardization fitted separately inside each training fold; modeled response uses `log1p` for association candidates.
- Algorithm/hyperparameters: `previous_year`.
- Random seed: not applicable; deterministic fitting.
- Naive comparators: expanding-window historical mean and previous-year persistence.
- MAE: 4354.588; RMSE: 5874.681; validation R-squared: -1.1954.
- Uncertainty method: rolling-origin out-of-sample error distribution; no forecast interval approved in Phase 4.
- Residual/influence diagnostics: not applicable to naive baseline.
- Lag sensitivity: Coho lag 2 primary; Chinook lag 4 primary, with Phase 3 lags 3/5 sensitivity showing unstable cohort-flow association.
- Scenario eligible: no.
- Decision: comparator.
- Git commit: generated before commit; commit identifier is the repository history containing this registry.
