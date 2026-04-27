# Hybrid quantum-inspired profilometry (simulation)

## Project aim (paper framing)
We consider a **rough reflective surface** measured with:

- a **classical Michelson-type interferometer** operated in **4-step phase-shifting interferometry (PSI)** mode, and
- a **quantum-inspired / coincidence-like photonic interferometer** where information is carried by a **fourth-order observable proxy**.

The aim is to determine when a **classical**, **direct quantum-like**, or **hybrid coarse-to-fine** pipeline is the more defensible choice for a given surface-metrology endpoint under matched count budgets.

## What this repo tests
This repo tests whether coincidence-like channels are useful as direct estimators, as auxiliary priors inside a hybrid architecture, or not at all for a given roughness regime and metrology target.

Primary endpoints (reported in `sweep.csv` and `summary.csv`):
- **Height RMSE after plane detrend** (texture-focused)
- **Step-height error** (metrology-focused for discontinuities)
- **Roughness bias** in Sa/Sq/Sz

Fairness / resource matching:
- Classical PSI uses Poisson shot noise with a nominal `--class-photons` (photons/pixel/frame).
- The coincidence branch can be matched across quantum models using `--quant-target-mean-counts` (mean coincidences/pixel/frame).
- Sweeps also record measured per-run budgets: `class_mean_counts_per_pixel_frame` and `quant_mean_counts_per_pixel_frame`.

If you want a simple “equal detected photons” heuristic for 4-step protocols:
- classical detected photons per pixel: $4\,N_{\mathrm{class}}$
- coincidence detected photons per pixel: $8\,N_{\mathrm{coinc}}$ (two detectors)
so a rough matching is $N_{\mathrm{coinc}} \approx N_{\mathrm{class}}/2$.

## Pipeline overview
Goal: build a reproducible simulation pipeline that compares

- **Classical interferometric profilometry** (second-order interference: intensity fringes)
- **Quantum-inspired / coincidence-like profilometry** (fourth-order interference proxy)

Both pipelines start from the same *ground-truth* surface height map $h(x,y)$, generate synthetic measurements, reconstruct $\hat h(x,y)$, and compare surface texture metrics.

## Current paper-level conclusion
- Classical PSI remains the default baseline when the target is the lowest detrended height RMSE or the most faithful fine-texture recovery.
- The strongest nonclassical result is the **hybrid coarse-to-fine** architecture, where the coincidence-like channel helps ambiguity handling while the classical branch still carries the fine texture.
- Direct quantum-like reconstruction is **selectively useful**, mainly for smoother finishing-style regimes and chiefly for envelope-weighted descriptors such as $S_q$ and $S_z$ rather than as a universal replacement for PSI.

## Why Python
Python gives us a compact scientific stack (NumPy/SciPy/Matplotlib) and easy packaging. If you prefer R later, we can port the same model.

## Quickstart
1. Create a venv and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
pip install -r requirements.txt
```

2. Run the demo end-to-end:

```bash
python scripts/run_demo.py --outdir outputs/demo
```

You can also run the same pipeline on a measured Mountains/DigitalSurf `.sur` surface:

```bash
python scripts/run_demo.py --outdir outputs/demo_sur --surface-sur data/1.4301_szlifowane.sur
```

## Batch processing measured `.sur` surfaces
If you have many measured surfaces in `data/` (different materials / treatments), you can generate a single metrics table:

```bash
python scripts/process_surfaces_sur.py --outdir outputs/surfaces_summary --nx 256 --ny 256
```

This writes:
- `outputs/surfaces_summary/summary.csv` (one row per `.sur` file)
- optional preview figures per file in `outputs/surfaces_summary/<stem>/` (disable with `--no-figs`)

Filename decoding:
- This repo assumes a convention like `<material_code>_<treatment_code>.sur` (example: `ELLOR_t_wyk.sur`).
- For reporting, scripts decode these codes into **English** `material` / `treatment` labels (and also keep `material_code` / `treatment_code`).
- The mapping lives in `src/qiprof/labels.py` and can be extended as you add more codes.

Example:
- `ELLOR_t_wyk.sur` → material: **Graphite** (code `ELLOR`), treatment: **turning (finishing)** (code `t_wyk`, Polish: *toczenie wykańczające*)

## Classical vs quantum-like on measured surfaces
To compare **classical**, **quantum-like**, and **hybrid** reconstruction performance on *measured* surfaces (grouped by material and by treatment):

```bash
python scripts/benchmark_sur_interferometry.py --outdir outputs/sur_benchmark --nx 256 --ny 256 --nreps 1
```

In this benchmark, the reference roughness values are computed on the native `.sur` grid after masking only explicit invalid pixels and removing a best-fit plane. The interferometric simulation itself still uses the downsampled benchmark grid selected by `--nx` and `--ny`.

Outputs:
- `outputs/sur_benchmark/per_surface.csv` (one row per surface × method × rep)
- `outputs/sur_benchmark/by_material.csv` (grouped summary)
- `outputs/sur_benchmark/by_treatment.csv` (grouped summary)

Tip: the synthetic wavelength can get extremely large if `lambda1` and `lambda2` are too close, which improves unambiguous range but makes height reconstruction very sensitive to phase noise. The demo defaults to a moderate wavelength difference; you can override:

```bash
python scripts/run_demo.py --outdir outputs/demo --lambda1-nm 810 --lambda2-nm 809 --quant-pairs 200000
```

This will generate:
- Figures comparing simulated signals and reconstructions
- A `metrics.json` summary (Sa, Sq, Sz, PSD summary)

## Sweep experiments (recommended for the paper)
Run a small parameter sweep to quantify where the synthetic-wavelength branch helps:

```bash
python scripts/run_sweep.py --outdir outputs/sweep --nreps 20 --step-nm 0 200 400 800 1200 --rms-nm 20 50 80 120
```

Convenience presets for manuscript-grade curves:

```bash
python scripts/run_sweep.py --outdir outputs/sweep_step_dense --nreps 20 --step-grid dense --rms-nm 50
python scripts/run_sweep.py --outdir outputs/sweep_rms_dense  --nreps 20 --rms-grid dense  --step-nm 0
```

This writes `outputs/sweep/sweep.csv` with per-run roughness bias and height RMSE.

You can also benchmark robustness to realistic PSI non-idealities (phase-step errors and drift):

```bash
python scripts/run_sweep.py --outdir outputs/sweep_drift --nreps 20 --step-nm 0 400 800 --rms-nm 50 80 \
	--phase-step-sigma-deg 2.0 --background-drift-frac 0.03 --amplitude-drift-frac 0.03 \
	--normalize-frames --hybrid-smooth-sigma-px 1.5
```

### Hero sweep (step-height metrology)
This sweep is tuned to produce a clean **step-height error** comparison figure (classical vs quantum-like vs hybrid), with Monte Carlo error bars:

```bash
python scripts/run_sweep.py --outdir outputs/sweep_step_hero --nreps 20 --nx 128 --ny 128 \
	--rms-nm 50 --step-nm 0 100 200 300 400 500 600 700 800 \
	--lambda1-nm 810 --lambda2-nm 800 \
	--phase-step-sigma-deg 2 --background-drift-frac 0.03 --amplitude-drift-frac 0.03 \
	--recon psi4 --hybrid-smooth-sigma-px 6.0

python scripts/plot_sweep.py outputs/sweep_step_hero \
	--outdir outputs/figures_step_hero --style photonics --layout twocol --formats pdf,png --dpi 400
```

Key outputs:
- `outputs/figures_step_hero/step_err_vs_step.pdf` (metrology-facing hero figure)
- `outputs/figures_step_hero/summary.csv` (table-friendly summary stats)

### Hero sweep (texture-only)
This sweep targets **surface texture fidelity** (no step), plotting reconstruction error and roughness bias vs RMS roughness:

```bash
python scripts/run_sweep.py --outdir outputs/sweep_texture_hero --nreps 20 --nx 128 --ny 128 \
	--step-nm 0 --rms-nm 20 50 80 120 \
	--lambda1-nm 810 --lambda2-nm 800 \
	--phase-step-sigma-deg 2 --background-drift-frac 0.03 --amplitude-drift-frac 0.03 \
	--recon psi4 --hybrid-smooth-sigma-px 6.0

python scripts/plot_sweep.py outputs/sweep_texture_hero \
	--outdir outputs/figures_texture_hero --style photonics --layout twocol --formats pdf,png --dpi 400
```

Key outputs:
- `outputs/figures_texture_hero/rmse_vs_rms.pdf`
- `outputs/figures_texture_hero/bias_Sq_vs_rms.pdf` (and Sa/Sz)

### Hero sweep (tunability / synthetic wavelength)
This sweep illustrates the **tunability tradeoff** by repeating the same texture-only scenario at several `lambda2` values (changing $\Lambda$), then plotting RMSE vs $\Lambda$.

```bash
for l2 in 809 805 800 780; do
	python scripts/run_sweep.py --outdir "outputs/sweep_lambda_hero_l2_${l2}" --nreps 10 --nx 128 --ny 128 \
		--step-nm 0 --rms-nm 50 --lambda1-nm 810 --lambda2-nm "$l2" \
		--phase-step-sigma-deg 2 --background-drift-frac 0.03 --amplitude-drift-frac 0.03 \
		--recon psi4 --hybrid-smooth-sigma-px 6.0
done

python scripts/plot_sweep.py outputs/sweep_lambda_hero_l2_809 outputs/sweep_lambda_hero_l2_805 outputs/sweep_lambda_hero_l2_800 outputs/sweep_lambda_hero_l2_780 \
	--outdir outputs/figures_lambda_hero --style photonics --layout onecol --formats pdf,png --dpi 400
```

Key output:
- `outputs/figures_lambda_hero/rmse_vs_lambda_eff.pdf`

## Literature & gaps
- Research gap → publishable claims: [docs/gaps_to_publications.md](docs/gaps_to_publications.md)
- Metrology-oriented new findings: [docs/new_findings.md](docs/new_findings.md)
- Working literature map (from Scopus export): [docs/literature_map.md](docs/literature_map.md)

## Paper-ready plots
After you have one or more sweep runs, generate figures with:

```bash
python scripts/plot_sweep.py outputs/sweep outputs/sweep_drift outputs/sweep_hybrid_smoke \
	--outdir outputs/figures --style photonics --layout twocol --formats png,pdf --dpi 600
```

This produces `png` plots and a `summary.csv` suitable for tables.

## Canonical paper workflows
For the manuscript, it is better to regenerate submission artefacts from a small number of fixed entry points than from many ad hoc commands.

Measured-surface branch:

```bash
python scripts/run_paper_measured_benchmark.py --tag paper_alicona_benchmark
```

This regenerates:
- `outputs/paper_alicona_benchmark/per_surface.csv`
- manuscript-facing figures under `outputs/paper_alicona_benchmark/figures/`
- targeted measured-benchmark controls under `outputs/paper_alicona_benchmark/resolution_sensitivity/` and `outputs/paper_alicona_benchmark/unwrap_control/`
- exploratory AI-selection artefacts under `outputs/paper_alicona_benchmark/ai_selection/`
- manuscript tables under `manuscript/tables/`

The measured-benchmark workflow now also refreshes:
- representative height/residual maps for automatically selected low-error, mid-regime, and direct-Q-failure cases
- a targeted resolution-sensitivity summary across benchmark grids
- a targeted unwrap-control table comparing the default separable unwrap with a least-squares Poisson unwrap

If you want to rerun those targeted controls directly:

```bash
python scripts/run_paper_resolution_sensitivity.py --tag paper_alicona_benchmark
python scripts/run_paper_unwrap_control.py --tag paper_alicona_benchmark
```

The current repository-local submission structure is indexed in `docs/submission_snapshot_manifest.md`.

The AI selection artefacts can also be refreshed directly from an existing measured benchmark:

```bash
python scripts/make_ai_selection_artifacts.py \
	--per-surface outputs/paper_alicona_benchmark/per_surface.csv \
	--outdir outputs/paper_alicona_benchmark/ai_selection \
	--out-table manuscript/tables/ai_method_selection.tex
```

If `per_surface.csv` already exists and you only want to refresh figures/tables:

```bash
python scripts/run_paper_measured_benchmark.py --tag paper_alicona_benchmark --skip-benchmark
```

Step-free optical-property branch:

```bash
python scripts/run_paper_optprops.py --tag paper_optprops_quick
```

Targeted non-ideality stress artefacts for the representative `Sq = 80 nm`, `R = 1.0`, `Vscale = 1.0` case:

```bash
python scripts/make_nonideal_stress_artifacts.py \
	--baseline-summary outputs/paper_optprops_quick/figures/summary.csv \
	--phase-summary outputs/paper_optprops_phasejitter_quick/figures/summary.csv \
	--drift-summary outputs/paper_optprops_drift_quick/figures/summary.csv \
	--drift-norm-summary outputs/paper_optprops_drift_norm_quick/figures/summary.csv \
	--out-table manuscript/tables/optprops_nonideal_stress.tex \
	--out-figure outputs/paper_optprops_nonideal_stress/nonideal_stress_summary.pdf
```

Targeted detector-model sensitivity artefacts for the same representative transition regime:

```bash
python scripts/run_paper_detector_sensitivity.py --tag paper_optprops_detector_sensitivity
```

Manuscript build:

```bash
cd manuscript
latexmk -pdf -bibtex -interaction=nonstopmode main.tex
```

## Model (high level)
- **Classical**: phase-shifting interferometry (PSI), 4-step algorithm.
- **Coincidence / quantum-sensing models (simulation)**: a coincidence signal modeled via a phase-dependent observable and an **effective wavelength**. We support multiple phenomenological interferometer models to compare quantum-sensing architectures under matched noise/drift conditions:
	- `diff`: difference/synthetic wavelength $\Lambda_{\Delta} = \frac{\lambda_1\lambda_2}{|\lambda_1-\lambda_2|}$ (long effective wavelength / large unambiguous range)
	- `sum`: sum-phase effective wavelength $\Lambda_{\Sigma} = \frac{\lambda_1\lambda_2}{\lambda_1+\lambda_2}$ (short effective wavelength)
	- `noon2`: 2-photon phase sensitivity (NOON-like, $\cos(2\phi)$), implemented as an effective wavelength $\lambda_1/2$
	- `su11`: SU(1,1) interferometer (same fringe period as $\lambda_1$; modeled phenomenologically as improved effective visibility via `--su11-gain`)

	By default, we simulate a 4-step *phase-stepped coincidence* protocol so we can use the same PSI phase estimator without `arccos` ambiguity.

	Detector/noise options:
	- `--quant-detector-model simple` (default): Poisson counting around a cosine mean (proxy)
	- `--quant-detector-model rates`: rate-based coincidences with **accidentals** via a coincidence window (`--tau-c-s`) and integration time (`--gate-time-s`)

	Fair comparison option:
	- `--quant-target-mean-counts X`: matches the quantum channel(s) to the same mean coincidence budget $X$ (counts/pixel/frame), so different interferometer models are compared at equal detected statistics.

Notes:
- This repo is a *simulation + methodology* project, not an experimental control stack.
- The quantum-like branch here is a **phenomenological forward model** for a coincidence observable rather than a complete experimental fourth-order transfer function.
- The current manuscript-level contribution is a **regime-dependent design rule**: classical PSI remains the default for fine-texture RMSE, hybrid coarse-to-fine reconstruction is the strongest nonclassical architecture, and direct quantum-like inversion is selectively useful rather than universally superior.

### Comparing quantum interferometer models
Example: run a small sweep that includes `diff`, `sum`, `noon2`, and `su11` and generates hybrid reconstructions for each (matched coincidence budget):

```bash
python scripts/run_sweep.py --outdir outputs/sweep_quant_models \
	--nreps 10 --nx 128 --ny 128 --rms-nm 50 --step-nm 0 400 800 \
	--lambda1-nm 810 --lambda2-nm 800 \
	--quant-interferometer diff sum noon2 su11 \
	--quant-detector-model rates --gate-time-s 1.0 --tau-c-s 1e-6 --eta1 0.6 --eta2 0.6 \
	--quant-target-mean-counts 20000 --su11-gain 0.5 \
	--phase-step-sigma-deg 2 --background-drift-frac 0.03 --amplitude-drift-frac 0.03 \
	--recon psi4 --hybrid-smooth-sigma-px 6.0
```

## Next steps
- Replace the current phenomenological quantum-like forward model with experimentally grounded fourth-order transfer expressions.
- Add more complete laboratory non-idealities, including detector imbalance, deadtime, accidentals, and visibility loss coupled to optical conditions.
- Validate whether the current regime map and hybrid advantage persist in an experimental implementation.
