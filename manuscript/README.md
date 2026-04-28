# Manuscript (MDPI LaTeX scaffold)

This folder contains the active MDPI manuscript in `main.tex`.

## What you need from MDPI
MDPI provides an official LaTeX class and bibliography style.

- Download the MDPI LaTeX template (contains `mdpi.cls` and `mdpi.bst`).
- Copy `mdpi.cls` (and any required `.sty` files) into this `manuscript/` folder.
- Ensure the BibTeX style file `mdpi.bst` is available to your LaTeX toolchain (placing it in `manuscript/` is simplest).

(We intentionally do **not** vendor the MDPI class/style files here.)

## Build
From the repository root:

```bash
cd manuscript
latexmk -pdf -bibtex -interaction=nonstopmode main.tex
```

Bibliography is wired to `references.bib` in this folder:
- `\bibliography{references}`

## Figures and tables
`main.tex` references figures already generated under `outputs/` and manuscript tables under `manuscript/tables/`.

Canonical paper workflows live in the repository root:
- `scripts/run_paper_measured_benchmark.py` regenerates the measured-surface benchmark figures, representative residual maps, PSD diagnostics, resolution/unwrap controls, tolerance summaries, and optional AI-selection artefacts.
- `scripts/run_paper_resolution_sensitivity.py` regenerates the targeted measured-benchmark grid-resolution control.
- `scripts/run_paper_unwrap_control.py` regenerates the targeted measured-benchmark unwrap-control table.
- `scripts/run_paper_optprops.py` regenerates the step-free optical-property sweep and its LaTeX table.
- `scripts/make_nonideal_stress_artifacts.py` regenerates the representative robustness figure/table from summary CSVs.
- `scripts/run_paper_detector_sensitivity.py` regenerates the targeted detector-model sensitivity figure/table.

The public reproducibility companion is indexed in `docs/reproducibility_companion.md`.

TikZ optical layouts are in:
- `manuscript/figures/tikz_layouts.tex`

## Next edits to make this submission-ready
- Finalise any remaining metadata and deposition identifiers.
- Keep manuscript inputs aligned with the canonical paper scripts above rather than exploratory output folders.
