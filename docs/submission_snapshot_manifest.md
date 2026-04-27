# Submission Snapshot Manifest

This repository-local manifest records the canonical scripts, inputs, and output folders used by the current manuscript snapshot. It improves traceability inside the working project tree, but it is not a substitute for public archival deposition and does not provide a DOI.

## Canonical Entry Points

- `scripts/run_paper_measured_benchmark.py`
- `scripts/run_paper_measured_rate_control.py`
- `scripts/run_paper_resolution_sensitivity.py`
- `scripts/run_paper_unwrap_control.py`
- `scripts/run_paper_classical_two_color_control.py`
- `scripts/run_paper_classical_frontier_control.py`
- `scripts/run_paper_surface_metadata.py`
- `scripts/make_benchmark_stat_tables.py`
- `scripts/select_experimental_validation_subset.py`
- `scripts/run_paper_optprops.py`
- `scripts/make_nonideal_stress_artifacts.py`
- `scripts/run_paper_detector_sensitivity.py`

## Canonical Manuscript Sources

- `manuscript/main.tex`
- `manuscript/references.bib`
- `manuscript/tables/*.tex`
- `manuscript/figures/*.tex`

## Submission Support Files

- `docs/photonics_cover_letter_draft.md`
- `docs/experimental_validation_protocol.md`

## Canonical Input Data

- Measured FV topographies: `data/*.sur`

## Canonical Output Folders

- `outputs/paper_alicona_benchmark/`
- `outputs/paper_optprops_quick/`
- `outputs/paper_optprops_nonideal_stress/`
- `outputs/paper_optprops_detector_sensitivity/`

## Notes

- The measured-benchmark workflow now also regenerates representative residual maps, a targeted resolution-sensitivity summary, and an unwrap-control table.
- Public archival deposition is still pending; until then, this manifest only identifies the local submission snapshot structure.