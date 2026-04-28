# Submission Snapshot Manifest

This repository-local manifest records the canonical scripts, inputs, output folders, public GitHub release, Zenodo DOI, and archive bundle used by the current manuscript snapshot. It improves traceability inside the working project tree; the GitHub release and Zenodo record are the current public code references for the manuscript-facing snapshot.

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
- `scripts/make_q1_reproducibility_package.py`

## Canonical Manuscript Sources

- `manuscript/main.tex`
- `manuscript/references.bib`
- `manuscript/tables/*.tex`
- `manuscript/figures/*.tex`

## Submission Support Files

- `docs/photonics_cover_letter_draft.md`
- `docs/experimental_validation_protocol.md`
- `docs/reproducibility_companion.md`

## Canonical Input Data

- Measured FV topographies: local `data/*.sur` files.
- Derived public benchmark-grid surfaces: `outputs/submission_archive/q1_reproducibility_companion/benchmark_grid_surfaces_256.npz`.
- Derived public benchmark-grid manifest: `outputs/submission_archive/q1_reproducibility_companion/benchmark_grid_manifest.csv`.

## Public Snapshot Policy

- The normal Git-tracked repository snapshot contains the manuscript sources, simulation code, and manuscript-facing generated artefacts.
- The Q1 submission-aligned public snapshot for the current manuscript is fixed by GitHub release tag `submission-2026-04-28-q1` in `https://github.com/dawidkucharski/Quantum_interference`.
- Zenodo archives repository releases under concept DOI `10.5281/zenodo.19844594`; each GitHub release receives its own version DOI under that concept record.
- GitHub release URL: `https://github.com/dawidkucharski/Quantum_interference/releases/tag/submission-2026-04-28-q1`.
- The full local `data/*.sur` set is excluded from normal Git history because the raw dataset is too large for a practical public GitHub snapshot.
- The release companion archive supplies the derived 256 x 256 benchmark-grid surfaces used by the simulator, public CSV summaries, generated table sources, exact regeneration commands, and checksums.
- Raw native-resolution SUR inputs remain available from the corresponding author upon reasonable request.

## Canonical Output Folders

- `outputs/paper_alicona_benchmark/`
- `outputs/paper_alicona_benchmark/nonideal_control/`
- `outputs/paper_alicona_benchmark/roughness_filter_control/`
- `outputs/paper_optprops_quick/`
- `outputs/paper_optprops_nonideal_stress/`
- `outputs/paper_optprops_detector_sensitivity/`
- `outputs/submission_archive/`

## Q1 Reproducibility Companion

- Generator: `scripts/make_q1_reproducibility_package.py`
- Bundle: `outputs/submission_archive/quantum_interference_reproducibility_submission-2026-04-28-q1.tar.gz`
- Checksum: `outputs/submission_archive/quantum_interference_reproducibility_submission-2026-04-28-q1.tar.gz.sha256`
- SHA-256: `a667377f36eb48515c26502a4b141f3df5e167b80c4c8c14d9588fe72c5a4b49`
- Contents: derived 256 x 256 benchmark-grid surfaces (`benchmark_grid_surfaces_256.npz`), benchmark-grid manifest, public CSV outputs, generated manuscript table sources, submission-support docs, exact regeneration commands, and Python environment summary. Raw native-resolution `data/*.sur` files are intentionally excluded.

## Legacy Local Bundle

- Bundle: `outputs/submission_archive/quantum_interference_submission_708d8bb3610f.tar.gz`
- Checksum: `outputs/submission_archive/quantum_interference_submission_708d8bb3610f.tar.gz.sha256`
- SHA-256: `209103c0bbf99b2c322a0e0e5cbf978df679faa59db73444503c97548fe5cf61`
- Contents: manuscript source and PDF, generated manuscript-facing tables and figures, canonical code, documentation, benchmark outputs, and manifest files. Raw `data/*.sur` files are intentionally excluded and remain available on request.

## Notes

- The measured-benchmark workflow now also regenerates representative residual maps, a targeted resolution-sensitivity summary, an unwrap-control table, a full-dataset measured non-ideality control, an approximate Gaussian roughness-filter sensitivity control, and the Q1 reproducibility companion package.
- Public development repository: `https://github.com/dawidkucharski/Quantum_interference`.
- The repository may continue to evolve as the project and paper are revised; use release `submission-2026-04-28-q1` for the manuscript-specific public code snapshot.
- The Q1 companion archive is intended as the reviewer-facing derived-data bundle for auditing the benchmark without the full native SUR files.