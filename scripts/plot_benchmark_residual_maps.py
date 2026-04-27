#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path
import sys

import numpy as np

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "src"))

from qiprof.labels import decode_sur_stem
from qiprof.metrics import detrend_plane
from qiprof.plot_style import apply_publication_style
from qiprof.reconstruct import height_from_phase, reconstruct_psi4, unwrap_height_with_coarse, unwrap_phase_2d
from qiprof.sim_classical import simulate_psi4
from qiprof.sim_quantum import effective_wavelength, simulate_coincidence_psi4
from qiprof.surfaces import load_surface_sur


def _load_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise ValueError(f"No rows found in {path}")
    return rows


def _collapse_height_rmse(rows: list[dict[str, str]]) -> dict[str, dict[str, object]]:
    grouped: dict[str, dict[str, object]] = {}
    values: dict[tuple[str, str], list[float]] = defaultdict(list)
    for row in rows:
        stem = row["stem"]
        grouped.setdefault(stem, {"stem": stem, "file": row["file"]})
        values[(stem, row["method"])].append(float(row["height_rmse_nm"]))
    for (stem, method), vals in values.items():
        grouped[stem][method] = float(np.median(np.asarray(vals, dtype=float)))
    return grouped


def _select_representatives(rows: list[dict[str, str]]) -> list[tuple[str, Path, str]]:
    collapsed = _collapse_height_rmse(rows)
    if len(collapsed) < 3:
        raise ValueError("Need at least three measured surfaces to build representative residual maps")

    stems = [stem for stem, entry in collapsed.items() if {"classical", "quantum_like", "hybrid"} <= set(entry.keys())]
    if len(stems) < 3:
        raise ValueError("Need at least three complete surfaces with all methods present")

    good = min(stems, key=lambda stem: float(collapsed[stem]["hybrid"]))
    hybrid_vals = np.asarray([float(collapsed[stem]["hybrid"]) for stem in stems], dtype=float)
    hybrid_med = float(np.median(hybrid_vals))

    remaining = [stem for stem in stems if stem != good]
    medium = min(remaining, key=lambda stem: abs(float(collapsed[stem]["hybrid"]) - hybrid_med))

    remaining = [stem for stem in remaining if stem != medium]
    failure = max(
        remaining,
        key=lambda stem: float(collapsed[stem]["quantum_like"]) / max(min(float(collapsed[stem]["classical"]), float(collapsed[stem]["hybrid"])), 1e-9),
    )

    return [
        (good, Path(str(collapsed[good]["file"])), "Low-error case"),
        (medium, Path(str(collapsed[medium]["file"])), "Mid-regime case"),
        (failure, Path(str(collapsed[failure]["file"])), "Direct-Q failure case"),
    ]


def _reconstruct_maps(path: Path, *, nx: int, ny: int, unwrap_method: str) -> dict[str, np.ndarray]:
    surface = load_surface_sur(path, target_nx=nx, target_ny=ny)
    valid_mask = getattr(surface, "valid_mask", None)
    h_true = detrend_plane(surface.h, valid_mask=valid_mask)
    if valid_mask is not None and bool(np.any(valid_mask)):
        fill = float(np.nanmedian(h_true[valid_mask]))
        h_true = np.where(valid_mask, h_true, fill)

    stem = path.stem
    np.random.seed(hash(stem) & 0xFFFFFFFF)

    lam_class = 532.0e-9
    lam1 = 810.0e-9
    lam2 = 809.0e-9
    lam_eff = effective_wavelength(interferometer="diff", lambda1_m=lam1, lambda2_m=lam2)

    I4 = simulate_psi4(h_true, wavelength_m=lam_class, photons_per_pixel=8e4, visibility=0.85)
    phi_w = reconstruct_psi4(I4)
    h_class = height_from_phase(unwrap_phase_2d(phi_w, method=unwrap_method), wavelength_m=lam_class)

    C4 = simulate_coincidence_psi4(
        h_true,
        lambda1_m=lam1,
        lambda2_m=lam2,
        visibility=0.6,
        background=1.0,
        amplitude=1.0,
        pairs_per_pixel=3e4,
        interferometer="diff",
        detector_model="simple",
        gate_time_s=1.0,
        pair_rate_hz=None,
        eta1=1.0,
        eta2=1.0,
        dark1_hz=0.0,
        dark2_hz=0.0,
        tau_c_s=1e-6,
        deadtime1_s=0.0,
        deadtime2_s=0.0,
        target_mean_counts_per_pixel=None,
        su11_gain=0.0,
    )
    phi_qw = reconstruct_psi4(C4)
    h_quant = height_from_phase(unwrap_phase_2d(phi_qw, method=unwrap_method), wavelength_m=lam_eff)
    h_hybrid = unwrap_height_with_coarse(
        phi_w,
        coarse_height_m=h_quant,
        wavelength_short_m=lam_class,
        coarse_smooth_sigma_px=1.5,
    )

    def _residual(h_est: np.ndarray) -> np.ndarray:
        return detrend_plane(h_est, valid_mask=valid_mask) - detrend_plane(h_true, valid_mask=valid_mask)

    return {
        "true": h_true,
        "classical_residual": _residual(h_class),
        "quantum_like_residual": _residual(h_quant),
        "hybrid_residual": _residual(h_hybrid),
        "valid_mask": valid_mask if valid_mask is not None else np.isfinite(h_true),
    }


def _masked_limits(data: np.ndarray, mask: np.ndarray, *, percentile: float = 99.0) -> float:
    vals = np.asarray(data[mask], dtype=float)
    vals = vals[np.isfinite(vals)]
    if vals.size == 0:
        return 1.0
    scale = float(np.nanpercentile(np.abs(vals), percentile))
    return max(scale, 1e-12)


def _surface_name(stem: str) -> str:
    label = decode_sur_stem(stem)
    return f"{label.material_en}; {label.treatment_en}"


def main() -> None:
    ap = argparse.ArgumentParser(description="Create representative height/residual maps for the measured-surface benchmark")
    ap.add_argument("--per-surface", type=Path, default=Path("outputs/paper_alicona_benchmark/per_surface.csv"))
    ap.add_argument(
        "--out",
        type=Path,
        default=Path("outputs/paper_alicona_benchmark/figures/residual_maps_representative.pdf"),
    )
    ap.add_argument("--nx", type=int, default=256)
    ap.add_argument("--ny", type=int, default=256)
    ap.add_argument("--unwrap-method", type=str, choices=["simple", "least_squares"], default="simple")
    args = ap.parse_args()

    import matplotlib.pyplot as plt

    rows = _load_rows(args.per_surface)
    selected = _select_representatives(rows)

    apply_publication_style(base_fontsize=8.0)
    fig, axes = plt.subplots(3, 4, figsize=(6.77, 6.8), constrained_layout=True)

    ref_cmap = plt.get_cmap("viridis").copy()
    ref_cmap.set_bad(color="0.92")
    res_cmap = plt.get_cmap("RdBu_r").copy()
    res_cmap.set_bad(color="0.92")

    ref_im = None
    res_im = None
    col_titles = ["Reference", "Classical residual", "Quantum-like residual", "Hybrid residual"]
    for idx, title in enumerate(col_titles):
        axes[0, idx].set_title(title)

    for row_idx, (stem, path, category) in enumerate(selected):
        maps = _reconstruct_maps(path, nx=args.nx, ny=args.ny, unwrap_method=args.unwrap_method)
        mask = np.asarray(maps["valid_mask"], dtype=bool)
        h_true_nm = np.where(mask, np.asarray(maps["true"], dtype=float) * 1e9, np.nan)
        ref_lim = _masked_limits(h_true_nm, mask)

        residual_keys = ["classical_residual", "quantum_like_residual", "hybrid_residual"]
        residuals_nm = {
            key: np.where(mask, np.asarray(maps[key], dtype=float) * 1e9, np.nan) for key in residual_keys
        }
        res_lim = max(_masked_limits(arr, mask) for arr in residuals_nm.values())

        ref_im = axes[row_idx, 0].imshow(h_true_nm, cmap=ref_cmap, vmin=-ref_lim, vmax=ref_lim, origin="lower")
        axes[row_idx, 0].set_ylabel(f"{category}\n{_surface_name(stem)}")

        for col_idx, key in enumerate(residual_keys, start=1):
            res_im = axes[row_idx, col_idx].imshow(
                residuals_nm[key],
                cmap=res_cmap,
                vmin=-res_lim,
                vmax=res_lim,
                origin="lower",
            )

        for ax in axes[row_idx, :]:
            ax.set_xticks([])
            ax.set_yticks([])

    if ref_im is not None:
        fig.colorbar(ref_im, ax=axes[:, 0], fraction=0.046, pad=0.02, label="Height (nm)")
    if res_im is not None:
        fig.colorbar(res_im, ax=axes[:, 1:], fraction=0.034, pad=0.02, label="Residual (nm)")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.out)
    plt.close(fig)
    print(f"Wrote: {args.out}")


if __name__ == "__main__":
    main()