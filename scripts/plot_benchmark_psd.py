#!/usr/bin/env python3

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import matplotlib.pyplot as plt
import numpy as np

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "src"))

from qiprof.metrics import detrend_plane, psd2d, radial_psd
from qiprof.plot_style import apply_publication_style
from qiprof.reconstruct import height_from_phase, reconstruct_psi4, unwrap_2d_simple, unwrap_height_with_coarse
from qiprof.sim_classical import simulate_psi4
from qiprof.sim_quantum import effective_wavelength, simulate_coincidence_psi4
from qiprof.surfaces import Surface, load_surface_sur


def _radial_profile(h_m: np.ndarray, *, dx: float, dy: float) -> tuple[np.ndarray, np.ndarray]:
    fx, fy, psd = psd2d(h_m, dx=dx, dy=dy)
    fr, prof = radial_psd(fx, fy, psd, nbins=140, fmin=max(float(np.min(np.abs(fx[fx != 0]))), float(np.min(np.abs(fy[fy != 0])))))
    mask = np.isfinite(prof) & (prof > 0.0) & np.isfinite(fr) & (fr > 0.0)
    return fr[mask], prof[mask]


def _surface_title(surface_sur: Path) -> str:
    treatment_map = {
        "szlifowane": "Grinding",
        "oselkowane": "Honed",
        "szkielkowane": "Glass bead",
        "t_wyk": "Turning finish",
        "t_zgrub": "Turning rough",
        "t_zgrubne": "Turning rough",
        "frez_wyk": "Milling finish",
        "frez_zgr": "Milling rough",
        "wedm_wyk": "WEDM finish",
        "wedm_zgru_1prz": "WEDM rough",
        "wedm_zgru": "WEDM rough",
        "nagniat": "Burnished",
    }
    stem = surface_sur.stem
    material = stem
    treatment = ""
    if "_" in stem:
        material, code = stem.rsplit("_", 1)
        treatment = treatment_map.get(code, code.replace("-", " "))
    material = material.replace("P1-", "").replace("Ti6A14V", "Ti-6Al-4V").replace("_", " ")
    return f"{material} / {treatment}" if treatment else material


def _profiles_for_surface(
    surface_sur: Path,
    *,
    nx: int,
    ny: int,
    lambda_class_nm: float,
    class_photons: float,
    class_visibility: float,
    lambda1_nm: float,
    lambda2_nm: float,
    quant_pairs: float,
    hybrid_smooth_sigma_px: float,
) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    surface0 = load_surface_sur(surface_sur, target_nx=int(nx), target_ny=int(ny))
    valid_mask = getattr(surface0, "valid_mask", None)
    h_true = detrend_plane(surface0.h, valid_mask=valid_mask)
    if valid_mask is not None and bool(np.any(valid_mask)):
        fill = float(np.nanmedian(h_true[valid_mask]))
        h_true = np.where(valid_mask, h_true, fill)
    surface = Surface(x=surface0.x, y=surface0.y, h=h_true, valid_mask=valid_mask)
    dx = float(surface.x[1] - surface.x[0])
    dy = float(surface.y[1] - surface.y[0])

    lam_class = float(lambda_class_nm) * 1e-9
    I4 = simulate_psi4(surface.h, wavelength_m=lam_class, photons_per_pixel=float(class_photons), visibility=float(class_visibility))
    phi_w = reconstruct_psi4(I4)
    h_class = height_from_phase(unwrap_2d_simple(phi_w), wavelength_m=lam_class)

    lam1 = float(lambda1_nm) * 1e-9
    lam2 = float(lambda2_nm) * 1e-9
    lam_eff = effective_wavelength(interferometer="diff", lambda1_m=lam1, lambda2_m=lam2)
    C4 = simulate_coincidence_psi4(
        surface.h,
        lambda1_m=lam1,
        lambda2_m=lam2,
        visibility=0.6,
        background=1.0,
        amplitude=1.0,
        pairs_per_pixel=float(quant_pairs),
        interferometer="diff",
    )
    phi_qw = reconstruct_psi4(C4)
    h_quant = height_from_phase(unwrap_2d_simple(phi_qw), wavelength_m=lam_eff)
    h_hybrid = unwrap_height_with_coarse(
        phi_w,
        coarse_height_m=h_quant,
        wavelength_short_m=lam_class,
        coarse_smooth_sigma_px=float(hybrid_smooth_sigma_px),
    )

    return {
        "Reference": _radial_profile(surface.h, dx=dx, dy=dy),
        "Classical": _radial_profile(h_class, dx=dx, dy=dy),
        "Coincidence-proxy": _radial_profile(h_quant, dx=dx, dy=dy),
        "Hybrid": _radial_profile(h_hybrid, dx=dx, dy=dy),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate a representative radial-PSD fidelity plot for the measured-surface benchmark")
    ap.add_argument(
        "--surface-sur",
        type=Path,
        nargs="+",
        default=[Path("data/1.4301_szlifowane.sur"), Path("data/P1-Ti6A14V_t_wyk.sur")],
    )
    ap.add_argument("--out", type=Path, default=Path("outputs/paper_alicona_benchmark/figures/psd_representative.pdf"))
    ap.add_argument("--nx", type=int, default=256)
    ap.add_argument("--ny", type=int, default=256)
    ap.add_argument("--lambda-class-nm", type=float, default=532.0)
    ap.add_argument("--class-photons", type=float, default=8e4)
    ap.add_argument("--class-visibility", type=float, default=0.85)
    ap.add_argument("--lambda1-nm", type=float, default=810.0)
    ap.add_argument("--lambda2-nm", type=float, default=809.0)
    ap.add_argument("--quant-pairs", type=float, default=3e4)
    ap.add_argument("--hybrid-smooth-sigma-px", type=float, default=1.5)
    args = ap.parse_args()

    apply_publication_style(base_fontsize=8.5)
    args.out.parent.mkdir(parents=True, exist_ok=True)

    surface_paths = [Path(path) for path in args.surface_sur]
    fig_width = 3.35 * len(surface_paths) if len(surface_paths) > 1 else 3.35
    fig, axes = plt.subplots(1, len(surface_paths), figsize=(fig_width, 2.55), constrained_layout=True)
    if len(surface_paths) == 1:
        axes = [axes]

    colors = {
        "Reference": "0.15",
        "Classical": "#1f77b4",
        "Coincidence-proxy": "#d62728",
        "Hybrid": "#2ca02c",
    }

    for ax, surface_sur in zip(axes, surface_paths):
        profiles = _profiles_for_surface(
            surface_sur,
            nx=int(args.nx),
            ny=int(args.ny),
            lambda_class_nm=float(args.lambda_class_nm),
            class_photons=float(args.class_photons),
            class_visibility=float(args.class_visibility),
            lambda1_nm=float(args.lambda1_nm),
            lambda2_nm=float(args.lambda2_nm),
            quant_pairs=float(args.quant_pairs),
            hybrid_smooth_sigma_px=float(args.hybrid_smooth_sigma_px),
        )
        for label, (fr, prof) in profiles.items():
            ax.plot(fr * 1e-3, prof, linewidth=1.4 if label == "Reference" else 1.2, label=label, color=colors[label])
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlabel("Spatial frequency (mm$^{-1}$)")
        ax.set_title(_surface_title(surface_sur))
        ax.grid(True, which="both", alpha=0.25)

    axes[0].set_ylabel("Radial PSD")
    axes[-1].legend(frameon=False, fontsize=7.4, loc="lower left")
    fig.savefig(args.out)
    plt.close(fig)
    print(f"Wrote: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())