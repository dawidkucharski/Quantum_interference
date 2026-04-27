from __future__ import annotations

import argparse
from pathlib import Path
import sys

import matplotlib.pyplot as plt
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
from qiprof.viz import save_surface_3d, save_surface_height_map


def save_image(path: Path, arr: np.ndarray, *, title: str, cmap: str = "viridis") -> None:
    masked = np.ma.masked_invalid(arr)
    fig = plt.figure(figsize=(6.0, 5.0), dpi=180)
    ax = fig.add_subplot(111)

    if path.suffix.lower() == ".pdf":
        xx = np.arange(masked.shape[1] + 1, dtype=float)
        yy = np.arange(masked.shape[0] + 1, dtype=float)
        im = ax.pcolormesh(xx, yy, masked, cmap=cmap, shading="flat")
        ax.set_aspect("auto")
    else:
        im = ax.imshow(masked, cmap=cmap, origin="lower", aspect="auto")

    fig.colorbar(im, ax=ax)
    ax.set_title(title)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def save_image_pair(outdir: Path, stem: str, arr: np.ndarray, *, title: str, cmap: str = "viridis") -> None:
    save_image(outdir / f"{stem}.png", arr, title=title, cmap=cmap)
    save_image(outdir / f"{stem}.pdf", arr, title=title, cmap=cmap)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", type=str, default="outputs/demo")
    ap.add_argument(
        "--surface-sur",
        type=str,
        default=None,
        help="Optional Mountains/DigitalSurf .sur file to use as the ground-truth surface (downsampled to 256x256).",
    )
    ap.add_argument("--lambda1-nm", type=float, default=810.0)
    ap.add_argument("--lambda2-nm", type=float, default=809.0)
    ap.add_argument(
        "--quant-interferometer",
        type=str,
        choices=["diff", "sum", "noon2", "su11"],
        default="diff",
        help="Quantum interferometer forward model.",
    )
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
        help="If >0, matches the quantum channel to this mean coincidence counts/pixel/frame.",
    )
    ap.add_argument("--quant-pairs", type=float, default=3e4)
    ap.add_argument("--gate-time-s", type=float, default=1.0)
    ap.add_argument("--pair-rate-hz", type=float, default=0.0)
    ap.add_argument("--eta1", type=float, default=1.0)
    ap.add_argument("--eta2", type=float, default=1.0)
    ap.add_argument("--dark1-hz", type=float, default=0.0)
    ap.add_argument("--dark2-hz", type=float, default=0.0)
    ap.add_argument("--tau-c-s", type=float, default=1e-6)
    ap.add_argument("--su11-gain", type=float, default=0.0)
    ap.add_argument(
        "--normalize-frames",
        action="store_true",
        help="Normalize each PSI/coincidence frame by its mean to reduce drift artifacts.",
    )
    ap.add_argument(
        "--recon",
        type=str,
        choices=["psi4", "lsq"],
        default="psi4",
        help="Phase reconstruction method.",
    )
    ap.add_argument(
        "--hybrid-smooth-sigma-px",
        type=float,
        default=1.5,
        help="Gaussian smoothing sigma (pixels) applied to coarse height prior in hybrid unwrapping.",
    )
    args = ap.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    apply_publication_style(base_fontsize=8.5)

    # --- Ground truth surface ---
    if args.surface_sur:
        surface0 = load_surface_sur(args.surface_sur, target_nx=256, target_ny=256)
        valid_mask = getattr(surface0, "valid_mask", None)
        h0_dt = detrend_plane(surface0.h, valid_mask=valid_mask)
        # Do not let invalid/missing pixels (which are often filled) turn into
        # large excursions after detrending; they should not influence the
        # simulation/reconstruction or show up as vertical spikes in plots.
        if valid_mask is not None and bool(np.any(valid_mask)):
            fill = float(np.nanmedian(h0_dt[valid_mask]))
            h0_dt = np.where(valid_mask, h0_dt, fill)

        surface = Surface(x=surface0.x, y=surface0.y, h=h0_dt, valid_mask=valid_mask)
    else:
        surface = make_surface(
            nx=256,
            ny=256,
            size_x=1e-3,
            size_y=1e-3,
            kind="gaussian_rough",
            rms=80e-9,
            corr_len=25e-6,
            step_height=400e-9,
        )
        valid_mask = None
    h_true = surface.h
    dx = float(surface.x[1] - surface.x[0])
    dy = float(surface.y[1] - surface.y[0])

    # Visualize the exact surface used by both interferometers
    save_surface_height_map(outdir / "surface_true_map.png", surface, title="Ground-truth surface")
    save_surface_height_map(outdir / "surface_true_map.pdf", surface, title="Ground-truth surface")
    save_surface_3d(outdir / "surface_true_3d.png", surface, title="Ground-truth surface (3D)", alpha=0.78)
    save_surface_3d(outdir / "surface_true_3d.pdf", surface, title="Ground-truth surface (3D)", alpha=0.78)

    # --- Classical PSI simulation + reconstruction ---
    lam_class = 532e-9
    I4 = simulate_psi4(h_true, wavelength_m=lam_class, photons_per_pixel=8e4, visibility=0.85)
    phase_steps = np.array([0.0, 0.5 * np.pi, np.pi, 1.5 * np.pi], dtype=float)
    if args.recon == "lsq":
        I4r = normalize_frames_mean(I4) if args.normalize_frames else I4
        phi_w = reconstruct_phase_lsq(I4r, phase_steps_rad=phase_steps)
    else:
        phi_w = reconstruct_psi4(I4)
    phi_u = unwrap_2d_simple(phi_w)
    h_class = height_from_phase(phi_u, wavelength_m=lam_class)

    # --- Quantum-like coincidence simulation + reconstruction ---
    lam1 = args.lambda1_nm * 1e-9
    lam2 = args.lambda2_nm * 1e-9
    lam_eff = effective_wavelength(interferometer=args.quant_interferometer, lambda1_m=lam1, lambda2_m=lam2)
    q_visibility = 0.6
    q_background = 1.0
    q_amplitude = 1.0

    pair_rate_hz = None
    if args.quant_detector_model == "rates":
        pair_rate_hz = float(args.pair_rate_hz) if float(args.pair_rate_hz) > 0 else float(args.quant_pairs) / float(args.gate_time_s)

    C4 = simulate_coincidence_psi4(
        h_true,
        lambda1_m=lam1,
        lambda2_m=lam2,
        visibility=q_visibility,
        background=q_background,
        amplitude=q_amplitude,
        pairs_per_pixel=args.quant_pairs,
        interferometer=args.quant_interferometer,
        detector_model=args.quant_detector_model,
        gate_time_s=float(args.gate_time_s),
        pair_rate_hz=pair_rate_hz,
        eta1=float(args.eta1),
        eta2=float(args.eta2),
        dark1_hz=float(args.dark1_hz),
        dark2_hz=float(args.dark2_hz),
        tau_c_s=float(args.tau_c_s),
        target_mean_counts_per_pixel=(
            float(args.quant_target_mean_counts) if float(args.quant_target_mean_counts) > 0 else None
        ),
        su11_gain=float(args.su11_gain),
    )
    if args.recon == "lsq":
        C4r = normalize_frames_mean(C4) if args.normalize_frames else C4
        phi_qw = reconstruct_phase_lsq(C4r, phase_steps_rad=phase_steps)
    else:
        phi_qw = reconstruct_psi4(C4)
    phi_qu = unwrap_2d_simple(phi_qw)
    h_quant = height_from_phase(phi_qu, wavelength_m=lam_eff)

    # --- Hybrid: use quantum-like coarse height to unwrap classical ---
    h_hybrid = unwrap_height_with_coarse(
        phi_w,
        coarse_height_m=h_quant,
        wavelength_short_m=lam_class,
        coarse_smooth_sigma_px=args.hybrid_smooth_sigma_px,
    )

    # --- Metrics ---
    m_true = roughness_metrics(h_true, valid_mask=valid_mask)
    m_class = roughness_metrics(h_class, valid_mask=valid_mask)
    m_quant = roughness_metrics(h_quant, valid_mask=valid_mask)
    m_hybrid = roughness_metrics(h_hybrid, valid_mask=valid_mask)

    h_true_dt = detrend_plane(h_true, valid_mask=valid_mask)
    h_class_dt = detrend_plane(h_class, valid_mask=valid_mask)
    h_quant_dt = detrend_plane(h_quant, valid_mask=valid_mask)
    h_hybrid_dt = detrend_plane(h_hybrid, valid_mask=valid_mask)

    if valid_mask is None:
        msk = np.isfinite(h_true_dt) & np.isfinite(h_class_dt)
    else:
        msk = valid_mask & np.isfinite(h_true_dt) & np.isfinite(h_class_dt)
    rmse_class = float(np.sqrt(np.mean(((h_class_dt - h_true_dt)[msk]) ** 2)))

    if valid_mask is None:
        msk = np.isfinite(h_true_dt) & np.isfinite(h_quant_dt)
    else:
        msk = valid_mask & np.isfinite(h_true_dt) & np.isfinite(h_quant_dt)
    rmse_quant = float(np.sqrt(np.mean(((h_quant_dt - h_true_dt)[msk]) ** 2)))

    if valid_mask is None:
        msk = np.isfinite(h_true_dt) & np.isfinite(h_hybrid_dt)
    else:
        msk = valid_mask & np.isfinite(h_true_dt) & np.isfinite(h_hybrid_dt)
    rmse_hybrid = float(np.sqrt(np.mean(((h_hybrid_dt - h_true_dt)[msk]) ** 2)))

    write_metrics_json(
        str(outdir / "metrics.json"),
        true=m_true,
        classical=m_class,
        quantum_like=m_quant,
        hybrid=m_hybrid,
        classical_error=roughness_errors(m_class, m_true),
        quantum_like_error=roughness_errors(m_quant, m_true),
        hybrid_error=roughness_errors(m_hybrid, m_true),
        height_rmse_m={"classical": rmse_class, "quantum_like": rmse_quant, "hybrid": rmse_hybrid},
        params={
            "lambda_class_m": lam_class,
            "lambda1_m": lam1,
            "lambda2_m": lam2,
            "lambda_eff_m": lam_eff,
        },
    )

    # --- Figures ---
    save_image_pair(outdir, "h_true", h_true * 1e9, title="h_true (nm)")
    save_image_pair(outdir, "h_class", h_class * 1e9, title="h_classical (nm)")
    save_image_pair(outdir, "h_quant", h_quant * 1e9, title="h_quantum-like (nm)")
    save_image_pair(outdir, "h_hybrid", h_hybrid * 1e9, title="h_hybrid (nm)")
    save_image_pair(outdir, "class_wrapped_phase", phi_w, title="Classical wrapped phase (rad)", cmap="twilight")
    save_image_pair(outdir, "quant_wrapped_phase", phi_qw, title="Quantum-like wrapped phase (rad)", cmap="twilight")
    save_image_pair(outdir, "C_counts", C4[0], title="Coincidence counts (frame 1)", cmap="magma")

    # Simple intensity frame visualization
    save_image_pair(outdir, "I1", I4[0], title="PSI frame I1")
    save_image_pair(outdir, "I2", I4[1], title="PSI frame I2")

    print(f"Wrote outputs to: {outdir}")


if __name__ == "__main__":
    main()
