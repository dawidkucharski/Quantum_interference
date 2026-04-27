# Literature map (from scopus.bib + Scopus AI report)

This is a working map of the bibliography in [scopus.bib](../scopus.bib) as it relates to this project’s *classical vs quantum-like surface texture metrology benchmarking*.

## Cluster 1 — Classical interferometry robustness & algorithms
- Ri et al. (2020) — spatiotemporal phase-shifting method for robust phase analysis under background/amplitude fluctuations and phase-step errors.
- Kim et al. (2026) — deep-learning-based robust aberration sensing / phase extraction with fewer frames.

**Relevance to this repo:** motivates our stress-tests for phase-step errors and intensity drift, and sets a strong “classical baseline” expectation.

## Cluster 2 — Harsh / industrial environments
- Albertazzi et al. (2018) — speckle interferometry design considerations in harsh environments (vibration, thermal/air instabilities).
- Tausendfreund et al. (2020) — in-process displacement measurements; uncertainty accumulation and averaging.

**Relevance:** motivates phase noise and drift models and encourages reporting uncertainty vs averaging/replicates.

## Cluster 3 — Two-color / synthetic-wavelength ideas (classical and quantum-inspired)
- Zhang et al. (2022) — two-color interferometry for refractive index self-correction in distance measurement.
- Kotsiuba et al. (2018) — two-wavelength holograms for relief mapping.

**Relevance:** provides classical context for “difference wavelength” and why synthetic wavelength helps avoid fringe counting.

## Cluster 4 — Quantum-enhanced metrology concepts
- Jha et al. (2011) — entangled photons for supersensitive angular displacement.
- Sharma et al. (2022) — displacement measurements using position-entangled photon pairs (low-light regimes).

**Relevance:** supports the low-light motivation and the use of coincidence-style observables.

## Cluster 5 — Quantum photonics platforms (enablers)
- Labbé et al. (2025) — integrated quantum photonics (thin-film LiNbO3).

**Relevance:** points toward integrated/hybrid experimental realizations after the simulation study.

## Key gap (from Scopus AI PDF, 03 Feb 2026)
- Direct, controlled benchmarking between classical surface metrology and entangled-photon/fourth-order approaches is rare.

**This repo’s purpose:** fill that gap with a unified simulation/reconstruction/metrics pipeline and publishable benchmark sweeps.
