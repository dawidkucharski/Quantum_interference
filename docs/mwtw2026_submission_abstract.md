---
title: "Hybrid Quantum-Inspired Profilometry: A Benchmark on Measured Rough Surfaces"
---

Dawid Kucharski  
Division of Metrology and Measurement Systems, Institute of Mechanical Technology, Faculty of Mechanical Engineering, Poznan University of Technology, 60-965 Poznan, Poland  
Email: dawid.kucharski@put.poznan.pl

## 1. Background and Aim

Optical profilometry remains an important route for surface-topography evaluation in precision manufacturing and functional-surface metrology [1]. Classical PSI is a strong baseline for high-precision surface measurement, but its practical performance can be limited by environmental sensitivity, phase-step error, and photon-statistical constraints [2,3]. In parallel, coincidence-based and entanglement-inspired interferometric schemes have been proposed as possible routes towards improved sensing [4,5]. What remains insufficiently explored is whether such schemes improve practically relevant rough-surface metrology endpoints under fair comparison conditions.

The aim of the present work is therefore not to claim a generic quantum advantage, but to determine when a coincidence-inspired channel should replace a classical PSI branch, when it should support that branch, and when it should be avoided. The benchmark is designed to extract a regime-dependent architectural recommendation rather than a single winner.

## 2. Benchmark Formulation

The study uses a common-surface framework. Real measured surfaces acquired by FV microscopy are exported as Mountains/DigitalSurf `.sur` files and treated as reference topographies. The same measured surfaces are then used to generate simulated classical photon-counting PSI frames and simulated coincidence-like measurements, allowing direct comparison of reconstruction pipelines on identical input topography.

Three reconstruction strategies are evaluated: classical four-step PSI, direct quantum-like reconstruction, and a hybrid coarse-to-fine method. In the hybrid branch, the coincidence-inspired channel provides only coarse or ambiguity-resolving height information, while the final fine texture is carried by the short-wavelength classical PSI branch. The coincidence channel is treated here as a phenomenological architecture proxy rather than a complete laboratory-grade fourth-order transfer model, so the present conclusions should be interpreted as benchmark-guided architectural evidence rather than as final experimental proof.

## 3. Current Results

Figure 1 summarises the measured-surface height benchmark across the FV dataset. The hybrid branch achieves the lowest median height RMSE (558.6 nm) and wins on the most surfaces (24 of 59), followed closely by the direct quantum-like branch (710.8 nm, 23 wins). Classical PSI yields the highest median RMSE (1227.4 nm, 12 wins) under matched count budgets. Figure 2 shows the corresponding roughness-parameter comparison. The hybrid method is strongest for Sa (26 wins), while the direct quantum-like branch is selectively favourable for Sq and Sz — particularly Sz, where it dominates (37 of 59 wins).

The data support a regime-dependent conclusion rather than a single universal winner. For overall height fidelity and Sa recovery, the hybrid strategy is the strongest option. For envelope-dominated descriptors such as Sq and Sz, the direct quantum-like branch is selectively competitive. Classical PSI, although a well-established baseline, does not dominate any metric in this matched-budget benchmark, suggesting that its advantage lies in experimental maturity rather than in photon-statistical efficiency.

![Figure 1. Measured-surface benchmark summary across all FV samples. Classical PSI and the hybrid branch remain the most texture-faithful estimators overall, whereas the direct quantum-like branch is only selectively competitive on smoother surfaces.](docs/mwtw2026_assets/rmse_measured_summary.png){ width=90% }

![Figure 2. Comparison of reconstructed roughness parameters against the FV reference values. The hybrid branch is strongest for Sa, whereas the direct quantum-like branch is selectively favourable for Sq and Sz.](docs/mwtw2026_assets/roughness_measured_summary.png){ width=90% }

## 4. Conclusions

At the current stage of the project, the strongest conclusion is architectural. The hybrid coarse-to-fine strategy — where a coincidence-like channel resolves ambiguity and the classical branch preserves fine texture — outperforms both standalone methods across the benchmark. Ongoing work is focused on a more realistic coincidence model, stronger treatment of non-idealities, and experimental validation of the hybrid concept.

## References

1. Vorburger TV, Teague EC. Optical techniques for on-line measurement of surface topography. Precision Engineering. 1981;3:61-83.
2. McDonnell EM, Deck LL. Solutions for environmentally robust interferometric optical testing. Proceedings of SPIE. 2020;11487.
3. Okamoto R, Tahara T. Precision limit for simultaneous phase and transmittance estimation with phase-shifting interferometry. Physical Review A. 2021;104:033521.
4. Richards RK. Quantum-entangled photon interferometry. Proceedings of SPIE. 2004;5531:17-23.
5. Rarity JG, Burnett J, Tapster PR, Paschotta R. High-visibility two-photon interference in a single-mode-fibre interferometer. EPL. 1993;22:95-100.