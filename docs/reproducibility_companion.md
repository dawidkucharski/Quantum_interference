# Quantum_interference reproducibility companion

Release tag: `submission-2026-04-28-q1`
Repository: `https://github.com/dawidkucharski/Quantum_interference`

The release tag is the authoritative pointer to the exact Git commit and public companion package.

This companion package is intentionally derived-data only. It does not include the full native Mountains/DigitalSurf `.sur` files because those raw exports are too large for normal Git history and remain available from the corresponding author on reasonable request. Instead, it provides the benchmark-grid surfaces and CSV artefacts needed to audit the manuscript-facing simulation benchmark.

## Contents

- `benchmark_grid_surfaces_256.npz`: area-averaged, detrended 256 x 256 benchmark-grid surfaces used as interferometric simulation inputs, stored in nm as `height_nm`; accompanying arrays include `valid_mask`, `x_um`, `y_um`, `stem`, `material`, and `treatment`.
- `benchmark_grid_manifest.csv`: one row per downsampled benchmark surface with group labels, lateral sampling, field of view, valid-pixel fraction, and height range.
- `derived_csv/`: public CSV outputs copied from `outputs/paper_alicona_benchmark/`, including per-surface benchmark rows and control summaries.
- `manuscript_tables/`: generated manuscript table sources used by the paper.
- `support_docs/`: public experimental-validation protocol.
- `CITATION.cff`: citation metadata for the public repository and companion package.
- `commands.txt`: exact full-regeneration and smoke-test commands.
- `environment.txt`: Python interpreter and package requirements used for this package.

## Full Regeneration Command

```bash
python scripts/run_paper_measured_benchmark.py
python scripts/run_paper_optprops.py
cd manuscript && latexmk -pdf -bibtex -interaction=nonstopmode main.tex
```

## Fast Smoke Regeneration Command

```bash
python scripts/run_paper_measured_benchmark.py --skip-benchmark --skip-resolution-sensitivity --skip-unwrap-control --skip-rate-model-control --skip-classical-frontier --skip-surface-metadata
cd manuscript && latexmk -pdf -bibtex -interaction=nonstopmode main.tex
```

## Determinism Notes

The measured-surface benchmark uses stable CRC32-derived seeds per surface, method branch, and Monte Carlo repetition. The canonical measured benchmark uses four repetitions per surface and method. The bootstrap confidence intervals use a fixed NumPy generator seed inside `scripts/make_benchmark_stat_tables.py`.

## Python Environment

`3.9.6 (default, Jan  9 2026, 11:03:41)  [Clang 17.0.0 (clang-1700.6.4.2)]`

Requirements:

```text
numpy>=1.26
scipy>=1.11
matplotlib>=3.8
pillow>=10.0
scikit-learn>=1.5
```
