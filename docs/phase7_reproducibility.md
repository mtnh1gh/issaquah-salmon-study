# Phase 7 reproducibility guide

## Frozen hypothesis analysis

Phase 7 uses one deterministic program,
[`src/run_phase7_hypothesis_tests.py`](../src/run_phase7_hypothesis_tests.py),
rather than notebook experiments. The program validates the frozen protocol and
inputs, runs A1/A3/A5, A6/A7, every frozen sensitivity (including amendment
D-022), and the species-specific A8 models in the prescribed order. It stages
the entire result package and publishes the completion manifest last.

From the repository root, run:

```powershell
python -m pip install -r requirements.txt
python src/run_phase7_hypothesis_tests.py
python src/validate_phase7.py
```

The exact protocol version and SHA-256 are enforced by the program. Results,
diagnostics, input hashes, software versions, and deterministic seeds are under
[`outputs/phase7/`](../outputs/phase7/). Start with the machine-readable files
before narrative interpretation:

- [`phase7_primary_results.csv`](../outputs/phase7/phase7_primary_results.csv)
  for A1/A3/A5;
- [`phase7_mechanism_results.csv`](../outputs/phase7/phase7_mechanism_results.csv)
  for A6/A7;
- [`phase7_sensitivity_results.csv`](../outputs/phase7/phase7_sensitivity_results.csv)
  for alternate-window, T1, jack-inclusive, extrapolation, Cook, and
  temporal-trend sensitivities; and
- [`phase7_execution_metadata.json`](../outputs/phase7/phase7_execution_metadata.json)
  for protocol, program, input, seed, runtime, and package-version provenance.

The generated narrative is in
[`phase7_hypothesis_analysis_report.md`](../outputs/phase7/phase7_hypothesis_analysis_report.md).
The authoritative completion marker and artifact hashes are in
[`phase7_output_manifest.json`](../outputs/phase7/phase7_output_manifest.json).
[`src/validate_phase7.py`](../src/validate_phase7.py) is a
standard-library-only, output-reading validator that does not import or rerun
the analysis. It writes 28 structural, family, provenance, and separation
checks to
[`phase7_independent_validation.json`](../outputs/phase7/phase7_independent_validation.json).

## Frozen result and scientific-synthesis records

Post-freeze scientific synthesis is kept outside the immutable output package:

- [`phase7_results_freeze.json`](phase7_results_freeze.json) records the
  first-run commit and SHA-256 for every Phase 7 artifact;
- [`phase7_scientific_report.md`](phase7_scientific_report.md) gives the concise
  scientific result; and
- [`phase7_manuscript_results_plan.md`](phase7_manuscript_results_plan.md)
  defines the shared four-display package and hypothesis-centered Results
  outline for JEI and STS.

The frozen analysis protocol is
[`phase7_hypothesis_analysis_protocol.md`](phase7_hypothesis_analysis_protocol.md).
Do not overwrite the first-run package in response to statistical significance
or manuscript preferences. If a verified software bug requires correction,
retain the original package and write the corrected analysis to a separately
versioned output directory with new provenance and hashes.
