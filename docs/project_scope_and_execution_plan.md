# Issaquah Creek Salmon Return Study

## 1. Updated project scope

### Authoritative scope and alignment
This document is the authoritative plan for the current project. It supersedes earlier proposal language that referred to the Snoqualmie and Cedar River watersheds or a 2030 projection horizon. The project README, notebooks, report, and metadata must use the scope below. Any future expansion to additional watersheds must be treated as a separately documented phase.

### Scope clarification
The study analyzes annual Chinook and Coho returns in the Issaquah Creek watershed, evaluates associations with environmental, hatchery, and urban stressors, and develops exploratory scenario-based projections through 2040. Results are decision-support evidence, not causal estimates or certain forecasts.

### Spatial and temporal unit
- **Watershed:** the delineated Issaquah Creek watershed used for each land-use calculation. Record the boundary source, version, area, and coordinate reference system in metadata.
- **Historical coverage:** 1985 through the most recent *complete and quality-checked* return year. Do not assume the final year in advance.
- **Time labels:** adult return observations retain their original return/calendar year. Hydrologic variables may also have a water-year field (October-September), but the transformation between the two must be documented.

### Study focus
This project will focus on Chinook and Coho salmon in Issaquah Creek because they are the most relevant and practical species for this study based on the repository’s current structure, the stated project goals, and the available return-data context.

### Species included in Phase 1
- Chinook salmon
- Coho salmon

### Species not included in Phase 1
- Steelhead: important ecologically, but better treated as a future extension because it would require a separate life-history and data approach.
- Chum, sockeye, and pink salmon: present in the broader Pacific Northwest, but not the best fit for the initial scope of this project.

### Scope statement
The study will analyze annual salmon return trends for Chinook and Coho in Issaquah Creek, evaluate environmental and urban stressors, and build predictive models to estimate future returns under alternative scenarios through 2040.

---

## 2. Study objectives

### Interpretation standard
- Report associations, predictive performance, and uncertainty; do not describe observational results as proven effects or impacts.
- Analyze total returns and natural-origin/wild adult returns separately when the data support it. Hatchery rack counts, escapement estimates, natural spawners, and jacks must never be silently combined.
- A null, unstable, or low-skill model is a valid result and must be reported.

1. Quantify long-term return trends for Chinook and Coho in Issaquah Creek.
2. Identify the environmental and land-use factors most associated with return variability.
3. Build a predictive model to estimate future returns.
4. Produce a clear awareness report for local decision-makers and partner organizations.

---

## 3. Data sources to collect

### Response variables
- WDFW escapement data for Issaquah Creek
- Annual salmon return counts by species

### Predictor variables
- Hatchery releases and smolt release records
- USGS streamflow and temperature data
- NRCS snowpack data
- NOAA PDO ocean index
- Impervious surface / land-use change data

### Data handling principles
- Preserve raw files in the raw-data folder.
- Use a cleaned master dataset for all analysis.
- Keep a data dictionary that explains variable definitions and units.
- Keep a source register for every dataset: provider, URL or query, access date, coverage, license/terms, counting method, spatial unit, transformation, and known limitations.
- Cache API downloads as dated raw files and record a checksum where practical; analyses must be rerunnable without live API access.
- Preserve observed values separately from interpolated, imputed, derived, or partner-provided values. Each must have a flag in the master dataset.

### Required analysis protocol before cleaning
Before merging data, write and commit an analysis protocol that specifies:

1. The primary and secondary response variables for each species.
2. The watershed boundary and data-source hierarchy.
3. The life-stage definitions and candidate lags.
4. The pre-specified predictor set, transformations, and missing-data rules.
5. The validation, tuning, and uncertainty procedures.
6. The scenario input sources and assumptions.

Changes after this point must be dated and justified in a decision log.

### Cohort and life-stage alignment rules
Predictors must be aligned to salmon life stage, not simply joined to the adult return year. The protocol must define species-specific candidate lags, justified by the data and biology. At minimum, assess approximately two-year Coho and three- to five-year Chinook return timing, while recognizing variable age at return. Match hatchery releases to plausible adult-return cohorts and, where feasible, calculate return-per-release or survival-type indicators. Assign freshwater rearing/outmigration conditions and marine/ocean conditions to their relevant years. Same-year adult-return predictors require a stated biological rationale.

---

## 4. Step-by-step execution plan

### Non-negotiable implementation requirements
The weekly tasks below are subject to the analysis protocol and data feasibility gate. If the available data cannot support the planned model complexity, prioritize transparent descriptive, trend, and association analyses over a complex forecast.

#### Data feasibility gate (end of Week 2)
Document, for every candidate response and predictor: coverage, missing years, units, measurement/counting method, source, spatial relevance, expected lag, and permission to publish. Confirm that the primary return series has enough complete years after the planned lags to support the analysis. If fewer than approximately 25 usable annual observations remain per species, reduce model complexity and predictors; do not fill unavailable response data simply to meet a target.

### Phase 1 — Project framing and data setup
Week 1
- Confirm the final scope and species focus.
- Review the project README and repository structure.
- Create or refine the project work plan.
- Define success metrics and deliverables.
- Create and approve the analysis protocol, source-register template, decision log, and report audience statement.
- Reconcile the proposal, README, code comments, and this plan to the authoritative Issaquah Creek / 2040 scope.

Week 2
- Identify and download all required raw data sources by category.
- Collect the core response data: annual Chinook and Coho return counts from Issaquah Creek.
- Collect management and production data: hatchery release records and smolt release counts.
- Collect environmental data: streamflow, water temperature, snowpack, and ocean condition indicators.
- Collect watershed stressor data: impervious surface and land-use change metrics.
- Collect optional supporting data if available: habitat condition, restoration activity, and local watershed context.
- Organize files into the correct folders.
- Create a data inventory and note missing or delayed sources.
- Draft a simple metadata file for each dataset.
- Complete the data feasibility gate before starting cleaning.

### Phase 2 — Data cleaning and master dataset construction
Week 3
- Clean and standardize each source dataset by category.
- Retain original dates and return years; create documented water-year fields only for appropriate hydrologic and climate variables.
- Align salmon return, release, hydrology, snowpack, ocean, and land-use data using the approved life-stage/cohort lag table.
- Check for missing values, duplicates, outliers, and obvious data entry errors.
- Create a data dictionary that documents variable names, units, and definitions.
- Add flags identifying observed, interpolated, imputed, derived, and externally supplied values.

Week 4
- Merge the cleaned datasets into a single master dataset.
- Validate the master dataset with basic sanity checks.
- Confirm that key response and predictor variables are present for both Chinook and Coho.
- Document assumptions, missing values, and any gaps in the data.
- Create a data-quality report with coverage by variable and species, missingness, transformations, and exclusions.
- Save the processed dataset for downstream use.
- Prepare the first data quality summary.

### Phase 3 — Exploratory analysis
Week 5
- Plot annual Chinook and Coho returns over time, clearly separating total and wild/natural-origin series where available.
- Create trend plots for flow, temperature, snowpack, PDO, and imperviousness.
- Compare species trends side by side.
- Review whether the current data suggest declines, stability, or recovery.

Week 6
- Run correlation analysis.
- Run trend tests such as Mann-Kendall.
- Compare pre-specified periods of low and high urban development only when sufficient observations exist; label these comparisons exploratory.
- Identify the strongest candidate drivers to investigate further.
- Report correlation confidence intervals or p-values with a multiple-testing strategy and account for autocorrelation where feasible.

### Phase 4 — Statistical analysis
Week 7
- Build small, regularized regression or other interpretable models to estimate associations between returns and pre-specified predictors.
- Evaluate the role of snowpack, flow, temperature, ocean conditions, and urbanization.
- Test lagged variables where they make biological sense.
- Check for multicollinearity and revise the model if needed.
- Check residual behavior, influential observations, temporal autocorrelation, and sensitivity to interpolation/imputation choices.

Week 8
- Compare model results across species and predictor sets.
- Summarize which variables have the strongest associations.
- Prepare the main statistical findings for the report.
- Describe variables as strongest associations, not effects, and report uncertainty and limitations.

### Phase 5 — Predictive modeling
Week 9
- Establish naive baselines (historical mean and persistence/trend where applicable).
- Use rolling-origin or expanding-window time-series cross-validation; feature selection and tuning must occur inside each training fold.
- Train an interpretable baseline model.
- Consider a constrained XGBoost model only if the feasibility gate and baseline validation show adequate sample support. Treat it as exploratory.
- Evaluate MAE, RMSE, and R-squared where meaningful, including comparison with the naive baselines.

Week 10
- Review feature importance.
- Compare model accuracy and interpretability.
- Decide which model is best for scenario-based projections.
- Quantify uncertainty using appropriate resampling, prediction intervals, or ensembles. Do not present feature importance as causal impact.
- Record all final model specifications, validation folds, random seeds, and selection rationale.

### Phase 6 — Scenario projections and reporting
Week 11
- Create scenario assumptions for optimistic, baseline, and pessimistic futures.
- Generate return projections through 2040.
- Create charts and summary tables for the results.
- Use cited, reproducible input trajectories. Distinguish controllable local inputs from external uncertainty; do not treat PDO as a controllable deterministic future input.
- Include prediction intervals, scenario assumptions, and applicability limits in every projection output.

Week 12
- Draft the awareness report.
- Write results in a language suitable for local decision-makers.
- Prepare final figures, tables, and conclusions.
- Review the full project package and identify any remaining gaps.
- Obtain and document a factual/domain review from a hatchery, WDFW, or watershed subject-matter reviewer when available; revise factual claims in response.

---

## 5. Weekly working rhythm

Each week should follow this pattern:
1. Review the previous week’s results.
2. Complete the planned analysis task.
3. Save the outputs in the appropriate folder.
4. Record assumptions, issues, and next steps.
5. Prepare a short summary for the next week.

---

## 6. Output folders

- data/bronze: original downloaded datasets, dated and checksummed per source (raw layer)
- data/silver: cleaned, source-conformed annual tables (silver layer)
- data/gold: joined, cohort-aligned, model-ready master dataset (gold layer)
- src: reusable data pipeline, feature engineering, and modeling code
- outputs/figures: charts and plots
- outputs/tables: analysis and model result tables
- docs: source/decision/validation registers and analysis reports

---

## 7. Recommended deliverables

- Clean master dataset
- Analysis protocol, source register, data dictionary, and decision log
- Data feasibility and data-quality summaries
- Exploratory analysis notebook
- Statistical analysis notebook
- Predictive modeling notebook
- Figures and charts
- Ranked stressor summary
- Scenario projection results
- Awareness report draft
- Reproducibility instructions and a locked environment/dependency specification

---

## 8. Recommended project governance

- Keep one main analysis notebook per stage.
- Save intermediate outputs so work can be resumed easily.
- Document major assumptions clearly.
- Revisit the scope if data availability changes significantly.
- Use version control for raw-data inventory metadata, code, notebooks, and final outputs; do not commit restricted raw data without permission.
- Include automated data-validation checks and one documented command or notebook sequence that rebuilds all processed data and outputs from cached inputs.
- Record substantive scope, method, source, and scenario changes in the decision log.

### Revised success criteria
The study succeeds when the workflow is transparent and reproducible, not when it reaches a preselected significance level or model score. Minimum completion criteria are:

1. An approved analysis protocol and complete source register are available with the project.
2. The cleaned dataset and data-quality summary clearly distinguish observed and derived values and document exclusions.
3. Trend and association analyses run end-to-end for every response series that meets the feasibility gate.
4. Any predictive model is compared with naive baselines using rolling time-series validation; weak performance is reported rather than hidden.
5. Scenario projections state all input assumptions and include uncertainty bounds or an explicit explanation of why bounds cannot be estimated.
6. The report distinguishes observed evidence, associations, projections, limitations, and management-relevant questions.
7. A documented factual/domain review is sought before release, and all notebooks and outputs can be rebuilt from cached permitted data.

---

## 9. Detailed data collection guidance and project rationale

To make the project execution plan more complete, the following detail should be treated as part of the working plan and used as guidance during the data collection and preparation phases.

### Data categories needed for the project

To support the analysis, the project needs data in these main categories:

#### 1. Salmon return data
This is the core response variable.

- Annual salmon return counts for Issaquah Creek
- Separate values for Chinook and Coho
- Preferred fields:
  - year
  - species
  - total returns
  - wild adults
  - hatchery adults
  - jacks if available

Why this matters:
- This is the main outcome being explained and predicted.

#### 2. Hatchery and release data
This helps capture human management influence and juvenile production.

- Annual smolt release counts
- By species:
  - Chinook
  - Coho
- Preferred fields:
  - year
  - species
  - number of smolts released
  - release location if available

Why this matters:
- Salmon returns are often influenced by how many juveniles were released or produced in previous years.

#### 3. Streamflow and water temperature data
These are key environmental stressor variables.

- Streamflow measurements
- Water temperature measurements
- Preferred fields:
  - date
  - discharge / flow
  - temperature
  - annual summary metrics such as:
    - mean flow
    - minimum summer flow
    - mean temperature
    - maximum summer temperature
    - number of days above a thermal stress threshold

Why this matters:
- Low flow and high temperature are strong stressors for salmon survival and spawning success.

#### 4. Snowpack data
This is an important climate and watershed signal.

- Snow water equivalent (SWE)
- Preferably from nearby SNOTEL stations
- Preferred fields:
  - year
  - April 1 snowpack
  - anomaly relative to a baseline period

Why this matters:
- Snowpack influences summer flow, temperature, and habitat conditions.

#### 5. Ocean condition data
This captures conditions during the marine phase of salmon life.

- Ocean climate indicators
- Most common example:
  - Pacific Decadal Oscillation (PDO)
- Preferred fields:
  - year
  - winter PDO average
  - lagged PDO values

Why this matters:
- Ocean conditions strongly affect marine survival and return patterns.

#### 6. Land use and urbanization data
This captures human development pressure in the watershed.

- Impervious surface coverage
- Urban growth / land-use change
- Preferred fields:
  - year
  - impervious percentage
  - change in impervious surface over time

Why this matters:
- Urban development can worsen runoff, temperature, habitat quality, and stream conditions.

#### 7. Habitat and watershed condition data
These are useful supporting variables if available.

- Habitat quality indicators
- Stream barriers
- Riparian condition
- Sediment or pollution indicators
- Watershed restoration activity if available

Why this matters:
- Habitat quality can strongly affect spawning success and juvenile survival.

#### 8. Optional contextual data
These are helpful but not strictly required at the start.

- Air temperature
- Precipitation
- Drought indices
- Flood frequency
- Local fishery or hatchery reports
- Management or restoration program records

Why this matters:
- They can improve interpretation but are not essential for the first version of the study.

### Recommended order to collect the data

1. Salmon return data
2. Hatchery release data
3. Streamflow and temperature data
4. Snowpack data
5. Ocean condition data
6. Land use / impervious surface data
7. Habitat condition data
8. Optional contextual data

### Suggested data collection strategy

For each category, collect:
- the raw source
- the time period covered
- the relevant variables
- a short note on how it will be used in the analysis

This will make the dataset easier to merge and validate later.

### Full project context and working assumptions

This project should be understood as a practical salmon recovery and watershed-analysis effort, not just a generic data exercise. The purpose is to build a defensible evidence base for understanding why salmon returns in Issaquah Creek vary over time and how local conditions may shape future outcomes.

#### Why this project matters
- It helps connect long-term salmon return patterns to environmental and human influences.
- It supports better communication with decision-makers, restoration partners, and stakeholder groups.
- It creates a repeatable analytic workflow that can be updated as new data become available.

#### Working context for the study
- The study is focused on Issaquah Creek, which is relevant for local watershed planning and salmon recovery discussions.
- The analysis will use annual time steps, with water years as the preferred framing where possible.
- The initial study will focus on Chinook and Coho because they are the most practical and relevant species for the first phase.
- Steelhead may be considered later if the project expands, but it is not part of the first phase.

#### Core framing of the analysis
- The main outcome is annual salmon return abundance.
- The analysis will test whether returns are associated with factors such as hatchery releases, streamflow, temperature, snowpack, ocean conditions, and urbanization.
- The study will not assume that a single cause explains all variation; instead, it will evaluate multiple plausible drivers.
- The work should be interpreted as an evidence-building process that can inform management discussion rather than provide a single definitive explanation.

#### Assumptions to carry into the analysis
- Publicly available and partner-provided data will be used where possible.
- Data quality and availability may vary by source, so some variables may be incomplete or require proxy measures.
- The project should prioritize a clean and transparent workflow over perfect completeness.
- Any missing or weak data should be clearly documented rather than silently ignored.
- Where direct return estimates are limited, the analysis should use the best available consistent series and note any limitations.

#### What the project should deliver
- A cleaned and documented master dataset.
- A clear summary of long-term return trends.
- Analysis of the strongest candidate drivers.
- Predictive models for future return estimates.
- A simple, decision-oriented report that can be shared with local partners and stakeholders.

#### Recommended interpretation standard
- Correlation does not equal causation.
- Model outputs should be treated as decision-support information, not absolute forecasts.
- Results should be communicated with appropriate caveats and confidence statements.

## 10. Execution controls and agent runbook

This section turns the scientific plan into an operational workflow. An agent or contributor must treat the registers and phase gates below as required project artifacts, not optional documentation.

### 10.1 Supporting files and ownership

Create these text-based files under `docs/` before collecting data. The project lead owns final approvals; the person or agent completing a task records the date, source, and decision.

| File | Purpose | Update trigger |
|---|---|---|
| `docs/analysis_protocol.md` | Locked study design, outcomes, lags, predictors, and validation approach | Before cleaning; then only with dated amendments |
| `docs/source_register.csv` | One row per acquired source or query | Every download, API request, or partner file |
| `docs/data_inventory.csv` | File-level coverage, schema, status, and quality | Every raw-file change |
| `docs/assumption_register.md` | Material scientific, data, and operational assumptions | When an assumption is made, tested, or retired |
| `docs/risk_register.md` | Risks, triggers, owners, mitigations, and status | Weekly review and any new risk |
| `docs/feature_registry.csv` | Definitions and lineage for all candidate features | Before feature engineering and after changes |
| `docs/model_registry.md` | Every trained model and validation result | Every model run retained for comparison |
| `docs/decision_log.md` | Scope, method, source, and scenario decisions | Immediately after a material decision |
| `docs/data_validation_report.md` | Results of automated and manual quality checks | Each processed-data build |

Suggested supporting folders: `docs/templates/`, `data/bronze/<source>/<access-date>/`, `data/silver/`, `data/gold/`, `outputs/tables/`, and `tests/`. Never overwrite a raw download; store a new dated snapshot.

### 10.2 Pipeline architecture

```text
Source register + acquisition log
            |
            v
Raw immutable snapshots -----> file/schema validation
            |                         |
            v                         v
Source-specific cleaning --> interim standardized tables
            |                         |
            +---- provenance and quality flags ----+
                                                   |
                                                   v
                          cohort/life-stage lag alignment
                                                   |
                                                   v
                         master analysis dataset + data dictionary
                                                   |
                    +------------------------------+-------------------+
                    v                                                  v
          EDA / trend / association analysis              forecasting validation and scenarios
                    |                                                  |
                    +--------------------> figures, tables, report <--+
                                                   |
                                                   v
                                      reproducibility and domain review
```

Each arrow is a reproducible code step. Each table must retain `source_id`, `raw_file`, `retrieved_at`, and value-status fields where applicable.

### 10.3 Phase exit criteria (Definition of Done)

Do not begin a later phase merely because its calendar week has arrived. The project lead records a pass, conditional pass, or stop-and-replan decision in the decision log.

| Phase | Exit criteria |
|---|---|
| 1. Framing and setup | Scope, response definitions, watershed boundary, analysis protocol, folder structure, registers, and software environment are present and reviewed. Each required source has a named acquisition route and fallback. |
| 2. Acquisition | Source register and inventory are complete; raw snapshots are immutable and readable; licenses/permissions are recorded; feasibility gate has passed or scope/model complexity has been reduced. |
| 3. Cleaning/master data | Source-specific checks pass; original values and transformations are traceable; cohort/lags are applied; data dictionary and validation report are complete; a clean build recreates the master dataset. |
| 4. EDA | All planned response plots, missingness plots, trend tests, and correlation outputs render from the master dataset; exploratory findings are labelled as such. |
| 5. Statistical analysis | Candidate models follow the protocol; diagnostic and sensitivity checks are saved; association language and uncertainty are correct. |
| 6. Predictive/scenario analysis | Naive baseline and rolling validation results are saved; retained model selection is justified; scenario inputs are cited and projection uncertainty is shown. |
| 7. Reporting/release | Report claims match results; factual/domain review is requested and recorded; notebooks/scripts run from cached permitted inputs; outputs, source citations, and limitations are complete. |

### 10.4 Data-acquisition runbook

For every source, follow this sequence: (1) create a `source_id`; (2) record the intended query and expected fields in the source register; (3) retrieve/download without modification; (4) save it in a dated raw directory using a descriptive filename; (5) calculate or record a checksum; (6) inspect schema and coverage; (7) add a data-inventory row; (8) record any deviation, access restriction, or known limitation in the decision and risk registers.

| Priority | Dataset | Collection procedure and acceptance rule |
|---|---|---|
| 1 | WDFW return/escapement data | Export the full Issaquah Creek query separately for Chinook and Coho. Preserve the exact filter values and download date. Confirm species, location, return year, count type, wild/hatchery origin, jacks, and units. Reconcile duplicate rows only using provider documentation; never sum rows of unknown stock or count type. |
| 2 | Hatchery releases | Query RMIS and/or obtain permitted FISH records. Record hatchery, species, release year/date, release location, life stage, number released, marks, and data owner. Confirm that release location is relevant to the response population before using it as a predictor. |
| 3 | USGS flow and water temperature | Retrieve daily values for the approved gauge and parameter codes, then cache the response. Record gauge location, datum, parameter, provisional/final status, timezone, and daily completeness. Derive annual metrics only after daily validation. |
| 4 | Snowpack | Retrieve April 1 SWE and, if used, daily/seasonal values for the approved station(s). Record station elevation, distance/relevance to watershed, reporting units, and baseline period for anomalies. A station is a climate proxy, not a direct watershed measurement. |
| 5 | Ocean conditions | Download the PDO series from NOAA and save the original file. Record the monthly-to-seasonal aggregation rule and the marine-life-stage lag. Treat projected PDO as uncertainty, not an intervention lever. |
| 6 | Imperviousness/land use | Save the watershed boundary first, then obtain every selected NLCD/King County layer. Record raster version, observation year, resolution, classification, clipping method, area calculation, and software. Keep observed years distinct from interpolated annual estimates. |
| 7 | Contextual habitat/restoration data | Record provider, spatial coverage, measurement method, date, and whether it is suitable as a quantitative predictor or only report context. Do not add a weakly documented variable simply because it is available. |

If a source is unavailable, record the failed route, wait time, alternate source, comparability assessment, and the decision to omit, substitute, or delay. Never substitute data from another watershed or a different count definition without an explicit documented comparability review.

### 10.5 Data validation rules

Implement these checks in code and save their results in the validation report. A failed critical check blocks the next phase until resolved or explicitly waived in the decision log.

| Check | Rule | Severity |
|---|---|---|
| Schema | Required columns exist; names, types, units, and controlled vocabularies match the source contract | Critical |
| Keys | No unexpected duplicate source rows; master data has at most one row per return year, species, and declared response definition | Critical |
| Coverage | Minimum/maximum dates, annual gaps, and completeness are reported for every variable | Critical |
| Range | Counts are non-negative; percentages are 0-100; dates parse; units and impossible physical values are flagged | Critical |
| Reconciliation | Total count is reconciled to components only when the provider defines them as additive | Warning/Critical if used as outcome |
| Spatial | Gauge/station/layer and watershed boundary match the approved source register entries | Critical |
| Provenance | Every master-data value has source and transformation/status information | Critical |
| Missingness | Missing values are counted before and after each transformation; no silent fill is permitted | Critical |
| Interpolation | Interpolated land-use values have an `interpolated` flag and sensitivity analysis excludes them or tests alternatives | Warning |
| Rebuild | A clean run recreates the same schema and expected row counts from cached raw inputs | Critical |

### 10.6 Assumption register

Each entry must include an ID, statement, rationale/source, affected outputs, owner, date, status (`untested`, `tested`, `accepted`, or `retired`), and what would invalidate it. Seed the register with these assumptions:

1. The selected WDFW series is a consistent representation of the intended Issaquah Creek response variable over time.
2. The selected hatchery release records represent fish plausibly returning to the studied population.
3. Chosen Coho and Chinook lags approximate relevant return-age distributions sufficiently for an exploratory analysis.
4. The selected gauge and snow station are suitable proxies for freshwater conditions in the study watershed.
5. Impervious-surface estimates use a stable watershed boundary and comparable products across years.
6. Missingness and any imputation are not so patterned that they invalidate the planned comparison.
7. Scenario inputs are illustrative conditional futures, not predictions of policy, ocean, or climate outcomes.

### 10.7 Risk register

Use a likelihood (L/M/H), impact (L/M/H), owner, trigger, mitigation, contingency, and status for each risk. Start with the following:

| Risk | Trigger | Mitigation and contingency |
|---|---|---|
| Response-series ambiguity | Multiple count definitions or unexplained discontinuity | Pause modeling; obtain provider definitions; select one primary series or report separate series. |
| Insufficient usable observations | Fewer than about 25 rows after lags or major gaps | Reduce predictors/model complexity; retain trends and descriptive results as primary output. |
| Data access or licensing delay | Portal fails, request remains unanswered, or sharing terms prohibit release | Use a documented public backup if comparable; otherwise omit variable and revise scope. |
| API/schema change | Retrieval fails or fields change | Cache raw snapshots, validate schema, update source adapter, and record version change. |
| Incorrect temporal alignment | A predictor is joined by adult return year without life-stage rationale | Block merge until lag table and biological justification are approved. |
| Leakage or overfitting | Test performance collapses or future information enters training | Use rolling validation, fewer predictors, and naive comparisons; report weak skill. |
| Confounded inference | Predictor estimates are unstable or correlated with trend/each other | Report associations only; use diagnostics and sensitivity analysis. |
| Unsupported scenario claim | Future input lacks a source or a plausible range | Remove it, use cited trajectory/range, or label the scenario illustrative. |
| Reproducibility failure | Clean rebuild fails or live API is required | Repair scripts, cache inputs, lock environment, and rerun before release. |

### 10.8 Feature registry and model registry

The feature registry is the contract between cleaning and modeling. One row is required for every candidate feature, including excluded features. Required columns: `feature_id`, `name`, `description`, `response_or_predictor`, `species`, `source_id`, `raw_fields`, `spatial_unit`, `temporal_aggregation`, `life_stage`, `lag_definition`, `units`, `transformation`, `missing_data_rule`, `value_status`, `leakage_risk`, `included_in_model`, and `rationale`.

The model registry records every retained experiment. Include: `model_id`, date, git commit/version, response definition, data-version ID, feature-registry version, training years, validation folds, preprocessing fitted within folds, algorithm/hyperparameters, random seed, naive comparator, MAE, RMSE, R-squared if meaningful, uncertainty method, diagnostic result, scenario eligibility, and decision (`retain`, `reject`, or `exploratory`). A model cannot be called final merely because it has the best in-sample score.

### 10.9 Software engineering and coding standards

- Keep source acquisition, transformation, features, modeling, visualization, and report rendering in separate modules or scripts; notebooks should orchestrate and explain rather than duplicate pipeline logic.
- Use deterministic file paths, explicit configuration, pinned dependencies, and fixed random seeds. Store configuration and scenario assumptions in versioned text files rather than notebook-only variables.
- Write functions with a single purpose, type hints where practical, docstrings stating input/output contracts, and clear exceptions. No placeholder data may be silently returned after an API failure.
- Add automated tests for schema validation, water-year/return-year conversion, lag calculations, duplicate handling, range checks, and a small end-to-end fixture build.
- Review code for target leakage before every model run. Fit scalers, imputers, feature selection, and tuning only on each training fold.
- Use stable naming: lowercase `snake_case` fields, ISO dates, explicit units in names where useful, and source-specific raw filenames. Never edit raw data manually.
- Keep generated figures/tables reproducible; do not hand-edit analytical values or charts. Record software versions and the git commit used for report outputs.

### 10.10 Agent execution order

1. Create the supporting files and populate the source register with planned sources.
2. Acquire and validate the two response datasets first; stop and resolve response-definition ambiguity before collecting optional predictors.
3. Acquire hatchery releases, then daily hydrology/temperature, snowpack, PDO, and land use in priority order.
4. Run the feasibility gate and record the approved response definitions, boundary, usable years, and lag table.
5. Build and validate source-specific interim tables, then the master dataset.
6. Execute EDA, associations, modeling, and scenarios only after the preceding phase gate passes.
7. Rebuild from cached raw data and complete the report/domain review before release.

### Suggested next action

Start with data collection and dataset organization in the next work block. That will provide the foundation for the rest of the analysis and help confirm whether any additional data sources are needed.
