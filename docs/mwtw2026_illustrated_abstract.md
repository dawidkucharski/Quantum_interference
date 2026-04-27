---
title: "Hybrid Quantum-Inspired Profilometry: A Benchmark on Measured Rough Surfaces"
---

Dawid Kucharski  
Division of Metrology and Measurement Systems, Institute of Mechanical Technology, Faculty of Mechanical Engineering, Poznan University of Technology, 60-965 Poznan, Poland  
Email: dawid.kucharski@put.poznan.pl

## Abstract

Quantum and quantum-inspired interferometric concepts are often proposed as routes to improved optical sensing, but their practical value for rough-surface profilometry remains unclear. Optical profilometry is widely used for surface-topography evaluation and on-line metrology [1]. Classical phase-shifting interferometry (PSI) remains a high-precision baseline, but practical deployment is limited by environmental sensitivity, phase-step errors, and photon-statistical constraints [2,3]. Coincidence-based and entanglement-inspired interferometric ideas have been proposed as possible routes towards improved sensing [4,5], yet metrology-facing comparisons on realistic rough surfaces under matched count budgets remain scarce.

This contribution presents the current state of a simulation-first benchmarking study comparing classical four-step PSI, direct coincidence-inspired reconstruction, and a hybrid coarse-to-fine strategy. The benchmark combines controlled synthetic sweeps with real focus-variation (FV) microscopy topographies exported as `.sur` files, which serve as common reference surfaces for all simulated measurement channels. Performance is assessed using detrended height RMSE, areal roughness errors (Sa, Sq, Sz), per-surface winner counts, and representative spatial-frequency fidelity.

The current results do not support a universal quantum advantage. Classical PSI remains the most reliable baseline for fine-texture recovery and lowest pointwise height error. Direct quantum-like reconstruction is only selectively useful, mainly for smoother finishing-style surfaces and chiefly for envelope-dominated descriptors such as Sq and Sz. The strongest nonclassical result is the hybrid strategy, in which coincidence-like information provides a coarse absolute-height prior while the final fine texture is preserved by the classical short-wavelength branch. In the measured-surface benchmark, the hybrid method gives the lowest median |Delta Sa| (197.0 nm), whereas the direct quantum-like branch gives the lowest median |Delta Sq| and |Delta Sz| (418.6 nm and 9498.0 nm). At the present project stage, the main conclusion is architectural: coincidence-based sensing appears most promising as an auxiliary ambiguity-resolving channel within a hybrid profilometer, rather than as a universal replacement for classical PSI. Ongoing work focuses on a more realistic coincidence model, stronger non-ideality analysis, and experimental validation.

## Current Project Goals

1. Replace the present phenomenological coincidence proxy with a more realistic fourth-order transfer model.
2. Extend the robustness study to stronger non-idealities, including drift, phase-step error, and background or accidental coincidences.
3. Translate the benchmark into an experimentally testable hybrid instrument concept.

## Selected Figures

![Measured-surface benchmark summary across all FV samples. Classical PSI and the hybrid branch remain the most texture-faithful estimators overall, whereas the direct quantum-like branch is only selectively competitive on smoother surfaces.](docs/mwtw2026_assets/rmse_measured_summary.png){ width=90% }

![Comparison of reconstructed roughness parameters against the FV reference values. The hybrid branch is strongest for Sa, whereas the direct quantum-like branch is selectively favourable for Sq and Sz.](docs/mwtw2026_assets/roughness_measured_summary.png){ width=90% }

## References

1. Vorburger TV, Teague EC. Optical techniques for on-line measurement of surface topography. Precision Engineering. 1981;3:61-83.
2. McDonnell EM, Deck LL. Solutions for environmentally robust interferometric optical testing. Proceedings of SPIE. 2020;11487.
3. Okamoto R, Tahara T. Precision limit for simultaneous phase and transmittance estimation with phase-shifting interferometry. Physical Review A. 2021;104:033521.
4. Richards RK. Quantum-entangled photon interferometry. Proceedings of SPIE. 2004;5531:17-23.
5. Rarity JG, Burnett J, Tapster PR, Paschotta R. High-visibility two-photon interference in a single-mode-fibre interferometer. EPL. 1993;22:95-100.