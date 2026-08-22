# Issaquah Creek Salmon Return Study
## Hypothesis Framework and Phase 7 Analysis Plan for JEI Manuscript Preparation

**Status:** Research-planning document — not a manuscript and not a statement of results  
**Project:** Issaquah Creek Salmon Return Study  
**Purpose:** Convert the project's original observation-driven ideas into explicit, biologically grounded, testable hypotheses; identify the analyses needed before preparing a Journal of Emerging Investigators (JEI) manuscript; and separate pre-specified hypotheses from later exploratory modeling.

---

## 1. Why this document exists

The existing repository contains a broad environmental-data investigation of Chinook and Coho returns to Issaquah Creek, including long-term trends, environmental associations, predictive modeling, uncertainty analysis, and scenario work.

For a JEI manuscript, the project should be framed more narrowly around **hypothesis-driven salmon ecology**, with statistical and predictive methods used as tools rather than as the scientific subject of the paper.

This document therefore:

1. records the **observation-driven origins** of the project's snowpack and temperature hypotheses;
2. refines those ideas into testable biological hypotheses without changing their original intent;
3. distinguishes what the current data can test directly from mechanisms that remain literature-supported but unmeasured;
4. defines species- and life-stage-specific exposure windows;
5. identifies the additional analyses needed before manuscript writing;
6. distinguishes **primary/pre-specified** analyses from **exploratory/post-hoc** extensions; and
7. defines conservative interpretation rules so the final study does not overstate causality or predictive skill.

> **Important:** This plan should not be used to retroactively invent hypotheses that were not part of the student's original research intent. Where possible, hypothesis provenance should be cross-checked against the earliest project proposal, README, analysis protocol, commit history, notes, or other contemporaneous records.

---

## 2. Original observation-driven research ideas

The following two research ideas were reported as core hypotheses that motivated the project before the later modeling work.

### 2.1 Snowpack / hydroclimate observation

Years of ski racing in the Cascade region created a firsthand observation that winters with lower snow accumulation can lead to earlier melt and drier late-season conditions.

The original biological reasoning was:

**Lower winter/spring snowpack**  
→ earlier or reduced snowmelt contribution  
→ lower late-summer streamflow  
→ potentially warmer stream conditions  
→ less favorable conditions for salmon during biologically important freshwater periods.

This observation motivated the inclusion of snowpack as an a priori environmental variable.

### 2.2 Water-temperature observation

Volunteer experience with Friends of the Issaquah Salmon Hatchery (FISH) motivated a second hypothesis: warmer water during periods when salmon occupy Issaquah Creek may reduce successful return or survival because elevated temperature can increase physiological stress and disease risk and can reduce the suitability of migration or rearing habitat.

The original general prediction was:

**Warmer freshwater conditions during biologically relevant periods**  
→ greater thermal stress / poorer habitat conditions  
→ lower subsequent adult return numbers.

The updated analysis should test this idea with **species- and life-stage-specific temperature windows**, rather than one generic annual or summer temperature index.

---

## 3. Scientific corrections and scope boundaries

Several refinements are necessary to keep the hypotheses biologically accurate and consistent with what the available data can actually support.

### 3.1 Coho juvenile exposure: natural and hatchery fish must be distinguished

Natural-origin Coho commonly spend an extended freshwater rearing period before migrating to sea, making summer stream temperature biologically relevant to juvenile survival and growth.

However, Issaquah Hatchery Coho are hatchery-reared yearlings rather than fish that spend the entire juvenile year freely rearing in Issaquah Creek. WDFW documentation nevertheless shows that the Issaquah Hatchery uses Issaquah Creek as its principal surface-water source, with well water also used. Therefore, creek temperature may still be relevant to hatchery rearing conditions, but the biological pathway differs from that of naturally rearing juveniles.

**Interpretation rule:**

- If natural-origin and hatchery-origin adult return series can be analyzed separately, the juvenile-rearing temperature hypothesis should be tested separately by origin.
- If only total or hatchery-dominated adult returns are available consistently, the paper must not claim that all returning Coho spent a year naturally rearing in Issaquah Creek.

Primary source:
- WDFW / NOAA, *Lake Washington Final Environmental Assessment and FONSI* — Issaquah Hatchery water supply and hatchery program context:  
  https://wdfw.wa.gov/sites/default/files/hgmp-esa-documents/NEPA%20Documents/Lake%20Washington/Lake%20Washington%20Final%20EA%20and%20FONSI.pdf

### 3.2 Snowpack should be treated as a regional hydroclimate proxy unless direct basin snow data are obtained

Issaquah Creek originates in the Tiger/Taylor Mountain area and drains to Lake Sammamish. A Snoqualmie/Cascade SNOTEL series is therefore **not the direct snowpack feeding Issaquah Creek**.

The snowpack variable should be described as a **regional winter/spring hydroclimate indicator** unless a more spatially appropriate snow dataset is identified.

This changes the test from:

> "Does Issaquah snowpack control Issaquah Creek summer flow?"

into the more defensible question:

> "Does the selected regional spring snowpack indicator covary with late-summer Issaquah Creek flow strongly enough to function as a useful hydroclimate proxy?"

Primary source:
- King County, Issaquah Creek Capital Investment Strategy — basin headwaters in Tiger and Taylor Mountains:  
  https://kingcounty.gov/en/dept/dnrp/nature-recreation/environment-ecology-conservation/flood-services/capital-projects-studies/issaquah-creek-capital-investment-strategy

### 3.3 Thermal-stress mechanisms are explanatory, not directly measured outcomes

The project does not directly measure:

- individual physiological stress;
- disease incidence;
- dissolved oxygen effects;
- migration delay;
- juvenile mortality; or
- prespawn mortality.

These mechanisms can be cited from fisheries literature as biological rationale, but the project should not claim to have demonstrated them.

### 3.4 Migration timing should not be treated as an outcome unless timing data are acquired

Annual adult return counts can test associations with return abundance. They cannot by themselves test whether warmer water caused earlier/later migration.

If daily or weekly ladder counts, trap counts, median return dates, or another valid run-timing series becomes available, migration timing could become a separate future analysis. Otherwise, it should remain outside the primary response variables.

---

## 4. Species timing and biologically relevant exposure windows

FISH describes Chinook as the first returning salmon, with initial arrivals generally in late August and the bulk of the run from mid-September through mid-October. Coho generally arrive from late September through late November.

Source:
- Friends of the Issaquah Salmon Hatchery, seasonal return timing:  
  https://www.issaquahfish.org/category/seasons/

Based on that timing, the following windows should be treated as **candidate biologically motivated windows to validate against available monitoring data**, not immutable facts.

| Species | Life stage | Candidate exposure window | Scientific purpose |
|---|---|---:|---|
| Chinook | Adult entry / early migration | Aug 15–Sep 30 | Capture warm-water conditions as adults begin entering Issaquah Creek |
| Chinook | Full adult migration | Aug 15–Oct 31 | Sensitivity analysis around the full return season |
| Coho | Adult entry / migration | Sep 15–Oct 31 | Capture low-flow / transitional autumn conditions during early Coho return |
| Coho | Full adult migration | Sep 15–Nov 30 | Sensitivity analysis around the broader return season |
| Coho | Juvenile freshwater/rearing exposure | Jun 1–Sep 30 in the biologically appropriate cohort year | Test summer thermal exposure during freshwater rearing / hatchery water exposure |

**Before final analysis:** document the exact cohort-year mapping used for each species and life stage.

---

## 5. Refined hypothesis hierarchy

The manuscript should distinguish **primary biological hypotheses** from **secondary mechanistic hypotheses** and from **exploratory analyses**.

### H1 — Adult migration temperature hypothesis

**Biological question:** Are warmer Issaquah Creek temperatures during species-specific adult migration periods associated with lower adult return numbers?

**Prediction:** Years with higher migration-period temperature metrics will tend to have lower adult returns, after accounting for the study's small sample size and uncertainty.

**Species:** Chinook and Coho, analyzed separately.

**Directly observed in this study:** temperature metrics and adult return counts.

**Not directly observed:** thermal stress, disease, dissolved oxygen limitation, migration delay, or mortality mechanism.

---

### H2 — Coho juvenile/rearing temperature hypothesis

**Biological question:** Are warmer summer freshwater conditions during the appropriate juvenile/rearing year associated with lower subsequent Coho adult returns?

**Prediction:** Higher summer temperature exposure during the relevant juvenile/rearing period will be associated with lower subsequent Coho return abundance.

**Priority:** Highest biological priority if temperature data have adequate temporal resolution and cohort alignment can be justified.

**Origin-specific interpretation:**

- Natural-origin Coho: summer creek temperature represents natural rearing habitat exposure.
- Hatchery-origin Coho: interpretation must reflect hatchery rearing and Issaquah Creek water use rather than free-stream rearing.

---

### H3 — Regional snowpack → late-summer flow hypothesis

**Biological/hydrologic question:** Does lower regional spring snowpack correspond to lower late-summer Issaquah Creek discharge?

**Prediction:** Lower spring snowpack index values will be associated with lower late-summer streamflow.

This is an **intermediate mechanism test**, not a direct salmon-return hypothesis.

---

### H4 — Flow → stream-temperature hypothesis

**Question:** Are lower late-summer flows associated with warmer Issaquah Creek temperatures?

**Prediction:** Lower discharge will be associated with higher stream temperature during overlapping late-summer periods.

Again, this tests a proposed physical mechanism before linking the mechanism to salmon outcomes.

---

### H5 — Combined hydroclimate pathway

The conceptual pathway motivating the original snowpack hypothesis is:

```text
Regional spring snowpack
          ↓
Late-summer Issaquah Creek discharge
          ↓
Biologically relevant stream temperature
          ↓
Salmon return abundance
```

With the available observational sample, this should **not** be treated as a fully identified causal mediation model.

Instead, each link should be tested separately. The final interpretation should state which links are supported, weak, or unsupported by the available data.

---

## 6. Temperature metrics to derive

A single seasonal mean is unlikely to capture all biologically relevant thermal exposure. If continuous or sufficiently dense temperature records are available, derive the following metrics for each candidate exposure window.

### Core metrics

1. **Mean daily temperature** over the window.
2. **Maximum daily temperature** over the window.
3. **Maximum 7DADMax** — highest 7-day average of daily maximum temperature.
4. **Number of days exceeding 17.5°C**.
5. **Number of days exceeding 19°C**.
6. **Number of days exceeding 21–22°C**, only if enough observations occur to make the metric informative.
7. **Longest consecutive warm spell**, where data completeness supports it.

### Why 7DADMax matters

Washington Department of Ecology uses the **7-day average of daily maximum temperature (7DADMax)** in salmonid water-quality criteria. A 17.5°C criterion is used for certain salmonid spawning/rearing/migration designated uses. Ecology's technical review also describes increasing risk to adult migrants above roughly 17–19°C 7DADMax and migration barriers/direct mortality becoming more likely around 21.5–22°C.

These values should be treated as **regulatory/biological reference points**, not universal binary thresholds at which stress suddenly begins.

Sources:
- Washington Department of Ecology, *Salmon Creek Temperature TMDL*:  
  https://apps.ecology.wa.gov/publications/documents/1110044.pdf
- Washington Department of Ecology, *Evaluating Standards for Protecting Aquatic Life — Temperature Criteria*:  
  https://apps.ecology.wa.gov/publications/documents/0010070.pdf

### Data sufficiency rule

**Do not compute 7DADMax from sparse grab samples.** 7DADMax requires sufficiently frequent daily/continuous observations to calculate daily maxima and rolling seven-day means defensibly.

If the existing King County temperature series is based primarily on sparse seasonal grab samples, Phase 7 should first search for a continuous logger dataset covering Issaquah Creek. If continuous coverage is incomplete, analyses should be restricted to metrics supported by the actual sampling design.

---

## 7. Phase 7 analysis matrix

| Analysis | Exposure | Species | Life stage | Candidate window | Response | Priority |
|---|---|---|---|---|---|---|
| A1 | Stream temperature | Chinook | Adult migration | Aug 15–Sep 30 | Adult returns | High |
| A2 | Stream temperature | Chinook | Adult migration | Aug 15–Oct 31 | Adult returns | Sensitivity |
| A3 | Stream temperature | Coho | Adult migration | Sep 15–Oct 31 | Adult returns | High |
| A4 | Stream temperature | Coho | Adult migration | Sep 15–Nov 30 | Adult returns | Sensitivity |
| A5 | Stream temperature | Coho | Juvenile/rearing | Jun 1–Sep 30, cohort-aligned prior year | Subsequent adult returns | **Highest** |
| A6 | Regional snowpack | — | Hydroclimate | Apr 1 SWE / selected index | Late-summer Issaquah flow | High |
| A7 | Issaquah Creek flow | — | Hydroclimate | Jul–Sep or matched window | Stream temperature | High |
| A8 | Flow + temperature | Chinook/Coho | Species-specific | Matched windows | Adult returns | Secondary |

---

## 8. Statistical analysis principles

Because the project has approximately three decades of annual response observations, the analysis should prioritize **effect size, robustness, uncertainty, and biological interpretation** over model complexity.

### 8.1 Primary association tests

For each pre-specified hypothesis:

- plot the raw relationship before fitting a model;
- report sample size and missing years;
- estimate Spearman correlation for monotonic association;
- where justified, fit a simple interpretable regression;
- report effect size and uncertainty, not only p-values;
- inspect influential observations;
- avoid causal wording.

### 8.2 Robustness tests

For high-priority relationships, test sensitivity to:

- one-year window shifts;
- alternate biologically plausible exposure windows;
- exclusion of the highest-influence observation;
- response transformation if strongly skewed;
- origin-specific return definitions where possible;
- alternative snowpack proxy selection, if scientifically justified before examining the final salmon result.

### 8.3 Multiple testing

Primary hypotheses should be few and explicitly labeled. Exploratory analyses should be separated from confirmatory tests.

If multiple related tests are evaluated together, preserve the repository's conservative multiple-testing approach or document any revised correction strategy before examining final significance results.

### 8.4 Prediction is supporting evidence, not the hypothesis

Existing rolling-origin cross-validation and baseline comparisons remain valuable, but they should answer a **secondary question**:

> Do the biologically selected environmental measurements contain out-of-sample information beyond simple historical baselines?

The JEI manuscript should not use a hypothesis such as "the environmental model will outperform the baseline" as its central scientific hypothesis.

JEI guidance specifically rejects manuscripts whose main hypothesis is that an algorithm or machine-learning model will be accurate or outperform another model.

Source:
- Journal of Emerging Investigators, engineering and machine-learning project guidance:  
  https://emerginginvestigators.org/submissions/engineering-and-machine-learning-based-projects

---

## 9. Primary vs. exploratory analysis boundary

The repository currently includes later ocean-index extensions such as NPGO and ONI. These may be scientifically useful, but if they were added after inspection of the initial results they must remain clearly labeled **exploratory/post-hoc** in a manuscript.

### Primary / hypothesis-driven

- snowpack/hydroclimate hypothesis;
- temperature hypothesis;
- biologically justified life-stage windows;
- variables that can be documented as selected before the relevant outcome analysis.

### Secondary / supportive

- flow relationships;
- predictive cross-validation;
- baseline comparisons;
- uncertainty quantification.

### Exploratory

- later-added NPGO/ONI specifications;
- alternative ocean-index combinations selected after seeing initial results;
- future-scenario modeling.

### Recommended JEI scope exclusion

The Phase 6 scenarios through 2040 should probably remain in the repository but **outside the main JEI manuscript** unless a later reviewer identifies a compelling reason to include them. They answer a different question and risk distracting from the hypothesis-driven ecological study.

---

## 10. Decision rules for interpreting outcomes

The study should be considered informative even if the original hypotheses are not supported.

### Example outcome A

```text
Lower regional snowpack → lower late-summer flow        SUPPORTED
Lower flow → warmer stream temperature                  SUPPORTED
Warmer temperature → lower salmon returns               NOT SUPPORTED
```

Interpretation:

> The expected hydroclimate relationship is visible in the observational data, but adult-return variability is not explained adequately by stream temperature alone.

This would motivate consideration of ocean survival, hatchery production, harvest, age structure, disease, habitat, or other unmeasured factors.

### Example outcome B

```text
Regional snowpack → Issaquah Creek late-summer flow     NOT SUPPORTED
```

Interpretation:

> The selected regional snowpack series is not a sufficiently informative proxy for Issaquah Creek late-summer hydrology, so the original snowpack mechanism is not supported by these data.

### Example outcome C

```text
Coho juvenile-rearing temperature → later adult returns  NEGATIVE / ROBUST
Adult migration temperature → returns                    WEAK
```

Interpretation:

> Temperature may be more informative during the Coho freshwater-rearing stage than during adult migration, subject to origin composition, hatchery-water exposure, and unmeasured cohort factors.

No outcome should be described as demonstrating causation from observational data alone.

---

## 11. Highest-priority data improvements before manuscript writing

### Priority 1 — Continuous Issaquah Creek temperature data

Determine whether continuous daily/hourly temperature records exist for enough years to calculate life-stage-specific metrics and 7DADMax.

Potential sources to search:

- King County Environmental Monitoring / EIM;
- Washington Department of Ecology EIM;
- City of Issaquah;
- WDFW / Issaquah Hatchery monitoring records;
- FISH or watershed monitoring partners.

### Priority 2 — Annual hatchery release data

Adult return counts are difficult to interpret without annual juvenile production/release information. A renewed effort should be made to obtain annual Chinook and Coho release counts by brood/release year.

Potential sources:

- WDFW;
- Regional Mark Information System (RMIS);
- Issaquah Hatchery records;
- FISH;
- NOAA/WDFW hatchery program documents.

### Priority 3 — Origin-specific adult returns

Where reliable, separate hatchery-origin and natural-origin adult counts. The current repository already recognizes that origin reporting is not consistently comparable across the full 1997–2025 period, so analyses must respect the actual period of comparable data.

### Priority 4 — Run-timing data

If daily/weekly adult counts or trap-entry records can be obtained, migration timing could become a future response variable. Without those data, do not claim to test run timing.

---

## 12. Proposed manuscript scientific structure

This is a **research architecture**, not manuscript prose.

### Introduction

1. Issaquah Creek Chinook and Coho ecological context.
2. Biological relevance of thermal conditions.
3. Why life-stage timing matters.
4. Snowpack/hydrology as a proposed mechanism rather than a direct causal assumption.
5. Original observation-driven hypotheses.

### Results

**Result 1 — Hydroclimate context**  
Did regional spring snowpack covary with Issaquah Creek late-summer discharge, and did low flow covary with warm water?

**Result 2 — Adult migration temperature**  
Were species-specific migration-period thermal metrics associated with Chinook or Coho adult returns?

**Result 3 — Coho juvenile/rearing temperature**  
Were summer thermal conditions during the biologically appropriate cohort year associated with subsequent Coho returns?

**Result 4 — Robustness and uncertainty**  
How stable were the relationships to influential years, alternate windows, and origin definitions?

**Secondary result — Out-of-sample information**  
Did biologically selected environmental predictors improve predictive error relative to naive baselines?

**Exploratory result, if retained — Ocean indices**  
Clearly label later NPGO/ONI analyses as exploratory.

### Discussion

1. Which original hypotheses were supported, partly supported, or not supported?
2. Were the proposed hydrologic links present even when salmon-return links were weak?
3. Why might Chinook and Coho differ?
4. Hatchery production, ocean survival, harvest, habitat, age structure, and other unmeasured processes.
5. Limits of observational inference and small annual sample size.
6. What new data or prospective monitoring would provide the strongest next test?

---

## 13. JEI-specific framing

JEI requires hypothesis-driven science and does not consider "my model will be accurate" or "my model will outperform another algorithm" to be acceptable hypotheses.

Therefore, the manuscript should be framed as:

> **A salmon-ecology study testing biologically motivated temperature and hydroclimate hypotheses using long-term environmental observations.**

It should **not** be framed primarily as:

> an AI project, a machine-learning benchmark, or an exercise in optimizing prediction accuracy.

The project's reproducible pipeline, regression/ridge models, rolling-origin validation, bootstrap uncertainty, and baselines remain strengths, but they are **methods supporting the ecological question**.

JEI guidance:
- https://emerginginvestigators.org/submissions/engineering-and-machine-learning-based-projects

---

## 14. Hypothesis-provenance audit checklist

Before manuscript submission, locate and archive evidence showing when the original hypotheses and variables were selected.

- [ ] Earliest project proposal or research question
- [ ] Earliest README
- [ ] Earliest project scope/execution plan
- [ ] Original analysis protocol
- [ ] Early notes describing snowpack expectation
- [ ] Early notes describing water-temperature expectation
- [ ] Git commit dates showing when snowpack and temperature variables entered the project
- [ ] Date of first EDA/results output
- [ ] Date NPGO/ONI were added
- [ ] Clear distinction between pre-specified and exploratory analyses

If the exact original hypothesis language was not written down contemporaneously, document the evidence conservatively rather than reconstructing a more precise prediction than the record supports.

---

## 15. Phase 7 completion criteria

Phase 7 should be considered complete when:

1. species/life-stage temperature windows are justified by primary/local sources;
2. temperature sampling frequency and data coverage are documented;
3. 7DADMax is used only where continuous data make it valid;
4. snowpack is explicitly treated as either a validated regional proxy or an unsupported proxy;
5. the snowpack → flow and flow → temperature links have been tested;
6. adult migration temperature associations have been rerun using species-specific windows;
7. Coho juvenile/rearing temperature exposure has been tested with defensible cohort alignment;
8. origin-specific analyses are performed where data quality permits;
9. robustness to influential observations and alternative windows is documented;
10. primary, secondary, and exploratory analyses are clearly separated;
11. no causal claim exceeds the observational design; and
12. the manuscript can be organized around the original biological hypotheses without relying on post-hoc model selection.

---

## 16. Recommended next actions

1. **Audit available Issaquah Creek temperature datasets** for continuous daily/hourly records and coverage years.
2. **Map exact cohort years** for Coho juvenile/rearing exposure to adult return years.
3. **Re-audit the current snowpack source/station** and document why it is or is not a defensible regional proxy.
4. **Attempt to obtain hatchery release histories** before final adult-return modeling.
5. **Implement the Phase 7 hypothesis tests in a separate analysis module** so the original model pipeline remains reproducible.
6. **Write a Phase 7 results report before touching JEI manuscript prose.**
7. **Have a fisheries/ecology expert review the biological assumptions and life-stage mapping.**
8. Only after those steps, freeze the science and begin the student-authored JEI manuscript.

---

## 17. Core external references for this planning document

### Local salmon timing

Friends of the Issaquah Salmon Hatchery (FISH). *Seasons.*  
https://www.issaquahfish.org/category/seasons/

### Issaquah Hatchery / Coho / water-source context

Washington Department of Fish and Wildlife / NOAA. *Lake Washington Final Environmental Assessment and FONSI.*  
https://wdfw.wa.gov/sites/default/files/hgmp-esa-documents/NEPA%20Documents/Lake%20Washington/Lake%20Washington%20Final%20EA%20and%20FONSI.pdf

Washington Department of Fish and Wildlife. *Hatchery production, HGMPs and the ESA — Lake Washington programs.*  
https://wdfw.wa.gov/fishing/management/hatcheries/hgmp

### Issaquah Creek watershed geography

King County. *Issaquah Creek Capital Investment Strategy.*  
https://kingcounty.gov/en/dept/dnrp/nature-recreation/environment-ecology-conservation/flood-services/capital-projects-studies/issaquah-creek-capital-investment-strategy

### Salmonid temperature metrics

Washington Department of Ecology. *Salmon Creek Temperature Total Maximum Daily Load.*  
https://apps.ecology.wa.gov/publications/documents/1110044.pdf

Washington Department of Ecology. *Evaluating Standards for Protecting Aquatic Life in Washington's Surface Water Quality Standards — Temperature Criteria.*  
https://apps.ecology.wa.gov/publications/documents/0010070.pdf

### JEI hypothesis / computational-project guidance

Journal of Emerging Investigators. *Guidelines for Engineering- and Machine Learning-Based Projects.*  
https://emerginginvestigators.org/submissions/engineering-and-machine-learning-based-projects

---

## 18. Research-integrity note

This document is a **planning and critique artifact**, not a student-authored manuscript section. Any future JEI or Regeneron STS submission should follow the applicable authorship and AI-use policies. The student should independently write the final scientific manuscript/report and should disclose or log AI-assisted research support where required by the competition or journal.
