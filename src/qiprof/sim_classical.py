from __future__ import annotations

from typing import Optional

import numpy as np


def phase_from_height(height_m: np.ndarray, *, wavelength_m: float) -> np.ndarray:
    """Round-trip reflection phase: phi = 4*pi*h/lambda."""
    return (4.0 * np.pi / wavelength_m) * height_m


def simulate_psi4(
    height_m: np.ndarray,
    *,
    wavelength_m: float = 532e-9,
    visibility: float = 0.9,
    background: float = 1.0,
    amplitude: float = 1.0,
    phase_steps: tuple[float, float, float, float] = (0.0, 0.5 * np.pi, np.pi, 1.5 * np.pi),
    phase_step_error_sigma_rad: float = 0.0,
    background_drift_frac: float = 0.0,
    amplitude_drift_frac: float = 0.0,
    shot_noise: bool = True,
    photons_per_pixel: float = 5e4,
    seed: Optional[int] = 0,
) -> np.ndarray:
    """Simulate 4-step phase-shifting interferometry intensities.

    Returns array of shape (4, H, W).
    """

    gen = np.random.default_rng(seed)
    phi = phase_from_height(height_m, wavelength_m=wavelength_m)

    if phase_step_error_sigma_rad < 0:
        raise ValueError("phase_step_error_sigma_rad must be >= 0")
    if background_drift_frac < 0:
        raise ValueError("background_drift_frac must be >= 0")
    if amplitude_drift_frac < 0:
        raise ValueError("amplitude_drift_frac must be >= 0")

    reference_level = background + amplitude
    if reference_level <= 0:
        raise ValueError("background + amplitude must be > 0")

    I = []
    for d in phase_steps:
        bg_i = background * (1.0 + gen.normal(0.0, background_drift_frac))
        amp_i = amplitude * (1.0 + gen.normal(0.0, amplitude_drift_frac))
        d_eff = d + gen.normal(0.0, phase_step_error_sigma_rad)

        # Standard interference model: I = B + A*(1 + V*cos(phi + d))
        Ii = bg_i + amp_i * (1.0 + visibility * np.cos(phi + d_eff))
        Ii = np.clip(Ii, 0.0, None)

        if shot_noise:
            # Poisson shot noise on expected photon counts
            lam = Ii * (photons_per_pixel / reference_level)
            counts = gen.poisson(lam=lam)
            Ii = counts.astype(float)

        I.append(Ii)

    return np.stack(I, axis=0)
