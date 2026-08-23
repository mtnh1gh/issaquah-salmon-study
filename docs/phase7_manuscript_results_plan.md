# Shared JEI and STS scientific-results plan

**Status:** Post-freeze synthesis plan  
**Applies to:** JEI manuscript and Regeneron STS research report  
**Numerical authority:** `outputs/phase7/` as frozen in
`docs/phase7_results_freeze.json`

Both manuscripts should use the same numerical results, formal support labels,
and four core displays. Their surrounding explanation may differ in depth, but
neither version should select a different window, result, or significance rule.
The scientific story is organized by hypotheses, not by pipeline phases.

## Four core displays

### Figure 1. T2 reconstruction and held-out validation

**Question answered:** Is T2 reliable enough to represent life-stage-specific
window-mean thermal exposure?

Use three compact panels:

- **A:** Observed King County grab temperature versus leave-one-year-out T2
  predictions, with a 1:1 line and the overall RMSE, MAE, and R-squared.
- **B:** Held-out RMSE for T2, T1, and monthly climatology overall and for the
  A1, A3, and A5 windows. Identify T2 as flow-independent and primary.
- **C:** Annual T2 window means for A1, A3, and A5 exposure years, 1995-2025;
  mark years whose window contains any extrapolation day without treating the
  flag as an observed error.

Primary sources are the T2 calibration table, model-comparison table,
hypothesis-window validation table, and life-stage exposure table. The caption
must say that T2 is a modeled window-mean proxy, not continuous observed water
temperature or regulatory 7DADMax. Put feature coefficients and the full
extrapolation audit in the supplement.

### Table 1. Primary life-stage thermal hypotheses

**Question answered:** Which prespecified salmon-temperature hypotheses received
formal support?

One row each for A1, A3, and A5. Include species, life stage, exposure window,
lag, n, expected sign, Spearman rho, bootstrap 95% CI, raw two-sided permutation
p, Holm-adjusted p, and frozen formal conclusion. Add one footnote for the HC3
effect-size interpretation, but keep Spearman plus Holm as the decision rule.

This table should make the family-level conclusion visually unavoidable: none
of A1/A3/A5 met family-wise alpha 0.05. Do not use stars on raw p-values and do
not promote the A1 supportive OLS interval over its Holm result.

### Figure 2. Prespecified robustness of the A1 Chinook association

**Question answered:** Does the moderate negative A1 association depend on a
single modeling choice, year, extrapolation flag, or broad temporal trend?

Use a horizontal coefficient-style plot of Spearman rho for primary T2, T1
replacement, alternate window, adults plus jacks, no-extrapolation rows,
highest-Cook removal, and detrended ranks. Show bootstrap intervals where the
frozen output provides them. Display the leave-one-year-out range as a separate
range glyph, not as a confidence interval. Use an open marker for detrended rho
because its unrestricted permutation p-value is intentionally absent.

The figure should emphasize direction and magnitude, not a collection of
unadjusted significance calls. Its caption should state that all sensitivity
inference is descriptive, the circular-shift result has only 29 possible
offsets, and A1 remains formally unsupported after primary-family correction.

### Table 2. Hydrologic mechanisms and secondary temperature-plus-flow models

**Question answered:** Which parts of the proposed hydrologic pathway were
observed, and did temperature retain an association when flow was included?

Use two clearly separated panels:

- **Panel A, confirmatory mechanism family:** A6 and A7 with relationship, n,
  rho, bootstrap CI, raw p, mechanism-family Holm p, and formal status.
- **Panel B, secondary A8:** species-specific standardized temperature and flow
  coefficients with HC3 intervals, adjusted R-squared, VIF, and the highest-Cook
  removal note. Label every A8 entry secondary/descriptive.

The table title and rule line must prevent A7's support or A8's nominal Chinook
temperature coefficient from being mistaken for confirmation of A1.

## What moves to the supplement or appendix

- complete engineering details for T1/T2 construction and coefficients;
- all 17 sensitivity rows and their descriptive p-values;
- all 87 leave-one-year-out results;
- complete extrapolation-day audits;
- regression residual, Q-Q, leverage, Cook, and VIF diagnostics;
- threshold-count and nonmean thermal metrics, labeled exploratory; and
- predictive modeling and future scenarios that do not answer the frozen
  life-stage hypotheses.

JEI can use the four displays with concise captions and plain-language
interpretation. STS can retain the same four displays in the main report and
route the fuller technical evidence to appendices. No numerical conclusion or
analysis role should differ between the two submissions.

## Hypothesis-centered Results outline

### 1. Temperature reconstruction and validation

**Purpose:** Establish that T2 is an adequate, flow-independent proxy for
biological-window mean temperature without turning model engineering into the
scientific result.

**Main result:** T2 leave-one-year-out RMSE was 0.788 C and only 0.9% above T1;
window-specific validation remained materially better than climatology. The
series was complete for 1995-2025, with extrapolation flags audited and retained
in the primary data.

**Display:** Figure 1.

**Required boundary:** Modeled proxy, not observed continuous temperature or
regulatory 7DADMax.

### 2. Life-stage-specific thermal hypotheses

**Purpose:** Report H1a/A1, H1b/A3, and H2/A5 together as the single frozen
primary family.

**Main result:** All three rhos were negative, but no hypothesis met the
family-wise alpha after Holm correction. A1 was moderate and nominal before
adjustment; A3 was near zero and A5 was weak and imprecise.

**Display:** Table 1.

**Required boundary:** State the multiplicity-adjusted conclusion before
discussing A1's raw p-value or supportive OLS estimate.

### 3. Robustness of the Chinook association

**Purpose:** Determine whether A1 weakened materially under the frozen
sensitivities.

**Main result:** A1 remained negative across T1, the alternate window,
jack-inclusive response, extrapolation exclusion, highest-Cook exclusion,
detrending, and every leave-one-year-out rerun. The result is stable in direction
and moderate in magnitude but uncertain after family correction.

**Display:** Figure 2.

**Required boundary:** Summarize the pattern in prose; do not enumerate every
unadjusted sensitivity p-value or call the signal confirmed/underpowered as a
fact.

### 4. Hydrologic mechanism tests

**Purpose:** Test H3/A6 and H4/A7 as a separate mechanism family.

**Main result:** A6 was unsupported. A7 was supported after mechanism-family
Holm correction, indicating that greater matched summer flow covaried with lower
T2 summer temperature.

**Display:** Table 2, Panel A.

**Required boundary:** A7 is an observational flow-temperature result and does
not repair the missing A6 link or establish a causal pathway to salmon returns.

### 5. Secondary multivariable analysis

**Purpose:** Describe A8 temperature and flow coefficients separately for
Chinook and Coho without changing the confirmatory conclusions.

**Main result:** Chinook temperature remained negative with flow included, while
the flow coefficient was near zero; the temperature interval crossed zero after
the highest-Cook year was removed. Neither Coho coefficient was distinguishable
from zero.

**Display:** Table 2, Panel B.

**Required boundary:** A8 is secondary/descriptive and cannot overwrite A1 or
A3. End Results here; reserve causal explanations, biological interpretation,
and alternative drivers for Discussion.

## Manuscript-level wording guardrails

Prefer: "associated with," "modeled temperature proxy," "supported by the
observational mechanism analysis," and "not supported by these data."

Avoid: "temperature reduced returns," "proved," "no effect," "continuous
observed temperature," "regulatory 7DADMax," "A1 was significant" without its
Holm qualifier, or "A1 survived" without naming the analysis as sensitivity.

The student should independently write the final JEI manuscript and STS report
and follow the applicable authorship and AI-use disclosure requirements.
