# Risk register

| ID | Risk | Likelihood | Impact | Owner | Trigger | Mitigation | Contingency | Status |
|---|---|---|---|---|---|---|---|---|
| R-001 | Response definition changes over time | M | H | Project lead | Failed report reconciliation or provider notice | Preserve event-level data and reconciliation checks | Split periods or responses; pause modeling | Monitoring |
| R-002 | Fewer than 25 usable observations after lags | M | H | Analyst | Any species/model has fewer than 25 rows | Use pre-period environmental data and few predictors | Make descriptive trends primary | Mitigated |
| R-003 | RMIS releases remain unavailable | H | H | Project lead | No authenticated export | Keep missing; request RMIS/FISH records | Omit survival claims and qualify forecasts | Open |
| R-004 | NLCD extraction remains blocked | M | M | Analyst | WCS/requester-pays/email route unavailable | Retry official AOI route | Omit direct urbanization model | Open |
| R-005 | King County boundary redistribution violation | M | H | Project lead | Raw polygon proposed for public commit | Keep geometry ignored; commit checksum and provenance | Seek written permission | Mitigated |
| R-006 | Source API/schema changes | M | M | Analyst | Retrieval or required-field validation fails | Use cached immutable snapshots and schema checks | Update adapter with dated decision | Monitoring |
| R-007 | Incorrect life-stage alignment | M | H | Analyst | Same-year feature used without rationale | Enforce feature registry and lag columns | Remove feature and rerun | Monitoring |
| R-008 | Leakage or overfitting | H | H | Analyst | Random split, fold-external preprocessing, unstable validation | Rolling validation and naive baselines | Reject predictive model | Open |
| R-009 | Confounded environmental associations | H | H | Project lead | Trend/correlation instability or omitted-release concern | Association-only language and sensitivity analyses | Report descriptive results only | Open |
| R-010 | Unsupported scenario claim | M | H | Project lead | Input lacks cited range/source | Scenario eligibility review | Remove or label illustrative | Monitoring |
| R-011 | Rebuild or checksum failure | L | H | Analyst | Output schema/count/hash changes unexpectedly | Deterministic cached-input scripts | Block release and investigate | Monitoring |
| R-012 | Unmeasured harvest and pinniped predation losses | H | M | Project lead | Escapement variance unexplained by any retained environmental model | Cached supporting documents (2026-07-29) identify Puget Sound harvest/exploitation-rate reports and WRIA 8 Ballard Locks pinniped-predation materials as candidate sources; neither is machine-extracted yet | Extract a stock-specific harvest or predation index and test as a covariate; otherwise keep as a stated unmeasured-loss caveat | Open |
