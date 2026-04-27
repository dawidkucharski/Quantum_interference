# From literature gaps to publishable findings

This project is intentionally shaped around the gap highlighted in **Scopus AI** (03 Feb 2026):

> Direct benchmarking between classical surface interferometry (PSI/white-light/speckle) and entangled-photon/fourth-order (coincidence) methods is rare.

Our contribution is not “quantum beats classical everywhere”; it is a *controlled, reproducible* framework that identifies **where** a synthetic (difference) wavelength and coincidence-style sensing can help surface texture metrology, and where classical methods remain dominant.

The most promising “new way” (and likely publishable) is a **hybrid, coarse-to-fine strategy**:

- Quantum-like synthetic wavelength channel provides a *coarse absolute height prior* with a large unambiguous range (good for steps/discontinuities).
- Classical short-wavelength PSI provides *fine sensitivity* to recover texture once the fringe order is disambiguated.

## Evidence-backed research claims (simulation-first)

### Claim A — Unambiguous range on stepped / discontinuous surfaces
**Hypothesis:** A synthetic wavelength $\Lambda = \frac{\lambda_1\lambda_2}{|\lambda_1-\lambda_2|}$ increases the unambiguous height range and reduces unwrap/fringe-count failures for large steps.

**Evidence to generate:**
- Sweep over step height (nm → µm)
- Compare classical vs synthetic-wavelength vs **hybrid (quantum-coarse + classical-fine)**
- Report: height RMSE, unwrap failure rate, roughness bias (Sa/Sq/Sz)

### Claim B — Low-light texture metrology regime
**Hypothesis:** In low photon (or low pair) budgets, coincidence-style sensing can preserve useful texture metrics at reduced sample irradiance.

**Evidence to generate:**
- Sweep over `photons_per_pixel` vs `pairs_per_pixel`
- Compare roughness parameter bias/variance vs ground truth
- Report: bias and spread across replicates (Monte Carlo)

### Claim C — Robustness under realistic non-idealities
Classical PSI is known to suffer from:
- phase-step errors,
- background/amplitude drift,
- vibration/turbulence (effectively phase noise),

while quantum-like schemes are limited by:
- losses, decoherence, reduced visibility, low detection efficiency.

**Evidence to generate (already wired into sweeps):**
- Phase-step jitter: `--phase-step-sigma-deg`
- Background drift: `--background-drift-frac`
- Amplitude drift: `--amplitude-drift-frac`

Report sensitivity of texture metrics to each non-ideality.

## Mapping to the current code

- Classical PSI simulator: `qiprof.sim_classical.simulate_psi4`
- Quantum-like, phase-stepped coincidence simulator: `qiprof.sim_quantum.simulate_coincidence_psi4`
- Reconstruction: `qiprof.reconstruct.reconstruct_psi4` + `unwrap_2d_simple`
- Hybrid unwrapping: `qiprof.reconstruct.unwrap_height_with_coarse`
- Texture metrics: `qiprof.metrics.roughness_metrics` + `roughness_errors`
- Benchmarking sweeps: `scripts/run_sweep.py` (writes `sweep.csv`)

## How this becomes a paper (minimal outline)

1. **Motivation & gap**: lack of unified benchmarking for surface texture metrics.
2. **Unified forward/inverse model**: same ground-truth $h(x,y)$, two measurement channels.
3. **Noise & non-idealities**: low-light, drift, phase-step errors.
4. **Results**: regimes where synthetic wavelength helps; regimes where classical wins.
5. **Discussion**: what’s needed for experimental feasibility (visibility, losses, detectors).

## What we should add next (high leverage)

- A more realistic unwrapping / failure detector (classical vs quantum-like).
- A structured “failure mode” taxonomy in the results (unwrap, drift, low SNR).
- Optional robust phase extraction (e.g., spatiotemporal PSI variants) for the classical baseline.
