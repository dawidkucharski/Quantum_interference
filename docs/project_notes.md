# Project notes

## Research framing
We want a simulation paper/project that demonstrates a *new* way to apply interferometry for surface texture measurements by contrasting:

- Classical 2nd-order interferometry (intensity, PSI reconstruction)
- Entangled-photon / 4th-order interferometry (coincidence observable)

Key outputs are not only height-map RMSE but texture parameters: Sa, Sq, Sz, and PSD.

## Current implementation status
The current quantum branch is a deliberately simple proxy:

- Coincidence-like observable: `C = B + A(1 + V cos(phi_eff))`
- Effective wavelength is the synthetic/difference wavelength: `Lambda = (λ1 λ2)/|λ1-λ2|`

This captures the main simulation argument: longer effective period -> larger unambiguous range, while still being sensitive to nm-scale variations.

## What to replace next
Once we extract the exact formula from Richards (2004):
- Replace the proxy `simulate_coincidence` with the paper’s 4th-order interference expression.
- Replace the `arccos` inversion with an estimator consistent with the measurement protocol (likely scanning delay or phase steps in the coincidence channel).

## Noise models to add
- Background coincidences / accidental coincidences
- Visibility loss vs roughness and numerical aperture
- Detector deadtime and saturation
- Correlated noise in scanning delay
