from __future__ import annotations

import numpy as np
from scipy.fft import dctn, idctn
from scipy.ndimage import gaussian_filter


def reconstruct_psi4(I4: np.ndarray) -> np.ndarray:
    """4-step PSI phase estimate.

    Expects I4 shape (4, H, W) for phase steps (0, pi/2, pi, 3pi/2).
    Returns wrapped phase in (-pi, pi].
    """

    if I4.shape[0] != 4:
        raise ValueError("Expected 4 frames")

    I1, I2, I3, I4_ = I4
    phi = np.arctan2((I4_ - I2), (I1 - I3))
    return phi


def normalize_frames_mean(frames: np.ndarray) -> np.ndarray:
    """Normalize each frame by its mean intensity/count.

    This is a simple mitigation for per-frame background/amplitude drift.
    It is not a substitute for a full spatiotemporal PSI model, but it helps
    stabilize least-squares phase extraction under realistic non-idealities.

    Expects frames shape (N, H, W). Returns normalized frames.
    """

    if frames.ndim != 3:
        raise ValueError("Expected frames with shape (N, H, W)")

    means = frames.mean(axis=(1, 2), keepdims=True)
    target = float(np.mean(means))
    means = np.where(means <= 0, 1.0, means)
    return frames * (target / means)


def reconstruct_phase_lsq(frames: np.ndarray, *, phase_steps_rad: np.ndarray) -> np.ndarray:
    """Least-squares phase estimate for arbitrary phase steps.

    Model per pixel:
      I_k = O + a*cos(d_k) + b*sin(d_k)
    where O = (background + amplitude) and (a,b) encode amplitude*visibility and phase.

    Then phase is: phi = atan2(-b, a)

    This generalizes 4-step PSI and supports non-ideal step values.
    """

    if frames.ndim != 3:
        raise ValueError("Expected frames with shape (N, H, W)")
    n = frames.shape[0]
    if phase_steps_rad.shape != (n,):
        raise ValueError("phase_steps_rad must have shape (N,)")
    if n < 3:
        raise ValueError("Need at least 3 frames")

    # Design matrix: [1, cos(d_k), sin(d_k)]
    d = phase_steps_rad.astype(float)
    X = np.stack([np.ones(n), np.cos(d), np.sin(d)], axis=1)  # (N, 3)

    # Compute pseudo-inverse once: (3, N)
    pinv = np.linalg.pinv(X)

    # Flatten spatial dims and solve for [O, a, b] per pixel
    y = frames.reshape(n, -1)  # (N, P)
    coeff = pinv @ y  # (3, P)
    a = coeff[1].reshape(frames.shape[1:])
    b = coeff[2].reshape(frames.shape[1:])

    phi = np.arctan2(-b, a)
    return phi


def unwrap_2d_simple(wrapped: np.ndarray) -> np.ndarray:
    """Simple 2D unwrap: unwrap rows then columns.

    This is a robust baseline; we can replace with quality-guided unwrapping later.
    """

    unwrapped = np.unwrap(wrapped, axis=1)
    unwrapped = np.unwrap(unwrapped, axis=0)
    return unwrapped


def _wrap_to_pi(values: np.ndarray) -> np.ndarray:
    """Wrap phase differences to the principal interval (-pi, pi]."""

    return (values + np.pi) % (2.0 * np.pi) - np.pi


def unwrap_2d_least_squares(wrapped: np.ndarray) -> np.ndarray:
    """Least-squares 2D phase unwrap via a Poisson solve.

    The method solves for the phase whose discrete gradients best match the
    wrapped phase differences in the least-squares sense under Neumann-like
    boundary conditions. It is more global than the separable row/column
    baseline and is useful as a control when direct branches may be sensitive
    to unwrap path choices.
    """

    if wrapped.ndim != 2:
        raise ValueError("Expected wrapped phase with shape (H, W)")
    if not np.all(np.isfinite(wrapped)):
        raise ValueError("wrapped phase must be finite")

    dx = _wrap_to_pi(wrapped[:, 1:] - wrapped[:, :-1])
    dy = _wrap_to_pi(wrapped[1:, :] - wrapped[:-1, :])

    rho = np.zeros_like(wrapped, dtype=float)
    rho[:, :-1] += dx
    rho[:, 1:] -= dx
    rho[:-1, :] += dy
    rho[1:, :] -= dy

    ny, nx = wrapped.shape
    yy = np.arange(ny, dtype=float)[:, None]
    xx = np.arange(nx, dtype=float)[None, :]
    denom = 2.0 * (np.cos(np.pi * yy / ny) + np.cos(np.pi * xx / nx) - 2.0)

    rhs = dctn(rho, type=2, norm="ortho")
    sol = np.zeros_like(rhs)
    nonzero = denom != 0.0
    sol[nonzero] = rhs[nonzero] / denom[nonzero]
    unwrapped = idctn(sol, type=2, norm="ortho")

    # The least-squares solution is defined up to a constant 2pi offset.
    cy = ny // 2
    cx = nx // 2
    unwrapped += 2.0 * np.pi * np.rint((wrapped[cy, cx] - unwrapped[cy, cx]) / (2.0 * np.pi))
    return unwrapped


def unwrap_phase_2d(wrapped: np.ndarray, *, method: str = "simple") -> np.ndarray:
    """Dispatch helper for the available 2D unwrap backends."""

    if method == "simple":
        return unwrap_2d_simple(wrapped)
    if method == "least_squares":
        return unwrap_2d_least_squares(wrapped)
    raise ValueError(f"Unknown unwrap method: {method}")


def height_from_phase(phase_rad: np.ndarray, *, wavelength_m: float) -> np.ndarray:
    """Convert phase to height for reflective geometry: h = (lambda/4pi) * phi."""
    return (wavelength_m / (4.0 * np.pi)) * phase_rad


def unwrap_height_with_coarse(
    phase_wrapped_short_rad: np.ndarray,
    *,
    coarse_height_m: np.ndarray,
    wavelength_short_m: float,
    coarse_smooth_sigma_px: float = 0.0,
) -> np.ndarray:
    """Unwrap short-wavelength height using a coarse absolute height prior.

    For reflective interferometry, adding 2π to phase corresponds to adding λ/2 in height.
    We choose the integer fringe order per pixel so the resulting height is closest to the
    provided coarse height map.

    This implements a standard two-wavelength / coarse-to-fine unwrapping strategy.
    """

    if phase_wrapped_short_rad.shape != coarse_height_m.shape:
        raise ValueError("phase_wrapped_short_rad and coarse_height_m must have same shape")
    if wavelength_short_m <= 0:
        raise ValueError("wavelength_short_m must be > 0")

    if coarse_smooth_sigma_px < 0:
        raise ValueError("coarse_smooth_sigma_px must be >= 0")

    coarse = coarse_height_m
    if coarse_smooth_sigma_px > 0:
        coarse = gaussian_filter(coarse, sigma=float(coarse_smooth_sigma_px))

    h0 = height_from_phase(phase_wrapped_short_rad, wavelength_m=wavelength_short_m)
    h_step = wavelength_short_m / 2.0
    k = np.rint((coarse - h0) / h_step)
    return h0 + k * h_step


def reconstruct_from_coincidence(
    C: np.ndarray,
    *,
    visibility: float,
    background: float,
    amplitude: float,
    effective_wavelength_m: float,
    phase_offset: float = 0.0,
) -> np.ndarray:
    """Invert coincidence proxy model: C = B + A*(1 + V*cos(phi+off)).

    Returns wrapped phase (principal value) using arccos.
    Note: arccos loses sign; we keep a wrapped estimate; further steps can disambiguate.
    """

    denom = (amplitude * visibility)
    if denom <= 0:
        raise ValueError("amplitude*visibility must be > 0")

    x = (C - background - amplitude) / denom
    x = np.clip(x, -1.0, 1.0)
    phi = np.arccos(x) - phase_offset
    # Wrap to (-pi, pi]
    phi = (phi + np.pi) % (2.0 * np.pi) - np.pi
    return phi
