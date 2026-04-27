from __future__ import annotations

import numpy as np


def fit_sinusoid_lsq_coeff(frames: np.ndarray, *, phase_steps_rad: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Fit the linear sinusoid model per pixel via least squares.

    Model:
      y_k = O + a*cos(d_k) + b*sin(d_k)

    Returns:
      (O, a, b) arrays of shape (H, W).

    Notes:
    - This is the same model used by `reconstruct_phase_lsq` in `qiprof.reconstruct`.
    - For ideal PSI with I = B + A*(1 + V*cos(phi + d)), the coefficients relate to
      R = A*V and phase via: a = R*cos(phi), b = -R*sin(phi).
    """

    if frames.ndim != 3:
        raise ValueError("Expected frames with shape (N, H, W)")
    n = frames.shape[0]
    if phase_steps_rad.shape != (n,):
        raise ValueError("phase_steps_rad must have shape (N,)")
    if n < 3:
        raise ValueError("Need at least 3 frames")

    d = phase_steps_rad.astype(float)
    X = np.stack([np.ones(n), np.cos(d), np.sin(d)], axis=1)  # (N, 3)
    pinv = np.linalg.pinv(X)  # (3, N)

    y = frames.reshape(n, -1)  # (N, P)
    coeff = pinv @ y  # (3, P)

    O = coeff[0].reshape(frames.shape[1:])
    a = coeff[1].reshape(frames.shape[1:])
    b = coeff[2].reshape(frames.shape[1:])
    return O, a, b


def fisher_information_phi_poisson(
    O: np.ndarray,
    a: np.ndarray,
    b: np.ndarray,
    *,
    phase_steps_rad: np.ndarray,
    eps: float = 1e-12,
) -> np.ndarray:
    """Per-pixel Fisher information for phase under a Poisson count model.

    Assumes the expected mean per step is:
      mu_k = O + R*cos(phi + d_k)
    with R = sqrt(a^2 + b^2) and phi = atan2(-b, a).

    For independent Poisson counts, Fisher information is:
      I(phi) = sum_k ( (d mu_k / d phi)^2 / mu_k )

    Returns:
      I_phi array of shape (H, W).

    Caution:
    - This is a lower bound under an *idealized* model.
    - It does not account for phase-step jitter unless `phase_steps_rad` matches the
      actual effective steps used during simulation/measurement.
    """

    if O.shape != a.shape or O.shape != b.shape:
        raise ValueError("O, a, b must have the same shape")
    if phase_steps_rad.ndim != 1:
        raise ValueError("phase_steps_rad must be 1D")

    R = np.sqrt(a * a + b * b)
    phi = np.arctan2(-b, a)

    I = np.zeros_like(O, dtype=float)
    for d in phase_steps_rad.astype(float):
        mu = O + R * np.cos(phi + d)
        mu = np.clip(mu, eps, None)
        dmu = -R * np.sin(phi + d)
        I += (dmu * dmu) / mu

    I = np.clip(I, 0.0, None)
    return I


def crlb_sigma_phi_from_frames(
    frames: np.ndarray,
    *,
    phase_steps_rad: np.ndarray,
    eps: float = 1e-12,
) -> np.ndarray:
    """Per-pixel CRLB (1-sigma) for phase from PSI-like frames.

    Returns sigma_phi (rad) array of shape (H, W), where sigma_phi = sqrt(1/I_phi).

    Pixels with near-zero Fisher information get sigma=inf.
    """

    O, a, b = fit_sinusoid_lsq_coeff(frames, phase_steps_rad=phase_steps_rad)
    I = fisher_information_phi_poisson(O, a, b, phase_steps_rad=phase_steps_rad, eps=eps)

    with np.errstate(divide="ignore", invalid="ignore"):
        sigma = np.sqrt(1.0 / I)
    sigma = np.where(np.isfinite(sigma), sigma, np.inf)
    return sigma


def summarize_sigma(sigma: np.ndarray) -> dict[str, float]:
    """Robust summary of a sigma map."""

    s = sigma[np.isfinite(sigma)]
    if s.size == 0:
        return {
            "mean": float("nan"),
            "median": float("nan"),
            "p90": float("nan"),
        }
    return {
        "mean": float(np.mean(s)),
        "median": float(np.median(s)),
        "p90": float(np.quantile(s, 0.9)),
    }
