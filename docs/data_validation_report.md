# Data validation report

Generated: 2026-07-29T09:23:22-07:00

Inputs are cached local snapshots; no live API was used.

| Category | Check | Severity | Result | Details |
|---|---|---|---|---|
| Schema | Required master columns | Critical | PASS | Required columns: 28 |
| Keys | Unique return_year/species | Critical | PASS | Duplicate groups: 0 |
| Coverage | Expected species and years | Critical | PASS | Species: Chinook, Coho; years: 1997-2025 (29) |
| Coverage | Expected row counts | Critical | PASS | Returns=58; environment=34; master=58 |
| Range | Non-negative fish counts | Critical | PASS | Invalid rows: 0 |
| Range | Environmental physical bounds | Critical | PASS | Invalid rows: 0 |
| Reconciliation | Response component equations | Critical | PASS | Invalid rows: 0 |
| Reconciliation | Published WDFW checks | Critical | PASS | Failures: 0 |
| Temporal | Protocol cohort and marine alignment | Critical | PASS | Invalid rows: 0 |
| Missingness | No missing core values | Critical | PASS | Rows with missing core values: 0 |
| Missingness | Blocked fields are blank and flagged | Critical | PASS | Checked impervious_pct and hatchery_releases on 58 rows |
| Coverage | Temperature sample threshold | Critical | PASS | Rows below four samples: 0 |
| Provenance | Source and value-status fields | Critical | PASS | Invalid rows: 0 |
| Registry | Feature registry contract | Critical | PASS | Features registered: 13; duplicate IDs: False |

## Gate decision

**PASS.** Phase 2 validation has no critical failures. The dataset may proceed to exploratory analysis under the locked protocol.

Known unavailable fields remain impervious_pct and hatchery_releases; both are blank and explicitly flagged rather than imputed.
