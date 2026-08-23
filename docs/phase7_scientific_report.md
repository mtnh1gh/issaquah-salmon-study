# Phase 7 scientific synthesis

**Status:** Frozen results synthesis, 2026-08-23  
**Analysis package:** first committed run at `5d0feedade3b2f00686556367df9f37300f0d41a`  
**Freeze record:** `docs/phase7_results_freeze.json`

Phase 7 tested three life-stage-specific thermal hypotheses, two hydrologic
mechanism hypotheses, prespecified robustness analyses, and a secondary
temperature-plus-flow model. All 39 analysis checks and all 28 independent
output-validation checks passed. The results below synthesize the frozen
machine-readable outputs; they do not change a window, lag, metric, test,
family, or exclusion.

## Scientific conclusion

The primary family did not provide multiplicity-adjusted support for any of the
three salmon-temperature hypotheses. Chinook returns nevertheless showed a
moderate negative association with modeled adult-migration temperature (A1,
Spearman rho = -0.400, raw two-sided permutation p = 0.0318), but the
Holm-adjusted p-value was 0.0954. The A1 direction and approximate magnitude
persisted across all prespecified model, window, outcome, extrapolation,
influence, leave-one-year-out, and temporal-trend checks. This is best described
as a stable but uncertain observational signal, not formal confirmation. The
Coho adult-migration and juvenile/rearing associations were weaker and
imprecise.

The proposed hydrologic pathway was only partly supported. A6 did not show a
supported association between April 1 snow-water equivalent and July-September
flow, whereas greater matched June-September flow was associated with lower T2
temperature (A7) after correction within the mechanism family. A7 supports a
local flow-temperature link in this modeled-proxy analysis; it does not
establish a complete snowpack-to-flow-to-temperature pathway or a causal
pathway to salmon returns.

## 1. Temperature reconstruction and validation

T2 reconstructed daily Issaquah Creek temperature for 1995-2025 from regional
air temperature and seasonal terms, without streamflow. It was calibrated to
431 King County station 0631 grab samples on 415 unique dates. In leave-one-year-
out validation, T2 had RMSE 0.788 C, MAE 0.618 C, negligible bias, and R-squared
0.955. Its RMSE was 48.4% lower than held-out monthly climatology and only 0.9%
higher than the flow-inclusive T1 model. This small performance difference
supports using T2 as the primary thermal variable while reserving T1 for model-
form sensitivity and avoiding mathematical flow coupling in A7 and A8.

Validation within the three biological windows also favored T2 over monthly
climatology. Held-out RMSE was 0.771 C for the Chinook Aug 15-Sep 30 window,
0.696 C for the Coho Sep 15-Oct 31 window, and 0.970 C for the Coho Jun-Sep
window. The complete reconstruction contained 11,323 daily estimates. Of 248
days outside at least one calibration predictor range, 54 occurred during
June-October (1.14% of days in those months). Excluding windows with any T2
extrapolation was prespecified as a sensitivity, not a reason to delete primary
rows.

These metrics validate T2 as an approximate window-mean proxy for the stated
analysis. T2 values remain modeled estimates rather than continuous in-stream
observations; sparse grab samples do not validate daily maxima, and modeled
seven-day metrics are not observed regulatory 7DADMax.

## 2. Life-stage-specific thermal hypotheses

Each primary test used 29 annual returns, T2 biological-window mean, Spearman
rho, 100,000 unrestricted two-sided permutations, and Holm adjustment across
A1/A3/A5.

| Hypothesis | Species and exposure | rho (95% bootstrap CI) | raw p | Holm p | Formal conclusion |
| --- | --- | ---: | ---: | ---: | --- |
| A1 | Chinook adult migration, Aug 15-Sep 30 | -0.400 (-0.677, -0.045) | 0.0318 | 0.0954 | Not supported after family correction |
| A3 | Coho adult migration, Sep 15-Oct 31 | -0.044 (-0.436, 0.360) | 0.8214 | 0.8214 | Not supported |
| A5 | Coho juvenile/rearing, Jun-Sep two years before return | -0.202 (-0.601, 0.235) | 0.2901 | 0.5801 | Not supported |

All observed directions matched the prespecified negative expectations, but
expected direction was a reporting criterion rather than one-sided inference.
The supportive A1 HC3 regression estimated a 21.5% lower fitted adult count per
one-SD warmer T2 window (beta on log1p count = -0.242; 95% CI -0.463 to -0.021).
That effect estimate does not override the primary family's Holm-adjusted
decision.

## 3. Robustness of the Chinook association

A1 did not materially weaken under the prespecified sensitivities. Spearman rho
was -0.400 with the flow-inclusive T1 proxy, -0.327 with the longer migration
window, -0.391 for adults plus jacks, -0.443 after excluding T2-extrapolation
rows, and -0.503 after removing the highest-Cook year. Across 29 leave-one-year-
out reruns, rho ranged from -0.503 to -0.347 with no sign changes. These checks
show that the negative association was not created by the choice of T2 or by any
single omitted return year, although inferential precision varied across the
smaller or altered samples.

After rank-residualizing temperature and returns against calendar year, A1 rho
was -0.352, a 12.2% reduction in magnitude with direction retained. Residual
lag-1 autocorrelation triggered the prespecified circular-shift diagnostic; its
exact two-sided p-value was 1/29 = 0.0345. This coarse diagnostic is reported
only as temporal-dependence sensitivity. It does not replace the primary test
or demonstrate that all cohort and multi-year dependence was removed.

Taken together, the sensitivity analyses favor the interpretation that A1 is a
stable, moderate negative association with limited precision. They do not
change its frozen formal status: A1 was not supported at family-wise alpha 0.05.

## 4. Hydrologic mechanism tests

The two mechanism tests formed a separate Holm family.

| Hypothesis | Relationship | n | rho (95% bootstrap CI) | Holm p | Formal conclusion |
| --- | --- | ---: | ---: | ---: | --- |
| A6 | April 1 SWE -> Jul-Sep mean flow | 29 | 0.137 (-0.289, 0.501) | 0.4767 | Not supported |
| A7 | Matched Jun-Sep flow -> T2 Jun-Sep temperature | 31 | -0.417 (-0.677, -0.078) | 0.0394 | Supported by observational mechanism analysis |

For A7, a one-SD increase in log matched flow corresponded to a 0.243 C lower
modeled Jun-Sep T2 mean in the supportive HC3 regression (95% CI -0.383 to
-0.104 C). A7 used T2 specifically because T2 contains no flow feature. The
unsupported A6 result means the full hypothesized snowpack-flow-temperature
chain was not observed in these annual data.

## 5. Secondary multivariable analysis

A8 added matched flow to T2 temperature separately by species and is secondary,
descriptive, and outside the primary hypothesis family. In the Chinook model,
the standardized temperature coefficient remained negative (beta = -0.240;
HC3 95% CI -0.478 to -0.001; p = 0.0490), whereas the flow coefficient was near
zero (beta = -0.035; 95% CI -0.307 to 0.238). Adjusted R-squared was 0.126 and
both VIFs were 1.006. The 2004 observation exceeded the Cook threshold; removing
it attenuated the temperature coefficient to -0.185 and its interval crossed
zero. Thus A8 is directionally consistent with A1 but is not independent
confirmatory evidence.

Neither predictor was distinguishable from zero in the Coho A8 model:
temperature beta = -0.034 (95% CI -0.416 to 0.348) and flow beta = 0.167 (95% CI
-0.207 to 0.541). Adjusted R-squared was -0.041. These models do not support a
claim that annual temperature or flow independently explains Coho returns.

## Interpretation boundary

This is a 29-year observational analysis using a reconstructed temperature
proxy and annual hatchery-return outcomes. It cannot identify causal effects,
migration delay, or the influence of unmeasured hatchery production, harvest,
ocean survival, habitat, and age structure. Threshold-count and other nonmean
thermal metrics remain exploratory and do not enter this synthesis. Any future
change to the frozen specification must be presented as a new analysis, not as
a replacement for these results.
