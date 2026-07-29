# Phase 5 uncertainty review

Status: completed; no final scenario model approved.

The three Coho candidates that passed the Phase 4 baseline gate were reviewed with paired bootstrap resampling of the 17 rolling-origin errors. These intervals describe validation uncertainty; they are not causal confidence intervals.

| Model | MAE | Bootstrap 95% CI | RMSE | Bootstrap 95% CI | Interval coverage |
|---|---:|---:|---:|---:|---:|
| `all_environment_ocean_ridge` | 3149 | [1995, 4424] | 4058 | [2632, 5261] | 88.2% |
| `ocean_index_ols` | 3355 | [2235, 4647] | 4203 | [2725, 5586] | 88.2% |
| `all_environment_ridge` | 3620 | [2545, 4730] | 4285 | [3086, 5332] | 88.2% |
| `freshwater_marine_ols` | 3857 | [2573, 5257] | 4805 | [3164, 6334] | 88.2% |
| `migration_marine_ols` | 3713 | [2328, 5316] | 4878 | [3122, 6578] | 88.2% |

Empirical intervals use held-out residual quantiles and are descriptive only. With 17 test years, coverage is too imprecise to certify nominal 95% calibration.

PDO is not treated as a controllable intervention; hatchery releases and imperviousness remain unavailable. Phase 6 may construct only explicitly illustrative, cited trajectories.

Reproduction: `python src/run_phase5_uncertainty.py`; `python src/validate_phase5.py`
