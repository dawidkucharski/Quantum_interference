from __future__ import annotations

from typing import Optional

import numpy as np


def synthetic_wavelength(lambda1_m: float, lambda2_m: float) -> float:
    """Difference/synthetic wavelength: Lambda = (lambda1*lambda2)/|lambda1-lambda2|."""
    return (lambda1_m * lambda2_m) / abs(lambda1_m - lambda2_m)


def synthetic_wavelength_sum(lambda1_m: float, lambda2_m: float) -> float:
    """Sum-frequency effective wavelength: Lambda_sum = (lambda1*lambda2)/(lambda1+lambda2)."""
    if (lambda1_m + lambda2_m) == 0:
        raise ValueError("lambda1_m + lambda2_m must be non-zero")
    return (lambda1_m * lambda2_m) / (lambda1_m + lambda2_m)


def effective_wavelength(
    *,
    interferometer: str,
    lambda1_m: float,
    lambda2_m: float,
) -> float:
    """Map an interferometer model name to an effective wavelength.

    Models:
    - 'diff'  : difference/synthetic wavelength (long effective wavelength)
    - 'sum'   : sum-phase effective wavelength (shorter than either lambda)
    - 'noon2' : 2-photon phase sensitivity ~cos(2φ) => effective wavelength ~lambda/2

    Notes:
    - This is a phenomenological mapping intended for simulation benchmarking.
    - For 'noon2', we use lambda1 as the base wavelength.
    """

    name = interferometer.strip().lower().replace("-", "_")
    if name in {"diff", "synthetic", "synthetic_diff", "difference", "lambda_diff"}:
        return synthetic_wavelength(lambda1_m, lambda2_m)
    if name in {"sum", "synthetic_sum", "franson", "franson_sum", "lambda_sum"}:
        return synthetic_wavelength_sum(lambda1_m, lambda2_m)
    if name in {"noon2", "noon", "noon_n2", "debroglie2"}:
        if lambda1_m <= 0:
            raise ValueError("lambda1_m must be > 0")
        return 0.5 * lambda1_m
    if name in {"su11", "su_11", "su(1,1)", "su1_1"}:
        # SU(1,1) does not change the fringe period; it changes phase sensitivity/SNR.
        # We model this phenomenologically elsewhere (e.g., via effective visibility / rate model).
        if lambda1_m <= 0:
            raise ValueError("lambda1_m must be > 0")
        return float(lambda1_m)
    raise ValueError(
        "interferometer must be one of: diff, sum, noon2, su11 (got %r)" % interferometer
    )


def _visibility_effective(*, interferometer: str, visibility: float, su11_gain: float) -> float:
    name = interferometer.strip().lower().replace("-", "_")
    if name in {"su11", "su_11", "su(1,1)", "su1_1"}:
        if su11_gain < 0:
            raise ValueError("su11_gain must be >= 0")
        # Phenomenological: SU(1,1) can enhance phase sensitivity; we model it as improved fringe visibility.
        return float(np.clip(visibility * (1.0 + su11_gain), 0.0, 1.0))
    return float(np.clip(visibility, 0.0, 1.0))


def _apply_nonparalyzable_deadtime(mean_counts, *, gate_time_s: float, deadtime_s: float):
    if gate_time_s <= 0:
        raise ValueError("gate_time_s must be > 0")
    if deadtime_s < 0:
        raise ValueError("deadtime_s must be >= 0")

    arr = np.asarray(mean_counts, dtype=float)
    if deadtime_s == 0:
        return float(arr) if arr.ndim == 0 else arr

    rate = arr / float(gate_time_s)
    observed = (rate / (1.0 + rate * float(deadtime_s))) * float(gate_time_s)
    return float(observed) if observed.ndim == 0 else observed


def _effective_eta_with_deadtime(
    *,
    n_pairs: float,
    eta: float,
    dark_hz: float,
    gate_time_s: float,
    deadtime_s: float,
) -> float:
    if deadtime_s == 0:
        return float(eta)
    singles_rate = (float(n_pairs) * float(eta) / float(gate_time_s)) + float(dark_hz)
    return float(eta / (1.0 + singles_rate * float(deadtime_s)))


def _rate_model_mean_counts(
    p_int,
    *,
    n_pairs: float,
    gate_time_s: float,
    eta1: float,
    eta2: float,
    dark1_hz: float,
    dark2_hz: float,
    tau_c_s: float,
    deadtime1_s: float,
    deadtime2_s: float,
):
    if gate_time_s <= 0:
        raise ValueError("gate_time_s must be > 0")
    if tau_c_s < 0:
        raise ValueError("tau_c_s must be >= 0")
    if deadtime1_s < 0 or deadtime2_s < 0:
        raise ValueError("deadtime must be >= 0")

    p_arr = np.asarray(p_int, dtype=float)
    mu_s1_raw = float(n_pairs) * float(eta1) + float(dark1_hz) * float(gate_time_s)
    mu_s2_raw = float(n_pairs) * float(eta2) + float(dark2_hz) * float(gate_time_s)
    mu_s1 = _apply_nonparalyzable_deadtime(mu_s1_raw, gate_time_s=float(gate_time_s), deadtime_s=float(deadtime1_s))
    mu_s2 = _apply_nonparalyzable_deadtime(mu_s2_raw, gate_time_s=float(gate_time_s), deadtime_s=float(deadtime2_s))

    eta1_eff = _effective_eta_with_deadtime(
        n_pairs=float(n_pairs),
        eta=float(eta1),
        dark_hz=float(dark1_hz),
        gate_time_s=float(gate_time_s),
        deadtime_s=float(deadtime1_s),
    )
    eta2_eff = _effective_eta_with_deadtime(
        n_pairs=float(n_pairs),
        eta=float(eta2),
        dark_hz=float(dark2_hz),
        gate_time_s=float(gate_time_s),
        deadtime_s=float(deadtime2_s),
    )

    mu_true = float(n_pairs) * eta1_eff * eta2_eff * p_arr
    mu_acc = float(mu_s1) * float(mu_s2) * (float(tau_c_s) / float(gate_time_s))
    mu = np.clip(mu_true + mu_acc, 0.0, None)
    return float(mu) if np.ndim(mu) == 0 else mu


def _solve_pairs_for_target_mean(
    *,
    target_mean: float,
    mean_p_int: float,
    gate_time_s: float,
    tau_c_s: float,
    eta1: float,
    eta2: float,
    dark1_hz: float,
    dark2_hz: float,
    deadtime1_s: float,
    deadtime2_s: float,
) -> float:
    """Solve for pairs-per-gate so the mean coincidence counts match a target."""

    if target_mean <= 0:
        raise ValueError("target_mean must be > 0")
    if mean_p_int <= 0:
        raise ValueError("mean_p_int must be > 0")
    if gate_time_s <= 0:
        raise ValueError("gate_time_s must be > 0")
    if tau_c_s < 0:
        raise ValueError("tau_c_s must be >= 0")
    if not (0.0 <= eta1 <= 1.0 and 0.0 <= eta2 <= 1.0):
        raise ValueError("eta1 and eta2 must be in [0, 1]")
    if deadtime1_s < 0 or deadtime2_s < 0:
        raise ValueError("deadtime must be >= 0")

    def expected_mean(n_pairs: float) -> float:
        mu = _rate_model_mean_counts(
            float(mean_p_int),
            n_pairs=float(n_pairs),
            gate_time_s=float(gate_time_s),
            eta1=float(eta1),
            eta2=float(eta2),
            dark1_hz=float(dark1_hz),
            dark2_hz=float(dark2_hz),
            tau_c_s=float(tau_c_s),
            deadtime1_s=float(deadtime1_s),
            deadtime2_s=float(deadtime2_s),
        )
        return float(mu)

    lo = 0.0
    hi = max(float(target_mean) / max(float(eta1) * float(eta2) * float(mean_p_int), 1e-12), 1.0)
    hi = max(hi, float(target_mean), 1.0)

    f_hi = expected_mean(hi)
    n_expand = 0
    while f_hi < float(target_mean) and n_expand < 80:
        hi *= 2.0
        f_hi = expected_mean(hi)
        n_expand += 1

    if f_hi < float(target_mean):
        raise ValueError("Target mean counts cannot be reached with the requested detector settings")

    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if expected_mean(mid) >= float(target_mean):
            hi = mid
        else:
            lo = mid

    return float(hi)


def phase_from_height(height_m: np.ndarray, *, effective_wavelength_m: float) -> np.ndarray:
    # Keep the same reflection geometry factor for comparability
    return (4.0 * np.pi / effective_wavelength_m) * height_m


def simulate_coincidence(
    height_m: np.ndarray,
    *,
    lambda1_m: float = 810e-9,
    lambda2_m: float = 809e-9,
    visibility: float = 0.6,
    background: float = 1.0,
    amplitude: float = 1.0,
    phase_offset: float = 0.0,
    shot_noise: bool = True,
    pairs_per_pixel: float = 2e4,
    seed: Optional[int] = 1,
    interferometer: str = "diff",
    detector_model: str = "simple",
    # Rate-based coincidence model (used when detector_model='rates')
    gate_time_s: float = 1.0,
    pair_rate_hz: Optional[float] = None,
    eta1: float = 1.0,
    eta2: float = 1.0,
    dark1_hz: float = 0.0,
    dark2_hz: float = 0.0,
    tau_c_s: float = 1e-6,
    deadtime1_s: float = 0.0,
    deadtime2_s: float = 0.0,
    target_mean_counts_per_pixel: Optional[float] = None,
    su11_gain: float = 0.0,
) -> np.ndarray:
    """Simulate a coincidence-like observable using an effective (synthetic) wavelength.

    This is a *forward model proxy* for fourth-order interference in an entangled-photon
    interferometer. It is intentionally simple and meant to be replaced by the exact
    expression from Richards (2004) once extracted.

    Returns array of shape (H, W) with coincidence counts.
    """

    gen = np.random.default_rng(seed)
    lam_eff = effective_wavelength(interferometer=interferometer, lambda1_m=lambda1_m, lambda2_m=lambda2_m)
    phi = phase_from_height(height_m, effective_wavelength_m=lam_eff)

    vis_eff = _visibility_effective(interferometer=interferometer, visibility=visibility, su11_gain=su11_gain)

    det = detector_model.strip().lower().replace("-", "_")
    if det == "simple":
        if target_mean_counts_per_pixel is not None and target_mean_counts_per_pixel > 0:
            pairs_per_pixel = float(target_mean_counts_per_pixel)

        C = background + amplitude * (1.0 + vis_eff * np.cos(phi + phase_offset))
        C = np.clip(C, 0.0, None)

        if shot_noise:
            reference_level = background + amplitude
            if reference_level <= 0:
                raise ValueError("background + amplitude must be > 0")
            lam = C * (pairs_per_pixel / reference_level)
            C = gen.poisson(lam=lam).astype(float)
        return C

    if det == "rates":
        if gate_time_s <= 0:
            raise ValueError("gate_time_s must be > 0")
        if tau_c_s < 0:
            raise ValueError("tau_c_s must be >= 0")
        if not (0.0 <= eta1 <= 1.0 and 0.0 <= eta2 <= 1.0):
            raise ValueError("eta1 and eta2 must be in [0, 1]")
        if deadtime1_s < 0 or deadtime2_s < 0:
            raise ValueError("deadtime must be >= 0")

        # If pair_rate_hz is omitted, treat pairs_per_pixel as pairs per gate.
        n_pairs = float(pair_rate_hz) * gate_time_s if pair_rate_hz is not None else float(pairs_per_pixel)
        # Interference probability in [0, 1]
        p_int = 0.5 * (1.0 + vis_eff * np.cos(phi + phase_offset))
        p_int = np.clip(p_int, 0.0, 1.0)

        if target_mean_counts_per_pixel is not None and target_mean_counts_per_pixel > 0:
            mean_p_int = float(np.mean(p_int))
            n_pairs = _solve_pairs_for_target_mean(
                target_mean=float(target_mean_counts_per_pixel),
                mean_p_int=mean_p_int,
                gate_time_s=float(gate_time_s),
                tau_c_s=float(tau_c_s),
                eta1=float(eta1),
                eta2=float(eta2),
                dark1_hz=float(dark1_hz),
                dark2_hz=float(dark2_hz),
                deadtime1_s=float(deadtime1_s),
                deadtime2_s=float(deadtime2_s),
            )

        mu = _rate_model_mean_counts(
            p_int,
            n_pairs=float(n_pairs),
            gate_time_s=float(gate_time_s),
            eta1=float(eta1),
            eta2=float(eta2),
            dark1_hz=float(dark1_hz),
            dark2_hz=float(dark2_hz),
            tau_c_s=float(tau_c_s),
            deadtime1_s=float(deadtime1_s),
            deadtime2_s=float(deadtime2_s),
        )
        if shot_noise:
            return gen.poisson(lam=mu).astype(float)
        return mu.astype(float)

    raise ValueError("detector_model must be 'simple' or 'rates'")


def simulate_coincidence_psi4(
    height_m: np.ndarray,
    *,
    lambda1_m: float = 810e-9,
    lambda2_m: float = 809e-9,
    visibility: float = 0.6,
    background: float = 1.0,
    amplitude: float = 1.0,
    phase_offset: float = 0.0,
    phase_steps: tuple[float, float, float, float] = (0.0, 0.5 * np.pi, np.pi, 1.5 * np.pi),
    phase_step_error_sigma_rad: float = 0.0,
    background_drift_frac: float = 0.0,
    amplitude_drift_frac: float = 0.0,
    shot_noise: bool = True,
    pairs_per_pixel: float = 2e4,
    seed: Optional[int] = 1,
    interferometer: str = "diff",
    detector_model: str = "simple",
    # Rate-based coincidence model (used when detector_model='rates')
    gate_time_s: float = 1.0,
    pair_rate_hz: Optional[float] = None,
    eta1: float = 1.0,
    eta2: float = 1.0,
    dark1_hz: float = 0.0,
    dark2_hz: float = 0.0,
    tau_c_s: float = 1e-6,
    deadtime1_s: float = 0.0,
    deadtime2_s: float = 0.0,
    target_mean_counts_per_pixel: Optional[float] = None,
    su11_gain: float = 0.0,
) -> np.ndarray:
    """Simulate a 4-step coincidence measurement by stepping reference phase.

    This mirrors classical 4-step PSI, but using a coincidence-like observable and an
    effective (synthetic/difference) wavelength.

    Returns array of shape (4, H, W).
    """

    gen = np.random.default_rng(seed)
    lam_eff = effective_wavelength(interferometer=interferometer, lambda1_m=lambda1_m, lambda2_m=lambda2_m)
    phi = phase_from_height(height_m, effective_wavelength_m=lam_eff)

    vis_eff = _visibility_effective(interferometer=interferometer, visibility=visibility, su11_gain=su11_gain)

    if phase_step_error_sigma_rad < 0:
        raise ValueError("phase_step_error_sigma_rad must be >= 0")
    if background_drift_frac < 0:
        raise ValueError("background_drift_frac must be >= 0")
    if amplitude_drift_frac < 0:
        raise ValueError("amplitude_drift_frac must be >= 0")

    reference_level = background + amplitude
    if reference_level <= 0:
        raise ValueError("background + amplitude must be > 0")

    det = detector_model.strip().lower().replace("-", "_")
    if det not in {"simple", "rates"}:
        raise ValueError("detector_model must be 'simple' or 'rates'")
    n_pairs = float(pairs_per_pixel)
    if det == "rates":
        if gate_time_s <= 0:
            raise ValueError("gate_time_s must be > 0")
        if tau_c_s < 0:
            raise ValueError("tau_c_s must be >= 0")
        if not (0.0 <= eta1 <= 1.0 and 0.0 <= eta2 <= 1.0):
            raise ValueError("eta1 and eta2 must be in [0, 1]")
        if deadtime1_s < 0 or deadtime2_s < 0:
            raise ValueError("deadtime must be >= 0")
        n_pairs = float(pair_rate_hz) * gate_time_s if pair_rate_hz is not None else float(pairs_per_pixel)

        if target_mean_counts_per_pixel is not None and target_mean_counts_per_pixel > 0:
            # Estimate mean p_int over both pixels and phase steps (for typical 0, pi/2, pi, 3pi/2 this reduces to ~0.5).
            p_means = []
            for d in phase_steps:
                p_int0 = 0.5 * (1.0 + vis_eff * np.cos(phi + phase_offset + d))
                p_means.append(float(np.mean(np.clip(p_int0, 0.0, 1.0))))
            mean_p_int = float(np.mean(p_means))
            n_pairs = _solve_pairs_for_target_mean(
                target_mean=float(target_mean_counts_per_pixel),
                mean_p_int=mean_p_int,
                gate_time_s=float(gate_time_s),
                tau_c_s=float(tau_c_s),
                eta1=float(eta1),
                eta2=float(eta2),
                dark1_hz=float(dark1_hz),
                dark2_hz=float(dark2_hz),
                deadtime1_s=float(deadtime1_s),
                deadtime2_s=float(deadtime2_s),
            )

    frames: list[np.ndarray] = []
    for d in phase_steps:
        bg_i = background * (1.0 + gen.normal(0.0, background_drift_frac))
        amp_i = amplitude * (1.0 + gen.normal(0.0, amplitude_drift_frac))
        d_eff = d + gen.normal(0.0, phase_step_error_sigma_rad)

        if det == "simple":
            if target_mean_counts_per_pixel is not None and target_mean_counts_per_pixel > 0:
                pairs_per_pixel = float(target_mean_counts_per_pixel)

            C = bg_i + amp_i * (1.0 + vis_eff * np.cos(phi + phase_offset + d_eff))
            C = np.clip(C, 0.0, None)
            if shot_noise:
                lam = C * (pairs_per_pixel / reference_level)
                C = gen.poisson(lam=lam).astype(float)
        else:
            assert det == "rates"
            # Rate-based coincidence model; bg_i/amp_i perturb the visibility-free offset in a crude way.
            p_int = 0.5 * (1.0 + vis_eff * np.cos(phi + phase_offset + d_eff))
            p_int = np.clip(p_int, 0.0, 1.0)
            mu = _rate_model_mean_counts(
                p_int,
                n_pairs=float(n_pairs),
                gate_time_s=float(gate_time_s),
                eta1=float(eta1),
                eta2=float(eta2),
                dark1_hz=float(dark1_hz),
                dark2_hz=float(dark2_hz),
                tau_c_s=float(tau_c_s),
                deadtime1_s=float(deadtime1_s),
                deadtime2_s=float(deadtime2_s),
            )
            # Keep drift knobs meaningful by modulating overall rate
            mu = np.clip(mu * (bg_i / background) * (amp_i / amplitude), 0.0, None)
            C = gen.poisson(lam=mu).astype(float) if shot_noise else mu.astype(float)
        frames.append(C)

    return np.stack(frames, axis=0)
