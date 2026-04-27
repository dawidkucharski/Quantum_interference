from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Optional

import numpy as np


@dataclass(frozen=True)
class Roughness:
    Sa: float
    Sq: float
    Sz: float


def detrend_plane(h: np.ndarray, *, valid_mask: Optional[np.ndarray] = None) -> np.ndarray:
    """Remove best-fit plane from a height map.

    If `h` contains NaNs/inf, the plane is fit using only finite pixels.
    """

    return detrend_plane_masked(h, valid_mask=valid_mask)


def detrend_plane_masked(h: np.ndarray, *, valid_mask: Optional[np.ndarray]) -> np.ndarray:
    """Remove best-fit plane using an explicit validity mask.

    Parameters
    - valid_mask: (H, W) boolean mask where True indicates valid pixels.
      If None, valid pixels are inferred from `np.isfinite(h)`.
    """

    if h.ndim != 2:
        raise ValueError("h must be 2D")

    ny, nx = h.shape
    finite = np.isfinite(h)
    if valid_mask is None:
        mask = finite
    else:
        if valid_mask.shape != h.shape:
            raise ValueError("valid_mask must have the same shape as h")
        mask = valid_mask & finite

    # Need at least 3 points to fit a plane.
    if int(np.sum(mask)) < 3:
        return h.copy()

    ys, xs = np.nonzero(mask)
    A = np.stack([xs.astype(float), ys.astype(float), np.ones(xs.size, dtype=float)], axis=1)
    b = h[mask].astype(float)
    coeff, *_ = np.linalg.lstsq(A, b, rcond=None)

    X, Y = np.meshgrid(np.arange(nx, dtype=float), np.arange(ny, dtype=float))
    plane = coeff[0] * X + coeff[1] * Y + coeff[2]
    return h - plane


def roughness_metrics(h_m: np.ndarray, *, valid_mask: Optional[np.ndarray] = None) -> Roughness:
    """Compute basic areal roughness metrics from ISO-like definitions.

    Invalid pixels (NaN/inf or masked out via `valid_mask`) are ignored.
    """

    h_dt = detrend_plane_masked(h_m, valid_mask=valid_mask)
    finite = np.isfinite(h_dt)
    if valid_mask is None:
        mask = finite
    else:
        if valid_mask.shape != h_dt.shape:
            raise ValueError("valid_mask must have the same shape as h_m")
        mask = valid_mask & finite

    vals = h_dt[mask]
    if vals.size == 0:
        return Roughness(Sa=float("nan"), Sq=float("nan"), Sz=float("nan"))

    Sa = float(np.mean(np.abs(vals)))
    Sq = float(np.sqrt(np.mean(vals**2)))
    Sz = float(np.max(vals) - np.min(vals))
    return Roughness(Sa=Sa, Sq=Sq, Sz=Sz)


def psd2d(h_m: np.ndarray, *, dx: float, dy: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Compute 2D PSD estimate (periodogram). Returns fx, fy, PSD."""

    h = detrend_plane_masked(h_m, valid_mask=None)
    # FFT requires finite values; fill missing values with 0 after detrending.
    if not np.isfinite(h).all():
        h = np.nan_to_num(h, nan=0.0, posinf=0.0, neginf=0.0)
    ny, nx = h.shape

    H = np.fft.fft2(h)
    psd = (np.abs(H) ** 2) * (dx * dy) / (nx * ny)

    fx = np.fft.fftshift(np.fft.fftfreq(nx, d=dx))
    fy = np.fft.fftshift(np.fft.fftfreq(ny, d=dy))
    return fx, fy, np.fft.fftshift(psd)


def radial_psd(
    fx: np.ndarray,
    fy: np.ndarray,
    psd: np.ndarray,
    *,
    nbins: int = 200,
    fmin: Optional[float] = None,
    fmax: Optional[float] = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Compute a simple radial average of a 2D PSD.

    Expects `fx`, `fy`, and `psd` as returned by `psd2d` (i.e. already fftshift'ed).
    Returns (fr, P(fr)) where fr are bin centers.
    """

    if psd.ndim != 2:
        raise ValueError("psd must be 2D")
    if fx.ndim != 1 or fy.ndim != 1:
        raise ValueError("fx and fy must be 1D")
    if psd.shape != (fy.size, fx.size):
        raise ValueError("psd shape must match (len(fy), len(fx))")
    if nbins < 5:
        raise ValueError("nbins must be >= 5")

    FX, FY = np.meshgrid(fx, fy)
    fr = np.sqrt(FX**2 + FY**2).ravel()
    p = psd.ravel()

    if fmin is None:
        fmin = float(np.min(fr))
    if fmax is None:
        fmax = float(np.max(fr))
    if not (0.0 <= fmin < fmax):
        raise ValueError("Require 0 <= fmin < fmax")

    edges = np.linspace(fmin, fmax, nbins + 1)
    idx = np.digitize(fr, edges) - 1
    valid = (idx >= 0) & (idx < nbins) & np.isfinite(p)
    idx = idx[valid]
    p = p[valid]

    sums = np.bincount(idx, weights=p, minlength=nbins)
    counts = np.bincount(idx, minlength=nbins)
    with np.errstate(invalid="ignore", divide="ignore"):
        prof = sums / counts

    centers = 0.5 * (edges[:-1] + edges[1:])
    return centers, prof


def roughness_errors(est: Roughness, true: Roughness) -> dict[str, float]:
    """Return bias (est-true) for Sa, Sq, Sz."""

    return {
        "bias_Sa": float(est.Sa - true.Sa),
        "bias_Sq": float(est.Sq - true.Sq),
        "bias_Sz": float(est.Sz - true.Sz),
    }


def write_metrics_json(path: str, **items) -> None:
    def _conv(v):
        if hasattr(v, "__dataclass_fields__"):
            return asdict(v)
        if isinstance(v, (np.floating, np.integer)):
            return v.item()
        return v

    serializable = {k: _conv(v) for k, v in items.items()}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(serializable, f, indent=2)
