# Phase 3 validation report

Status: PASS

Checks passed: 9

- PASS: Trend table has 11 pre-specified tests
- PASS: Correlation table has 14 pre-specified tests
- PASS: Lag table has 12 pre-specified tests
- PASS: Every primary correlation uses all 29 return years
- PASS: All adjusted correlation p-values are valid
- PASS: All adjusted trend p-values are valid
- PASS: Only the two documented blocked fields are entirely unavailable
- PASS: All four expected figures are present
- PASS: Exploratory analysis report is present

Run after regenerating the EDA outputs:

```powershell
.\.venv\Scripts\python.exe .\src\validate_phase3.py
```
