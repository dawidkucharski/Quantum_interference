# MwTW 2026 Final Abstract

## Title

Hybrid Quantum-Inspired Profilometry: A Coincidence-Proxy Benchmark on Measured Rough Surfaces

## Author

Dawid Kucharski

## Affiliation

Poznan University of Technology

## Email

dawid.kucharski@put.poznan.pl

## Abstract

Optical profilometry remains an important route for surface-topography evaluation in precision manufacturing and functional-surface metrology [1]. Classical PSI is a strong baseline for high-precision surface measurement, and robust practical implementations remain an active concern in interferometric testing [2]. Its performance can also be limited by phase-step error and photon-statistical estimation constraints [3]. In parallel, quantum-entangled photon interferometry [4] and high-visibility two-photon interference schemes [5] have been proposed as possible routes towards improved sensing. What remains insufficiently explored is whether such schemes improve practically relevant rough-surface metrology endpoints under fair-comparison conditions.

The aim of the present work is therefore not to claim a generic quantum advantage, but to determine when a coincidence-inspired channel should replace a classical PSI branch, when it should support that branch, and when it should be avoided. The benchmark is designed to extract a regime-dependent architectural recommendation rather than a single winner.

The study uses a common-surface framework. Real measured surfaces acquired by focus-variation microscopy are exported as Mountains/DigitalSurf .sur files and treated as reference topographies. The same measured surfaces are then used to generate simulated classical photon-counting PSI frames and simulated coincidence-like measurements, allowing direct comparison of reconstruction pipelines on identical input topography.

Three reconstruction strategies are evaluated: classical four-step PSI, direct quantum-like reconstruction, and a hybrid coarse-to-fine method. In the hybrid branch, the coincidence-inspired channel provides only coarse or ambiguity-resolving height information, while the final fine texture is carried by the short-wavelength classical PSI branch. The coincidence channel is treated here as a phenomenological architecture proxy rather than a complete laboratory-grade fourth-order transfer model, so the present conclusions should be interpreted as benchmark-guided architectural evidence rather than as final experimental proof.

Figure 1 summarises the measured surface height benchmark across the focus-variation dataset. The hybrid branch achieves the lowest median height RMSE (558.6 nm) and wins on the most surfaces (24 of 59), followed closely by the direct quantum-like branch (710.8 nm, 23 wins). Classical PSI yields the highest median RMSE (1227.4 nm, 12 wins) under matched count budgets. Figure 2 shows the corresponding roughness-parameter comparison. The hybrid method is strongest for Sa (26 wins), while the direct quantum-like branch is selectively favourable for Sq and Sz, particularly Sz, where it dominates (37 of 59 wins).

The data support a regime-dependent conclusion rather than a single universal winner. For overall height fidelity and Sa recovery, the hybrid strategy is the strongest option. For envelope-dominated descriptors such as Sq and Sz, the direct quantum-like branch is selectively competitive. Classical PSI, although a well-established baseline, does not dominate any metric in this matched-budget benchmark, suggesting that its advantage lies in experimental maturity rather than in photon-statistical efficiency.

At the current stage of the project, the strongest conclusion is architectural. The hybrid coarse-to-fine strategy, where a coincidence-like channel resolves ambiguity and the classical branch preserves fine texture, outperforms both standalone methods across the benchmark. Ongoing work focuses on a more realistic coincidence model, stronger treatment of non-idealities, and experimental validation of the hybrid concept.

## Keywords

hybrid quantum-inspired profilometry; surface profilometry; hybrid reconstruction; coarse-to-fine reconstruction; phase-shifting interferometry

## Figure captions

Figure 1. Measured-surface benchmark summary across all focus-variation samples. Classical PSI and the hybrid branch remain the most texture-faithful estimators overall, whereas the direct quantum-like branch is only selectively competitive on smoother surfaces.

Figure 2. Comparison of reconstructed roughness parameters against the focus-variation reference values. The hybrid branch is strongest for Sa, whereas the direct quantum-like branch is selectively favourable for Sq and Sz.

## References

[1] Vorburger T V and Teague E C 1981 Optical techniques for on-line measurement of surface topography Precision Engineering 3 61-83

[2] McDonnell E M and Deck L L 2020 Solutions for environmentally robust interferometric optical testing Proceedings of SPIE - The International Society for Optical Engineering 11487

[3] Okamoto R and Tahara T 2021 Precision limit for simultaneous phase and transmittance estimation with phase-shifting interferometry Physical Review A 104

[4] Richards R K 2004 Quantum-entangled photon interferometry Interf. XII: Tech. Anal. 5531 17-23

[5] Rarity J G, Burnett J, Tapster P R and Paschotta R 1993 High-visibility two-photon interference in a single-mode-fibre interferometer EPL 22 95-100