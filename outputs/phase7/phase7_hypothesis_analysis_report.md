# Phase 7 frozen hypothesis-analysis results

Run date: 2026-08-23

Frozen protocol: version 1.1; SHA-256 `33BFCCD299DA7064462B9F66F1944638E6949FFB5406C78DC9EE6E97E8D15DE2`.

Status: deterministic observational analysis of modeled temperature proxies. These results are not causal effects, observed continuous water temperatures, or regulatory 7DADMax estimates.

## Input validation

All 39 validation checks passed before any association was calculated. The exact frozen input hashes are recorded in `phase7_output_manifest.json` and `phase7_input_validation.json`.

## Primary family: A1, A3, A5

| ID | Species | n | rho | 95% bootstrap CI | raw p | Holm p | OLS beta | %/1 SD | Protocol classification |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A1 | Chinook | 29 | -0.400 | -0.677, -0.045 | 0.03180 | 0.09540 | -0.242 | -21.5 | not_supported_by_these_data |
| A3 | Coho | 29 | -0.044 | -0.436, 0.360 | 0.82142 | 0.82142 | -0.024 | -2.4 | not_supported_by_these_data |
| A5 | Coho | 29 | -0.202 | -0.601, 0.235 | 0.29007 | 0.58013 | -0.096 | -9.1 | not_supported_by_these_data |

The rank tests use 100,000 unrestricted outcome permutations. Holm correction is confined to A1/A3/A5. The OLS coefficient is for standardized T2 window temperature in `log1p(total_adults)` models with HC3 intervals.

## Mechanism family: A6, A7

| ID | Relationship | n | Expected | rho | 95% CI | raw p | Holm p |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A6 | April 1 SWE -> Jul-Sep mean flow | 29 | positive | 0.137 | -0.289, 0.501 | 0.47673 | 0.47673 |
| A7 | Matched Jun-Sep flow -> T2 Jun-Sep temperature | 31 | negative | -0.417 | -0.677, -0.078 | 0.01971 | 0.03942 |

## Frozen sensitivity analyses

| ID | Sensitivity | n | rho | unadjusted p | max Cook year |
| --- | --- | --- | --- | --- | --- |
| A2 | window_alternative | 29 | -0.327 | 0.08332 | 2022 |
| A4 | window_alternative | 29 | -0.175 | 0.36113 | 2014 |
| A1 | t1_replacement | 29 | -0.400 | 0.03227 | 1999 |
| A3 | t1_replacement | 29 | -0.047 | 0.80827 | 2014 |
| A5 | t1_replacement | 29 | -0.188 | 0.32538 | 2010 |
| A1 | adults_plus_jacks | 29 | -0.391 | 0.03627 | 2022 |
| A3 | adults_plus_jacks | 29 | -0.026 | 0.89286 | 2014 |
| A5 | adults_plus_jacks | 29 | -0.193 | 0.31215 | 2010 |
| A1 | no_t2_extrapolation_rows | 21 | -0.443 | 0.04595 | 1999 |
| A3 | no_t2_extrapolation_rows | 23 | -0.137 | 0.53021 | 2014 |
| A5 | no_t2_extrapolation_rows | 15 | 0.036 | 0.90226 | 2001 |
| A1 | highest_cook_removed | 28 | -0.503 | 0.00688 | 2000 |
| A3 | highest_cook_removed | 28 | -0.126 | 0.51954 | 2001 |
| A5 | highest_cook_removed | 28 | -0.299 | 0.12342 | 2002 |

All sensitivity p-values are descriptive and unadjusted. Full coefficients, HC3 intervals, Cook diagnostics, and the one-time highest-Cook OLS refits are provided in machine-readable tables.

### Leave-one-year-out rho

| ID | Full rho | LOYO min | LOYO max | sign changes |
| --- | --- | --- | --- | --- |
| A1 | -0.400 | -0.503 | -0.347 | 0 |
| A3 | -0.044 | -0.132 | 0.049 | 2 |
| A5 | -0.202 | -0.311 | -0.121 | 0 |

### Temporal-trend sensitivity (D-022)

| ID | temp raw lag1 | return raw lag1 | temp resid lag1 | return resid lag1 | primary rho | detrended rho | direction | magnitude change % | circular shift | shift p |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A1 | 0.480 | 0.567 | 0.060 | 0.542 | -0.400 | -0.352 | retained | -12.2 | triggered_abs_residual_lag1_ge_0_30 | 0.03448 |
| A3 | 0.115 | 0.010 | -0.161 | 0.011 | -0.044 | -0.014 | retained | -67.1 | not_triggered_below_abs_lag1_0_30 | NA |
| A5 | 0.621 | 0.010 | 0.290 | 0.011 | -0.202 | -0.217 | retained | 7.3 | not_triggered_below_abs_lag1_0_30 | NA |

This is strictly a temporal-trend sensitivity. It is not a fitted time-series model and does not prove that all cohort or multi-year dependence was removed.

## A8 secondary temperature + flow models

| Species | Term | beta | HC3 95% CI | HC3 p | VIF | adjusted R2 |
| --- | --- | --- | --- | --- | --- | --- |
| Chinook | z_t2_window_mean_c | -0.240 | -0.478, -0.001 | 0.04901 | 1.006 | 0.126 |
| Chinook | z_log_matched_flow_cfs | -0.035 | -0.307, 0.238 | 0.79433 | 1.006 | 0.126 |
| Coho | z_t2_window_mean_c | -0.034 | -0.416, 0.348 | 0.85612 | 1.003 | -0.041 |
| Coho | z_log_matched_flow_cfs | 0.167 | -0.207, 0.541 | 0.36667 | 1.003 | -0.041 |

A8 is secondary and descriptive and cannot overturn A1 or A3. See `phase7_a8_diagnostics.png` for residual, Q-Q, and Cook plots.

## Output interpretation boundary

T2 is an air-temperature-plus-seasonal proxy calibrated to grab samples; T1 adds flow and is used only as model-form sensitivity. Extrapolation exclusions are sensitivity analyses. Threshold counts and all other nonmean thermal metrics remain exploratory only and were not tested here.
