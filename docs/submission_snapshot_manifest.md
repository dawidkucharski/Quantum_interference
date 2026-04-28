# Submission Snapshot Manifest

This repository-local manifest records the canonical scripts, inputs, output folders, existing public GitHub commit, Zenodo-enabled repository status, and archive-ready bundle used by the current manuscript snapshot. It improves traceability inside the working project tree; the GitHub commit is the current public code reference, and the enabled GitHub-Zenodo bridge can mint a DOI-bearing manuscript release once the final submission snapshot is released on GitHub.

## Canonical Entry Points

- `scripts/run_paper_measured_benchmark.py`
- `scripts/run_paper_measured_rate_control.py`
- `scripts/run_paper_measured_nonideal_control.py`
- `scripts/run_paper_roughness_filter_control.py`
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

- Measured FV topographies: local `data/*.sur` files.

## Public Snapshot Policy

- The normal Git-tracked repository snapshot contains the manuscript sources, simulation code, and manuscript-facing generated artefacts.
- The submission-aligned public snapshot for the current manuscript corresponds to commit `708d8bb3610f` in `https://github.com/dawidkucharski/Quantum_interference`.
- Zenodo archiving is enabled for the GitHub repository `dawidkucharski/Quantum_interference`; create a manuscript-specific GitHub release from the final submission snapshot to mint the DOI-bearing Zenodo record.
- Insert the minted Zenodo DOI in the manuscript data-availability statement before journal submission.
- The full local `data/*.sur` set is excluded from normal Git history because the raw dataset is too large for a practical public GitHub snapshot.
- Raw SUR inputs are available from the corresponding author upon reasonable request.

## Canonical Output Folders

- `outputs/paper_alicona_benchmark/`
- `outputs/paper_alicona_benchmark/nonideal_control/`
- `outputs/paper_alicona_benchmark/roughness_filter_control/`
- `outputs/paper_optprops_quick/`
- `outputs/paper_optprops_nonideal_stress/`
- `outputs/paper_optprops_detector_sensitivity/`

## Archive-Ready Local Bundle

- Bundle: `outputs/submission_archive/quantum_interference_submission_708d8bb3610f.tar.gz`
- Checksum: `outputs/submission_archive/quantum_interference_submission_708d8bb3610f.tar.gz.sha256`
- SHA-256: `209103c0bbf99b2c322a0e0e5cbf978df679faa59db73444503c97548fe5cf61`
- Contents: manuscript source and PDF, generated manuscript-facing tables and figures, canonical code, documentation, benchmark outputs, and manifest files. Raw `data/*.sur` files are intentionally excluded and remain available on request.

## Notes

- The measured-benchmark workflow now also regenerates representative residual maps, a targeted resolution-sensitivity summary, an unwrap-control table, a full-dataset measured non-ideality control, and an approximate Gaussian roughness-filter sensitivity control.
- Public development repository: `https://github.com/dawidkucharski/Quantum_interference`.
- The repository may continue to evolve as the project and paper are revised; use commit `708d8bb3610f` for the manuscript-specific public code snapshot.
- The local archive bundle mirrors the submission snapshot and can be attached to the Zenodo-backed GitHub release if a compact archive is preferred in addition to the release source archive.