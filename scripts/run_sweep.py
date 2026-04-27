from __future__ import annotations

import argparse
import csv
from pathlib import Path
import sys

import numpy as np

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "src"))

from qiprof.metrics import detrend_plane, roughness_errors, roughness_metrics, write_metrics_json
from qiprof.plot_style import apply_publication_style
from qiprof.reconstruct import (
    height_from_phase,
    normalize_frames_mean,
    reconstruct_phase_lsq,
    reconstruct_psi4,
    unwrap_2d_simple,
    unwrap_height_with_coarse,
)
from qiprof.sim_classical import simulate_psi4
from qiprof.sim_quantum import effective_wavelength, simulate_coincidence_psi4
from qiprof.surfaces import Surface, load_surface_sur, make_surface
from qiprof.uncertainty import crlb_sigma_phi_from_frames, summarize_sigma
from qiprof.viz import save_surface_3d, save_surface_height_map


def _coherence_factor(*, rms_m: float, wavelength_m: float, model: str, incidence_cos: float = 1.0) -> float:
    """Return a scalar coherence/contrast factor in [0, 1] for a rough reflective surface.

    - none: no coherence loss
    - rayleigh: Rayleigh roughness factor for specular coherence ~ exp(-(4*pi*sigma*cos(theta)/lambda)^2)
    """

    name = model.strip().lower().replace("-", "_")
    if name in {"none", "off", "0"}:
        return 1.0
    if name in {"rayleigh", "roughness", "specular"}:
        if wavelength_m <= 0:
            raise ValueError("wavelength_m must be > 0")
        if rms_m < 0:
            raise ValueError("rms_m must be >= 0")
        c = float(np.clip(incidence_cos, 0.0, 1.0))
        x = (4.0 * np.pi * float(rms_m) * c) / float(wavelength_m)
        return float(np.exp(-(x * x)))
    raise ValueError("coherence-model must be one of: none, rayleigh")


def _rmse_m(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.sqrt(np.mean((a - b) ** 2)))


def _estimate_step_mid_x(h_m: np.ndarray) -> float:
    """Estimate step height assuming a vertical step at mid x (matches make_surface default)."""

    ny, nx = h_m.shape
    mid = nx // 2
    left = np.median(h_m[:, :mid])
    right = np.median(h_m[:, mid:])
    return float(right - left)


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Parameter sweep comparing classical PSI vs quantum-like (synthetic wavelength) coincidence PSI."
    )
    ap.add_argument("--outdir", type=str, default="outputs/sweep")
    ap.add_argument(
        "--surface-sur",
        type=str,
        default=None,
        help="Optional Mountains/DigitalSurf .sur file to use as the ground-truth surface (downsampled to --nx/--ny). Overrides rms/step synthetic generation.",
    )
    ap.add_argument("--nreps", type=int, default=10)
    ap.add_argument("--nx", type=int, default=256)
    ap.add_argument("--ny", type=int, default=256)
    ap.add_argument("--size-x", type=float, default=1e-3)
    ap.add_argument("--size-y", type=float, default=1e-3)
    ap.add_argument("--corr-len-um", type=float, default=25.0)
    ap.add_argument(
        "--rms-nm",
        type=float,
        nargs="+",
        default=[20.0, 50.0, 80.0, 120.0],
        help="RMS roughness values to sweep (nm).",
    )
    ap.add_argument(
        "--rms-grid",
        type=str,
        choices=["smoke", "paper", "dense"],
        default=None,
        help="Convenience preset for --rms-nm (overrides --rms-nm if provided).",
    )
    ap.add_argument(
        "--step-nm",
        type=float,
        nargs="+",
        default=[0.0, 200.0, 400.0, 800.0, 1200.0],
        help="Step heights to sweep (nm).",
    )
    ap.add_argument(
        "--step-grid",
        type=str,
        choices=["smoke", "paper", "dense"],
        default=None,
        help="Convenience preset for --step-nm (overrides --step-nm if provided).",
    )

    # Classical model params
    ap.add_argument("--lambda-class-nm", type=float, default=532.0)
    ap.add_argument("--class-visibility", type=float, default=0.85)
    ap.add_argument("--class-photons", type=float, default=8e4)

    ap.add_argument(
        "--recon",
        type=str,
        choices=["psi4", "lsq"],
        default="psi4",
        help="Phase reconstruction method. 'psi4' is the standard 4-step formula; 'lsq' is least-squares over sin/cos basis.",
    )

    ap.add_argument(
        "--normalize-frames",
        action="store_true",
        help="Normalize each frame by its mean to mitigate background/amplitude drift.",
    )

    ap.add_argument(
        "--hybrid-smooth-sigma-px",
        type=float,
        default=1.5,
        help="Gaussian smoothing sigma (pixels) for the coarse prior in hybrid unwrapping.",
    )

    # Shared stress-test knobs
    ap.add_argument(
        "--phase-step-sigma-deg",
        type=float,
        default=0.0,
        help="Std dev of phase-step error per frame (degrees).",
    )
    ap.add_argument(
        "--background-drift-frac",
        type=float,
        default=0.0,
        help="Per-frame multiplicative background drift sigma (fraction).",
    )
    ap.add_argument(
        "--amplitude-drift-frac",
        type=float,
        default=0.0,
        help="Per-frame multiplicative fringe amplitude drift sigma (fraction).",
    )

    # Sample optical properties / surface-dependent contrast
    ap.add_argument(
        "--sample-reflectivity",
        type=float,
        nargs="+",
        default=[1.0],
        help="Relative sample reflectivity in [0,1]. Implemented as a multiplicative scale on detected photon budgets.",
    )
    ap.add_argument(
        "--sample-visibility-scale",
        type=float,
        nargs="+",
        default=[1.0],
        help="Additional multiplicative scale on fringe visibility (models e.g. polarization mismatch / alignment / material effects).",
    )
    ap.add_argument(
        "--coherence-model",
        type=str,
        choices=["none", "rayleigh"],
        default="none",
        help="Optional roughness-dependent coherence/contrast model applied to visibility.",
    )
    ap.add_argument(
        "--incidence-cos",
        type=float,
        default=1.0,
        help="cos(theta) for the coherence model (theta=incidence angle). Use 1.0 for normal incidence.",
    )

    # Quantum-like model params
    ap.add_argument("--lambda1-nm", type=float, default=810.0)
    ap.add_argument("--lambda2-nm", type=float, default=809.0)
    ap.add_argument(
        "--quant-interferometer",
        type=str,
        nargs="+",
        choices=["diff", "sum", "noon2", "su11"],
        default=["diff"],
        help="Quantum interferometer forward model(s) to simulate.",
    )
    ap.add_argument("--quant-visibility", type=float, default=0.6)
    ap.add_argument("--quant-pairs", type=float, default=3e4)

    ap.add_argument(
        "--quant-detector-model",
        type=str,
        choices=["simple", "rates"],
        default="simple",
        help="Coincidence detector/noise model. 'rates' adds accidentals via a coincidence window.",
    )
    ap.add_argument(
        "--quant-target-mean-counts",
        type=float,
        default=0.0,
        help="If >0, matches all quantum models to this mean coincidence counts/pixel/frame (fair budget comparison).",
    )
    ap.add_argument(
        "--su11-gain",
        type=float,
        default=0.0,
        help="Phenomenological SU(1,1) gain knob (implemented as improved effective visibility).",
    )
    ap.add_argument("--gate-time-s", type=float, default=1.0)
    ap.add_argument("--pair-rate-hz", type=float, default=0.0)
    ap.add_argument("--eta1", type=float, default=1.0)
    ap.add_argument("--eta2", type=float, default=1.0)
    ap.add_argument("--dark1-hz", type=float, default=0.0)
    ap.add_argument("--dark2-hz", type=float, default=0.0)
    ap.add_argument("--tau-c-s", type=float, default=1e-6)
    ap.add_argument("--deadtime1-s", type=float, default=0.0)
    ap.add_argument("--deadtime2-s", type=float, default=0.0)

    ap.add_argument(
        "--no-surface-fig",
        action="store_true",
        help="Do not save representative ground-truth surface figures (2D + 3D) into the output folder.",
    )

    args = ap.parse_args()

    apply_publication_style(base_fontsize=8.5)

    fixed_surface = None
    if args.surface_sur:
        fixed_surface = load_surface_sur(args.surface_sur, target_nx=int(args.nx), target_ny=int(args.ny))
        fixed_surface = Surface(x=fixed_surface.x, y=fixed_surface.y, h=detrend_plane(fixed_surface.h))

    if args.step_grid is not None:
        if args.step_grid == "smoke":
            args.step_nm = [0.0, 400.0]
        elif args.step_grid == "paper":
            args.step_nm = [0.0, 100.0, 200.0, 300.0, 400.0, 500.0, 600.0, 700.0, 800.0]
        elif args.step_grid == "dense":
            args.step_nm = [
                0.0,
                50.0,
                100.0,
                150.0,
                200.0,
                250.0,
                300.0,
                350.0,
                400.0,
                450.0,
                500.0,
                600.0,
                700.0,
                800.0,
                900.0,
                1000.0,
            ]

    if args.rms_grid is not None:
        if args.rms_grid == "smoke":
            args.rms_nm = [50.0]
        elif args.rms_grid == "paper":
            args.rms_nm = [20.0, 50.0, 80.0, 120.0]
        elif args.rms_grid == "dense":
            args.rms_nm = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 80.0, 100.0, 120.0, 150.0]

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    lam_class = args.lambda_class_nm * 1e-9
    lam1 = args.lambda1_nm * 1e-9
    lam2 = args.lambda2_nm * 1e-9
    lam_eff = effective_wavelength(interferometer="diff", lambda1_m=lam1, lambda2_m=lam2)

    phase_step_sigma_rad = float(np.deg2rad(args.phase_step_sigma_deg))
    phase_steps = np.array([0.0, 0.5 * np.pi, np.pi, 1.5 * np.pi], dtype=float)

    rows: list[dict[str, float | int | str]] = []
    wrote_surface_fig = False

    mean_optical_lambda_m = 0.5 * (lam1 + lam2)

    for step_nm in args.step_nm:
        for rms_nm in args.rms_nm:
            for sample_reflectivity in args.sample_reflectivity:
                for sample_visibility_scale in args.sample_visibility_scale:
                    for rep in range(args.nreps):
                        seed = int(rep)
                        if fixed_surface is not None:
                            surface = fixed_surface
                        else:
                            surface = make_surface(
                                nx=args.nx,
                                ny=args.ny,
                                size_x=args.size_x,
                                size_y=args.size_y,
                                kind="gaussian_rough",
                                rms=rms_nm * 1e-9,
                                corr_len=args.corr_len_um * 1e-6,
                                step_height=step_nm * 1e-9,
                                seed=seed,
                            )
                        h_true = surface.h

                        if (not args.no_surface_fig) and (not wrote_surface_fig):
                            # Save one representative surface per sweep output to document the ground truth.
                            # Use the first generated surface (first scenario, rep=0).
                            if int(rep) == 0:
                                if fixed_surface is not None:
                                    title = "Ground-truth surface (from .sur)"
                                else:
                                    title = f"Ground-truth surface (step={float(step_nm):g} nm, rms={float(rms_nm):g} nm)"
                                save_surface_height_map(outdir / "surface_true_map.png", surface, title=title)
                                save_surface_height_map(outdir / "surface_true_map.pdf", surface, title=title)
                                save_surface_3d(outdir / "surface_true_3d.png", surface, title=title, alpha=0.78)
                                save_surface_3d(outdir / "surface_true_3d.pdf", surface, title=title, alpha=0.78)
                                wrote_surface_fig = True

                        refl = float(sample_reflectivity)
                        vis_scale = float(sample_visibility_scale)
                        if not (0.0 < refl <= 1.0):
                            raise ValueError("--sample-reflectivity values must be in (0, 1]")
                        if vis_scale < 0:
                            raise ValueError("--sample-visibility-scale values must be >= 0")

                        coh_class = _coherence_factor(
                            rms_m=float(rms_nm) * 1e-9,
                            wavelength_m=float(lam_class),
                            model=str(args.coherence_model),
                            incidence_cos=float(args.incidence_cos),
                        )
                        coh_quant = _coherence_factor(
                            rms_m=float(rms_nm) * 1e-9,
                            wavelength_m=float(mean_optical_lambda_m),
                            model=str(args.coherence_model),
                            incidence_cos=float(args.incidence_cos),
                        )

                        class_visibility_eff = float(
                            np.clip(float(args.class_visibility) * vis_scale * coh_class, 0.0, 1.0)
                        )
                        quant_visibility_eff = float(
                            np.clip(float(args.quant_visibility) * vis_scale * coh_quant, 0.0, 1.0)
                        )

                        class_photons_eff = float(args.class_photons) * refl
                        quant_pairs_eff = float(args.quant_pairs) * refl
                        quant_target_mean_counts_eff = (
                            float(args.quant_target_mean_counts) * refl if float(args.quant_target_mean_counts) > 0 else 0.0
                        )

                        # Classical
                        I4 = simulate_psi4(
                            h_true,
                            wavelength_m=lam_class,
                            visibility=class_visibility_eff,
                            photons_per_pixel=class_photons_eff,
                            phase_step_error_sigma_rad=phase_step_sigma_rad,
                            background_drift_frac=args.background_drift_frac,
                            amplitude_drift_frac=args.amplitude_drift_frac,
                            seed=seed,
                        )

                        class_mean_counts_per_pixel_frame = float(np.mean(I4))

                        sigma_phi_class = crlb_sigma_phi_from_frames(I4, phase_steps_rad=phase_steps)
                        sigphi_class = summarize_sigma(sigma_phi_class)
                        # Reflective geometry: h = (lambda/4pi) * phi
                        sigma_h_class_nm = (lam_class / (4.0 * np.pi)) * sigma_phi_class * 1e9
                        sigh_class = summarize_sigma(sigma_h_class_nm)

                        if args.recon == "lsq":
                            I4r = normalize_frames_mean(I4) if args.normalize_frames else I4
                            phi_w = reconstruct_phase_lsq(I4r, phase_steps_rad=phase_steps)
                        else:
                            phi_w = reconstruct_psi4(I4)
                        h_class = height_from_phase(unwrap_2d_simple(phi_w), wavelength_m=lam_class)

                        # Metrics (true + classical shared)
                        m_true = roughness_metrics(h_true)
                        m_class = roughness_metrics(h_class)

                        # Height RMSE after plane detrend (texture-focused)
                        h_true_dt = detrend_plane(h_true)
                        h_class_dt = detrend_plane(h_class)
                        step_true_m = float(step_nm) * 1e-9

                        # Step error (metrology-relevant for discontinuities)
                        step_class_m = _estimate_step_mid_x(h_class)

                        # Always write classical row
                        err_class = roughness_errors(m_class, m_true)
                        rows.append(
                            {
                                "method": "classical",
                                "step_nm": float(step_nm),
                                "rms_nm": float(rms_nm),
                                "sample_reflectivity": refl,
                                "sample_visibility_scale": vis_scale,
                                "coherence_model": str(args.coherence_model),
                                "incidence_cos": float(args.incidence_cos),
                                "coherence_class": float(coh_class),
                                "coherence_quant": float(coh_quant),
                                "lambda_class_nm": float(args.lambda_class_nm),
                                "lambda1_nm": float(args.lambda1_nm),
                                "lambda2_nm": float(args.lambda2_nm),
                                "lambda_eff_um": float(lam_eff * 1e6),
                                "class_visibility": float(args.class_visibility),
                                "class_visibility_eff": float(class_visibility_eff),
                                "class_photons_per_pixel": float(args.class_photons),
                                "class_photons_per_pixel_eff": float(class_photons_eff),
                                "class_mean_counts_per_pixel_frame": class_mean_counts_per_pixel_frame,
                                "crlb_phi_rad_mean": float(sigphi_class["mean"]),
                                "crlb_phi_rad_median": float(sigphi_class["median"]),
                                "crlb_phi_rad_p90": float(sigphi_class["p90"]),
                                "crlb_h_nm_mean": float(sigh_class["mean"]),
                                "crlb_h_nm_median": float(sigh_class["median"]),
                                "crlb_h_nm_p90": float(sigh_class["p90"]),
                                "quant_interferometer": "-",
                                "quant_detector_model": str(args.quant_detector_model),
                                "quant_visibility": float(args.quant_visibility),
                                "quant_visibility_eff": float(quant_visibility_eff),
                                "quant_pairs_per_pixel": float(args.quant_pairs),
                                "quant_pairs_per_pixel_eff": float(quant_pairs_eff),
                                "gate_time_s": float(args.gate_time_s),
                                "tau_c_s": float(args.tau_c_s),
                                "eta1": float(args.eta1),
                                "eta2": float(args.eta2),
                                "dark1_hz": float(args.dark1_hz),
                                "dark2_hz": float(args.dark2_hz),
                                "phase_step_sigma_deg": float(args.phase_step_sigma_deg),
                                "deadtime1_s": float(args.deadtime1_s),
                                "deadtime2_s": float(args.deadtime2_s),
                                "background_drift_frac": float(args.background_drift_frac),
                                "amplitude_drift_frac": float(args.amplitude_drift_frac),
                                "normalize_frames": int(bool(args.normalize_frames)),
                                "hybrid_smooth_sigma_px": float(args.hybrid_smooth_sigma_px),
                                "recon": str(args.recon),
                                "rep": int(rep),
                                "Sa_true_nm": m_true.Sa * 1e9,
                                "Sq_true_nm": m_true.Sq * 1e9,
                                "Sz_true_nm": m_true.Sz * 1e9,
                                "Sa_est_nm": m_class.Sa * 1e9,
                                "Sq_est_nm": m_class.Sq * 1e9,
                                "Sz_est_nm": m_class.Sz * 1e9,
                                "bias_Sa_nm": err_class["bias_Sa"] * 1e9,
                                "bias_Sq_nm": err_class["bias_Sq"] * 1e9,
                                "bias_Sz_nm": err_class["bias_Sz"] * 1e9,
                                "rmse_h_nm": _rmse_m(h_class_dt, h_true_dt) * 1e9,
                                "step_est_nm": step_class_m * 1e9,
                                "step_err_nm": (step_class_m - step_true_m) * 1e9,
                            }
                        )

                        # Quantum models + hybrid per model
                        for qint in args.quant_interferometer:
                            lam_eff_i = effective_wavelength(interferometer=qint, lambda1_m=lam1, lambda2_m=lam2)

                            pair_rate_hz = None
                            if args.quant_detector_model == "rates":
                                # If user specified a rate, use it; else infer rate from quant_pairs_per_gate.
                                pair_rate_hz = (
                                    float(args.pair_rate_hz)
                                    if float(args.pair_rate_hz) > 0
                                    else float(quant_pairs_eff) / float(args.gate_time_s)
                                )

                            C4 = simulate_coincidence_psi4(
                                h_true,
                                lambda1_m=lam1,
                                lambda2_m=lam2,
                                visibility=quant_visibility_eff,
                                pairs_per_pixel=quant_pairs_eff,
                                phase_step_error_sigma_rad=phase_step_sigma_rad,
                                background_drift_frac=args.background_drift_frac,
                                amplitude_drift_frac=args.amplitude_drift_frac,
                                seed=seed,
                                interferometer=qint,
                                detector_model=args.quant_detector_model,
                                gate_time_s=float(args.gate_time_s),
                                pair_rate_hz=pair_rate_hz,
                                eta1=float(args.eta1),
                                eta2=float(args.eta2),
                                dark1_hz=float(args.dark1_hz),
                                dark2_hz=float(args.dark2_hz),
                                tau_c_s=float(args.tau_c_s),
                                deadtime1_s=float(args.deadtime1_s),
                                deadtime2_s=float(args.deadtime2_s),
                                target_mean_counts_per_pixel=(
                                    float(quant_target_mean_counts_eff)
                                    if float(quant_target_mean_counts_eff) > 0
                                    else None
                                ),
                                su11_gain=float(args.su11_gain),
                            )

                            quant_mean_counts_per_pixel_frame = float(np.mean(C4))

                            sigma_phi_quant = crlb_sigma_phi_from_frames(C4, phase_steps_rad=phase_steps)
                            sigphi_quant = summarize_sigma(sigma_phi_quant)
                            sigma_h_quant_nm = (lam_eff_i / (4.0 * np.pi)) * sigma_phi_quant * 1e9
                            sigh_quant = summarize_sigma(sigma_h_quant_nm)

                            if args.recon == "lsq":
                                C4r = normalize_frames_mean(C4) if args.normalize_frames else C4
                                phi_qw = reconstruct_phase_lsq(C4r, phase_steps_rad=phase_steps)
                            else:
                                phi_qw = reconstruct_psi4(C4)
                            h_quant = height_from_phase(unwrap_2d_simple(phi_qw), wavelength_m=lam_eff_i)

                            h_hybrid = unwrap_height_with_coarse(
                                phi_w,
                                coarse_height_m=h_quant,
                                wavelength_short_m=lam_class,
                                coarse_smooth_sigma_px=args.hybrid_smooth_sigma_px,
                            )

                            m_quant = roughness_metrics(h_quant)
                            m_hybrid = roughness_metrics(h_hybrid)
                            h_quant_dt = detrend_plane(h_quant)
                            h_hybrid_dt = detrend_plane(h_hybrid)
                            step_quant_m = _estimate_step_mid_x(h_quant)
                            step_hybrid_m = _estimate_step_mid_x(h_hybrid)

                            # Backwards-compatible naming when only diff is used
                            if len(args.quant_interferometer) == 1 and qint == "diff":
                                method_q = "quantum_like"
                                method_h = "hybrid"
                            else:
                                method_q = f"quant_{qint}"
                                method_h = f"hybrid_{qint}"

                            for method, h_est_dt, m_est, step_est_m in (
                                (method_q, h_quant_dt, m_quant, step_quant_m),
                                (method_h, h_hybrid_dt, m_hybrid, step_hybrid_m),
                            ):
                                err = roughness_errors(m_est, m_true)
                                rows.append(
                                    {
                                        "method": method,
                                        "step_nm": float(step_nm),
                                        "rms_nm": float(rms_nm),
                                        "sample_reflectivity": refl,
                                        "sample_visibility_scale": vis_scale,
                                        "coherence_model": str(args.coherence_model),
                                        "incidence_cos": float(args.incidence_cos),
                                        "coherence_class": float(coh_class),
                                        "coherence_quant": float(coh_quant),
                                        "lambda_class_nm": float(args.lambda_class_nm),
                                        "lambda1_nm": float(args.lambda1_nm),
                                        "lambda2_nm": float(args.lambda2_nm),
                                        "lambda_eff_um": float(lam_eff_i * 1e6),
                                        "class_visibility": float(args.class_visibility),
                                        "class_visibility_eff": float(class_visibility_eff),
                                        "class_photons_per_pixel": float(args.class_photons),
                                        "class_photons_per_pixel_eff": float(class_photons_eff),
                                        "class_mean_counts_per_pixel_frame": class_mean_counts_per_pixel_frame,
                                        "quant_interferometer": str(qint),
                                        "quant_detector_model": str(args.quant_detector_model),
                                        "quant_visibility": float(args.quant_visibility),
                                        "quant_visibility_eff": float(quant_visibility_eff),
                                        "quant_pairs_per_pixel": float(args.quant_pairs),
                                        "quant_pairs_per_pixel_eff": float(quant_pairs_eff),
                                        "quant_mean_counts_per_pixel_frame": quant_mean_counts_per_pixel_frame,
                                        "crlb_phi_rad_mean": float(sigphi_quant["mean"])
                                        if method == method_q
                                        else float(sigphi_class["mean"]),
                                        "crlb_phi_rad_median": float(sigphi_quant["median"])
                                        if method == method_q
                                        else float(sigphi_class["median"]),
                                        "crlb_phi_rad_p90": float(sigphi_quant["p90"])
                                        if method == method_q
                                        else float(sigphi_class["p90"]),
                                        "crlb_h_nm_mean": float(sigh_quant["mean"])
                                        if method == method_q
                                        else float(sigh_class["mean"]),
                                        "crlb_h_nm_median": float(sigh_quant["median"])
                                        if method == method_q
                                        else float(sigh_class["median"]),
                                        "crlb_h_nm_p90": float(sigh_quant["p90"])
                                        if method == method_q
                                        else float(sigh_class["p90"]),
                                        # For hybrid, record the coarse (quantum) bound as well.
                                        "crlb_phi_coarse_rad_median": float(sigphi_quant["median"])
                                        if method == method_h
                                        else float("nan"),
                                        "crlb_h_coarse_nm_median": float(sigh_quant["median"])
                                        if method == method_h
                                        else float("nan"),
                                        "quant_target_mean_counts": float(args.quant_target_mean_counts),
                                        "quant_target_mean_counts_eff": float(quant_target_mean_counts_eff),
                                        "su11_gain": float(args.su11_gain),
                                        "gate_time_s": float(args.gate_time_s),
                                        "tau_c_s": float(args.tau_c_s),
                                        "eta1": float(args.eta1),
                                        "eta2": float(args.eta2),
                                        "dark1_hz": float(args.dark1_hz),
                                        "dark2_hz": float(args.dark2_hz),
                                        "deadtime1_s": float(args.deadtime1_s),
                                        "deadtime2_s": float(args.deadtime2_s),
                                        "phase_step_sigma_deg": float(args.phase_step_sigma_deg),
                                        "background_drift_frac": float(args.background_drift_frac),
                                        "amplitude_drift_frac": float(args.amplitude_drift_frac),
                                        "normalize_frames": int(bool(args.normalize_frames)),
                                        "hybrid_smooth_sigma_px": float(args.hybrid_smooth_sigma_px),
                                        "recon": str(args.recon),
                                        "rep": int(rep),
                                        "Sa_true_nm": m_true.Sa * 1e9,
                                        "Sq_true_nm": m_true.Sq * 1e9,
                                        "Sz_true_nm": m_true.Sz * 1e9,
                                        "Sa_est_nm": m_est.Sa * 1e9,
                                        "Sq_est_nm": m_est.Sq * 1e9,
                                        "Sz_est_nm": m_est.Sz * 1e9,
                                        "bias_Sa_nm": err["bias_Sa"] * 1e9,
                                        "bias_Sq_nm": err["bias_Sq"] * 1e9,
                                        "bias_Sz_nm": err["bias_Sz"] * 1e9,
                                        "rmse_h_nm": _rmse_m(h_est_dt, h_true_dt) * 1e9,
                                        "step_est_nm": step_est_m * 1e9,
                                        "step_err_nm": (step_est_m - step_true_m) * 1e9,
                                    }
                                )

    csv_path = outdir / "sweep.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        fieldnames: list[str] = []
        seen: set[str] = set()
        for r in rows:
            for k in r.keys():
                if k not in seen:
                    fieldnames.append(k)
                    seen.add(k)
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

    write_metrics_json(
        str(outdir / "params.json"),
        params={
            "lambda_class_m": lam_class,
            "lambda1_m": lam1,
            "lambda2_m": lam2,
            "lambda_eff_m": lam_eff,
            "nreps": args.nreps,
            "step_nm": args.step_nm,
            "rms_nm": args.rms_nm,
            "phase_step_sigma_deg": args.phase_step_sigma_deg,
            "background_drift_frac": args.background_drift_frac,
            "amplitude_drift_frac": args.amplitude_drift_frac,
            "recon": args.recon,
            "normalize_frames": bool(args.normalize_frames),
            "hybrid_smooth_sigma_px": args.hybrid_smooth_sigma_px,
            "quant_interferometer": args.quant_interferometer,
            "quant_detector_model": args.quant_detector_model,
            "quant_target_mean_counts": args.quant_target_mean_counts,
            "su11_gain": args.su11_gain,
            "gate_time_s": args.gate_time_s,
            "pair_rate_hz": args.pair_rate_hz,
            "eta1": args.eta1,
            "eta2": args.eta2,
            "dark1_hz": args.dark1_hz,
            "dark2_hz": args.dark2_hz,
            "tau_c_s": args.tau_c_s,
            "deadtime1_s": args.deadtime1_s,
            "deadtime2_s": args.deadtime2_s,
            "sample_reflectivity": args.sample_reflectivity,
            "sample_visibility_scale": args.sample_visibility_scale,
            "coherence_model": args.coherence_model,
            "incidence_cos": args.incidence_cos,
        },
    )

    print(f"Wrote: {csv_path}")


if __name__ == "__main__":
    main()
