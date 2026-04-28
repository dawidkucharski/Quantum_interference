# Photonics Cover Letter Draft

28 April 2026

Editor-in-Chief
Photonics

Dear Editor,

I am pleased to submit the manuscript titled "Simulation benchmark of hybrid coarse-to-fine interferometric profilometry using coincidence-proxy priors on measured rough surfaces" for consideration in Photonics.

This manuscript presents a reproducible simulation benchmark for photonic-instrumentation architecture selection in rough-surface profilometry. It compares classical phase-shifting interferometry, direct coincidence-proxy channels, and hybrid coarse-to-fine reconstruction under matched detected-count assumptions using 59 focus-variation (FV) surface topographies exported as Mountains/DigitalSurf `.sur` files as measured geometric priors. The main result is an architecture-level height-fidelity finding: within the present proxy hierarchy, coincidence-derived information is most valuable as a coarse ambiguity-resolving prior inside a hybrid estimator when benchmark-grid height RMSE is the primary endpoint.

The manuscript should fit Photonics for three reasons.

1. It addresses photonic interferometric measurement architecture rather than only numerical post-processing. The paper compares classical and coincidence-inspired sensing routes at the level of the full reconstruction pipeline and endpoint-level benchmark behaviour.
2. It is benchmarked on measured engineering surfaces rather than only idealized synthetic objects. The measured branch uses 59 Mountains/DigitalSurf `.sur` topographies spanning six material groups and ten treatment classes.
3. It includes critical controls that raise the comparator bar instead of protecting the main claim: matched-bandwidth roughness evaluation, approximate Gaussian roughness-filter sensitivity, classical two-colour and classical-frontier controls, material- and treatment-holdout stability checks, and a stronger rate-based coincidence model with detector-side non-idealities.

The submission is best read as a rigorous screening study for future photonic instrumentation. It identifies which architectural role remains defensible for a coincidence-derived channel after realistic texture endpoints and stronger classical controls are imposed, while keeping the scope aligned with the available evidence.

The main measured-surface result is that the hybrid branch yields the lowest fixed-workflow median height RMSE on the benchmark surfaces, remains below an optimistic classical-frontier oracle, and preserves the same ordering under a stronger rate-based coincidence control with detector-side non-idealities. Roughness endpoints are reported as an endpoint-specific boundary map: matched-bandwidth $S_a$ and $S_q$ favour hybrid within the primary branches, while the surviving direct long-wavelength $S_z$ behaviour is treatment-dependent and also reproduced by the classical two-colour control.

The manuscript is original, has not been published previously, and is not under consideration elsewhere. The author declares no conflicts of interest. The work was supported by the Polish Ministry of Science under the programme Polish Metrology II, project no. PM-II/SP/0090/2024/02. A public development repository is provided, with the Q1 submission snapshot fixed by GitHub release `submission-2026-04-28-q1` and archived on Zenodo with version DOI `10.5281/zenodo.19852223` and concept DOI `10.5281/zenodo.19844594`. A companion release archive provides derived 256 x 256 benchmark-grid surfaces, public CSV summaries, generated table sources, exact regeneration commands, and a SHA-256 checksum. The manuscript also identifies a reduced experimental-validation subset and protocol for the next laboratory stage.

Thank you for your consideration.

Sincerely,

Dawid Kucharski
Division of Metrology and Measurement Systems, Institute of Mechanical Technology, Faculty of Mechanical Engineering, Poznan University of Technology, 60-965 Poznan, Poland
dawid.kucharski@put.poznan.pl