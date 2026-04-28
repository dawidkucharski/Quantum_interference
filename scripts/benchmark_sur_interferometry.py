from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import csv
from dataclasses import asdict
from dataclasses import dataclass
import os
from pathlib import Path
import sys
from typing import Dict, Iterable, List, Optional, Tuple
import zlib

import numpy as np

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "src"))

from qiprof.metrics import detrend_plane, roughness_errors, roughness_metrics
from qiprof.reconstruct import (
    height_from_phase,
    normalize_frames_mean,
    reconstruct_phase_lsq,
    reconstruct_psi4,
    unwrap_phase_2d,
    unwrap_height_with_coarse,
)
from qiprof.sim_classical import simulate_psi4
from qiprof.sim_quantum import effective_wavelength, simulate_coincidence_psi4
from qiprof.surfaces import load_surface_sur, roughness_metrics_sur_reference
from qiprof.labels import decode_sur_stem


def _rmse_nm(a_m: np.ndarray, b_m: np.ndarray, *, valid_mask: Optional[np.ndarray]) -> float:
    a = detrend_plane(a_m, valid_mask=valid_mask)
    b = detrend_plane(b_m, valid_mask=valid_mask)
    if valid_mask is None:
        msk = np.isfinite(a) & np.isfinite(b)
    else:
        msk = valid_mask & np.isfinite(a) & np.isfinite(b)
    return float(np.sqrt(np.mean(((a - b)[msk]) ** 2)) * 1e9)


def _decode_label(stem: str) -> Dict[str, str]:
    label = decode_sur_stem(stem)
    return {
        "sample_group": label.sample_group,
        "material_code": label.material_code,
        "treatment_code": label.treatment_code,
        "material": label.material_en,
        "treatment": label.treatment_en,
    }


def _iter_inputs(patterns: List[str]) -> List[Path]:
    paths: List[Path] = []
    for pat in patterns:
        p = Path(pat)
        if p.exists():
            paths.append(p)
        else:
            paths.extend(sorted(Path().glob(pat)))

    # de-duplicate
    seen: set[Path] = set()
    out: List[Path] = []
    for p in paths:
        rp = p.resolve()
        if rp not in seen:
            out.append(p)
            seen.add(rp)
    return out


def _write_csv(path: Path, rows: List[Dict[str, object]], fieldnames: Optional[List[str]] = None) -> None:
    if fieldnames is None:
        keys = {k for r in rows for k in r.keys()}
        fieldnames = sorted(keys)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def _group_summary(
    rows: Iterable[Dict[str, object]],
    *,
    group_key: str,
    metric_keys: List[str],
) -> List[Dict[str, object]]:
    groups: Dict[Tuple[str, str], List[Dict[str, object]]] = {}
    for r in rows:
        g = str(r.get(group_key, ""))
        method = str(r.get("method", ""))
        groups.setdefault((g, method), []).append(r)

    out: List[Dict[str, object]] = []
    for (g, method), rs in sorted(groups.items(), key=lambda t: (t[0][0], t[0][1])):
        row: Dict[str, object] = {group_key: g, "method": method, "n": len(rs)}
        for mk in metric_keys:
            vals = [float(x) for x in (r.get(mk) for r in rs) if x not in (None, "")]
            if len(vals) == 0:
                row[f"{mk}_mean"] = ""
                row[f"{mk}_std"] = ""
            else:
                row[f"{mk}_mean"] = float(np.mean(vals))
                row[f"{mk}_std"] = float(np.std(vals, ddof=1)) if len(vals) >= 2 else 0.0
        out.append(row)
    return out


METHOD_ORDER = {"classical": 0, "quantum_like": 1, "hybrid": 2}


@dataclass(frozen=True)
class BenchmarkConfig:
    nx: int
    ny: int
    nreps: int
    sur_resample: str
    recon: str
    normalize_frames: bool
    unwrap_method: str
    lambda_class_m: float
    lambda1_m: float
    lambda2_m: float
    lambda_eff_m: float
    class_photons: float
    class_visibility: float
    quant_interferometer: str
    quant_detector_model: str
    quant_target_mean_counts: float
    quant_pairs: float
    gate_time_s: float
    pair_rate_hz: float
    phase_step_error_sigma_rad: float
    background_drift_frac: float
    amplitude_drift_frac: float
    roughness_s_filter_m: float
    roughness_l_filter_m: float
    eta1: float
    eta2: float
    dark1_hz: float
    dark2_hz: float
    tau_c_s: float
    deadtime1_s: float
    deadtime2_s: float
    su11_gain: float
    hybrid_smooth_sigma_px: float
    phase_steps_rad: Tuple[float, ...]


def _stable_seed(stem: str, rep: int) -> int:
    return (zlib.crc32(stem.encode("utf-8")) + int(rep)) & 0xFFFFFFFF


def _process_surface(path_str: str, config: BenchmarkConfig) -> List[Dict[str, object]]:
    p = Path(path_str)
    stem = p.stem
    decoded = _decode_label(stem)
    surface = load_surface_sur(
        p,
        target_nx=int(config.nx),
        target_ny=int(config.ny),
        resample=str(config.sur_resample),
    )
    valid_mask = getattr(surface, "valid_mask", None)
    h_true = detrend_plane(surface.h, valid_mask=valid_mask)
    if valid_mask is not None and bool(np.any(valid_mask)):
        fill = float(np.nanmedian(h_true[valid_mask]))
        h_true = np.where(valid_mask, h_true, fill)

    dx = float(np.mean(np.diff(surface.x))) if surface.x.size >= 2 else 1.0
    dy = float(np.mean(np.diff(surface.y))) if surface.y.size >= 2 else 1.0

    true_m_native = roughness_metrics_sur_reference(p)
    true_m_bw = roughness_metrics(surface.h, valid_mask=valid_mask)
    true_m_iso = None
    if float(config.roughness_s_filter_m) > 0.0 or float(config.roughness_l_filter_m) > 0.0:
        true_m_iso = roughness_metrics(
            surface.h,
            valid_mask=valid_mask,
            dx=dx,
            dy=dy,
            s_filter_m=float(config.roughness_s_filter_m),
            l_filter_m=float(config.roughness_l_filter_m),
        )
    pair_rate_hz = None
    if str(config.quant_detector_model) == "rates":
        pair_rate_hz = (
            float(config.pair_rate_hz)
            if float(config.pair_rate_hz) > 0
            else float(config.quant_pairs) / float(config.gate_time_s)
        )

    rows: List[Dict[str, object]] = []
    phase_steps = np.array(config.phase_steps_rad, dtype=float)
    for rep in range(int(config.nreps)):
        class_seed = _stable_seed(f"{stem}:classical", rep)
        quant_seed = _stable_seed(f"{stem}:quantum", rep)

        I4 = simulate_psi4(
            h_true,
            wavelength_m=float(config.lambda_class_m),
            photons_per_pixel=float(config.class_photons),
            visibility=float(config.class_visibility),
            phase_step_error_sigma_rad=float(config.phase_step_error_sigma_rad),
            background_drift_frac=float(config.background_drift_frac),
            amplitude_drift_frac=float(config.amplitude_drift_frac),
            seed=class_seed,
        )
        if config.recon == "lsq":
            I4r = normalize_frames_mean(I4) if bool(config.normalize_frames) else I4
            phi_w = reconstruct_phase_lsq(I4r, phase_steps_rad=phase_steps)
        else:
            phi_w = reconstruct_psi4(I4)
        phi_u = unwrap_phase_2d(phi_w, method=str(config.unwrap_method))
        h_class = height_from_phase(phi_u, wavelength_m=float(config.lambda_class_m))

        C4 = simulate_coincidence_psi4(
            h_true,
            lambda1_m=float(config.lambda1_m),
            lambda2_m=float(config.lambda2_m),
            visibility=0.6,
            background=1.0,
            amplitude=1.0,
            pairs_per_pixel=float(config.quant_pairs),
            interferometer=str(config.quant_interferometer),
            detector_model=str(config.quant_detector_model),
            gate_time_s=float(config.gate_time_s),
            pair_rate_hz=pair_rate_hz,
            eta1=float(config.eta1),
            eta2=float(config.eta2),
            dark1_hz=float(config.dark1_hz),
            dark2_hz=float(config.dark2_hz),
            tau_c_s=float(config.tau_c_s),
            deadtime1_s=float(config.deadtime1_s),
            deadtime2_s=float(config.deadtime2_s),
            target_mean_counts_per_pixel=(
                float(config.quant_target_mean_counts) if float(config.quant_target_mean_counts) > 0 else None
            ),
            su11_gain=float(config.su11_gain),
            phase_step_error_sigma_rad=float(config.phase_step_error_sigma_rad),
            background_drift_frac=float(config.background_drift_frac),
            amplitude_drift_frac=float(config.amplitude_drift_frac),
            seed=quant_seed,
        )
        if config.recon == "lsq":
            C4r = normalize_frames_mean(C4) if bool(config.normalize_frames) else C4
            phi_qw = reconstruct_phase_lsq(C4r, phase_steps_rad=phase_steps)
        else:
            phi_qw = reconstruct_psi4(C4)
        phi_qu = unwrap_phase_2d(phi_qw, method=str(config.unwrap_method))
        h_quant = height_from_phase(phi_qu, wavelength_m=float(config.lambda_eff_m))

        h_hybrid = unwrap_height_with_coarse(
            phi_w,
            coarse_height_m=h_quant,
            wavelength_short_m=float(config.lambda_class_m),
            coarse_smooth_sigma_px=float(config.hybrid_smooth_sigma_px),
        )

        methods = {
            "classical": h_class,
            "quantum_like": h_quant,
            "hybrid": h_hybrid,
        }

        for method, h_est in methods.items():
            m_est = roughness_metrics(h_est, valid_mask=valid_mask)
            errs_native = roughness_errors(m_est, true_m_native)
            errs_bw = roughness_errors(m_est, true_m_bw)
            if true_m_iso is not None:
                m_est_iso = roughness_metrics(
                    h_est,
                    valid_mask=valid_mask,
                    dx=dx,
                    dy=dy,
                    s_filter_m=float(config.roughness_s_filter_m),
                    l_filter_m=float(config.roughness_l_filter_m),
                )
                errs_iso = roughness_errors(m_est_iso, true_m_iso)
            else:
                errs_iso = None
            rows.append(
                {
                    "file": str(p.as_posix()),
                    "stem": stem,
                    **decoded,
                    "rep": int(rep),
                    "method": method,
                    "sur_resample": str(config.sur_resample),
                    "unwrap_method": str(config.unwrap_method),
                    "nx": int(surface.x.size),
                    "ny": int(surface.y.size),
                    "lambda_class_nm": float(config.lambda_class_m * 1e9),
                    "lambda1_nm": float(config.lambda1_m * 1e9),
                    "lambda2_nm": float(config.lambda2_m * 1e9),
                    "lambda_eff_nm": float(config.lambda_eff_m * 1e9),
                    "phase_step_sigma_deg": float(np.rad2deg(config.phase_step_error_sigma_rad)),
                    "background_drift_frac": float(config.background_drift_frac),
                    "amplitude_drift_frac": float(config.amplitude_drift_frac),
                    "deadtime1_s": float(config.deadtime1_s),
                    "deadtime2_s": float(config.deadtime2_s),
                    "Sa_true_nm": float(true_m_native.Sa * 1e9),
                    "Sq_true_nm": float(true_m_native.Sq * 1e9),
                    "Sz_true_nm": float(true_m_native.Sz * 1e9),
                    "Sa_true_bw_nm": float(true_m_bw.Sa * 1e9),
                    "Sq_true_bw_nm": float(true_m_bw.Sq * 1e9),
                    "Sz_true_bw_nm": float(true_m_bw.Sz * 1e9),
                    "Sa_true_iso_nm": float(true_m_iso.Sa * 1e9) if true_m_iso is not None else "",
                    "Sq_true_iso_nm": float(true_m_iso.Sq * 1e9) if true_m_iso is not None else "",
                    "Sz_true_iso_nm": float(true_m_iso.Sz * 1e9) if true_m_iso is not None else "",
                    "Sa_est_nm": float(m_est.Sa * 1e9),
                    "Sq_est_nm": float(m_est.Sq * 1e9),
                    "Sz_est_nm": float(m_est.Sz * 1e9),
                    "bias_Sa_nm": float(errs_native["bias_Sa"] * 1e9),
                    "bias_Sq_nm": float(errs_native["bias_Sq"] * 1e9),
                    "bias_Sz_nm": float(errs_native["bias_Sz"] * 1e9),
                    "bias_Sa_bw_nm": float(errs_bw["bias_Sa"] * 1e9),
                    "bias_Sq_bw_nm": float(errs_bw["bias_Sq"] * 1e9),
                    "bias_Sz_bw_nm": float(errs_bw["bias_Sz"] * 1e9),
                    "bias_Sa_iso_nm": float(errs_iso["bias_Sa"] * 1e9) if errs_iso is not None else "",
                    "bias_Sq_iso_nm": float(errs_iso["bias_Sq"] * 1e9) if errs_iso is not None else "",
                    "bias_Sz_iso_nm": float(errs_iso["bias_Sz"] * 1e9) if errs_iso is not None else "",
                    "height_rmse_nm": _rmse_nm(h_est, h_true, valid_mask=valid_mask),
                }
            )
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Benchmark classical vs quantum-like vs hybrid interferometry reconstruction on measured .sur surfaces"
    )
    ap.add_argument("inputs", nargs="*", default=["data/*.sur"], help="SUR files or glob patterns")
    ap.add_argument("--outdir", type=str, default="outputs/sur_benchmark")
    ap.add_argument("--nx", type=int, default=256)
    ap.add_argument("--ny", type=int, default=256)
    ap.add_argument("--nreps", type=int, default=1, help="Monte-Carlo repetitions per surface")
    ap.add_argument(
        "--sur-resample",
        type=str,
        choices=["area", "index"],
        default="area",
        help="How the native .sur grid is reduced to the benchmark grid.",
    )
    ap.add_argument("--recon", type=str, choices=["psi4", "lsq"], default="psi4")
    ap.add_argument("--normalize-frames", action="store_true")
    ap.add_argument("--unwrap-method", type=str, choices=["simple", "least_squares"], default="simple")
    ap.add_argument("--lambda-class-nm", type=float, default=532.0)
    ap.add_argument("--class-photons", type=float, default=8e4)
    ap.add_argument("--class-visibility", type=float, default=0.85)

    ap.add_argument("--lambda1-nm", type=float, default=810.0)
    ap.add_argument("--lambda2-nm", type=float, default=809.0)
    ap.add_argument(
        "--quant-interferometer",
        type=str,
        choices=["diff", "sum", "noon2", "su11"],
        default="diff",
    )
    ap.add_argument("--quant-detector-model", type=str, choices=["simple", "rates"], default="simple")
    ap.add_argument("--quant-target-mean-counts", type=float, default=0.0)
    ap.add_argument("--quant-pairs", type=float, default=3e4)
    ap.add_argument("--gate-time-s", type=float, default=1.0)
    ap.add_argument("--pair-rate-hz", type=float, default=0.0)
    ap.add_argument("--phase-step-sigma-deg", type=float, default=0.0)
    ap.add_argument("--background-drift-frac", type=float, default=0.0)
    ap.add_argument("--amplitude-drift-frac", type=float, default=0.0)
    ap.add_argument("--roughness-s-filter-um", type=float, default=0.0)
    ap.add_argument("--roughness-l-filter-um", type=float, default=0.0)
    ap.add_argument("--eta1", type=float, default=1.0)
    ap.add_argument("--eta2", type=float, default=1.0)
    ap.add_argument("--dark1-hz", type=float, default=0.0)
    ap.add_argument("--dark2-hz", type=float, default=0.0)
    ap.add_argument("--tau-c-s", type=float, default=1e-6)
    ap.add_argument("--deadtime1-s", type=float, default=0.0)
    ap.add_argument("--deadtime2-s", type=float, default=0.0)
    ap.add_argument("--su11-gain", type=float, default=0.0)

    ap.add_argument("--hybrid-smooth-sigma-px", type=float, default=1.5)
    ap.add_argument(
        "--jobs",
        type=int,
        default=0,
        help="Parallel workers across surfaces; 0 uses up to 4 workers automatically, 1 keeps serial execution.",
    )
    ap.add_argument("--limit", type=int, default=0, help="If >0, process at most this many surfaces")

    args = ap.parse_args()
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    paths = _iter_inputs(list(args.inputs))
    if int(args.limit) > 0:
        paths = paths[: int(args.limit)]

    lam_class = float(args.lambda_class_nm) * 1e-9
    lam1 = float(args.lambda1_nm) * 1e-9
    lam2 = float(args.lambda2_nm) * 1e-9
    lam_eff = effective_wavelength(
        interferometer=str(args.quant_interferometer),
        lambda1_m=float(lam1),
        lambda2_m=float(lam2),
    )

    phase_steps = np.array([0.0, 0.5 * np.pi, np.pi, 1.5 * np.pi], dtype=float)
    config = BenchmarkConfig(
        nx=int(args.nx),
        ny=int(args.ny),
        nreps=int(args.nreps),
        sur_resample=str(args.sur_resample),
        recon=str(args.recon),
        normalize_frames=bool(args.normalize_frames),
        unwrap_method=str(args.unwrap_method),
        lambda_class_m=float(lam_class),
        lambda1_m=float(lam1),
        lambda2_m=float(lam2),
        lambda_eff_m=float(lam_eff),
        class_photons=float(args.class_photons),
        class_visibility=float(args.class_visibility),
        quant_interferometer=str(args.quant_interferometer),
        quant_detector_model=str(args.quant_detector_model),
        quant_target_mean_counts=float(args.quant_target_mean_counts),
        quant_pairs=float(args.quant_pairs),
        gate_time_s=float(args.gate_time_s),
        pair_rate_hz=float(args.pair_rate_hz),
        phase_step_error_sigma_rad=float(np.deg2rad(args.phase_step_sigma_deg)),
        background_drift_frac=float(args.background_drift_frac),
        amplitude_drift_frac=float(args.amplitude_drift_frac),
        roughness_s_filter_m=float(args.roughness_s_filter_um) * 1e-6,
        roughness_l_filter_m=float(args.roughness_l_filter_um) * 1e-6,
        eta1=float(args.eta1),
        eta2=float(args.eta2),
        dark1_hz=float(args.dark1_hz),
        dark2_hz=float(args.dark2_hz),
        tau_c_s=float(args.tau_c_s),
        deadtime1_s=float(args.deadtime1_s),
        deadtime2_s=float(args.deadtime2_s),
        su11_gain=float(args.su11_gain),
        hybrid_smooth_sigma_px=float(args.hybrid_smooth_sigma_px),
        phase_steps_rad=tuple(float(v) for v in phase_steps),
    )

    per_surface: List[Dict[str, object]] = []
    path_strings = [str(p) for p in paths]
    requested_jobs = int(args.jobs)
    max_workers = 1
    if len(path_strings) > 1:
        if requested_jobs <= 0:
            max_workers = min(len(path_strings), os.cpu_count() or 1, 4)
        else:
            max_workers = min(len(path_strings), requested_jobs)

    if max_workers <= 1:
        for idx, path_str in enumerate(path_strings, start=1):
            per_surface.extend(_process_surface(path_str, config))
            print(f"[{idx}/{len(path_strings)}] {Path(path_str).name}", flush=True)
    else:
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            future_to_path = {executor.submit(_process_surface, path_str, config): path_str for path_str in path_strings}
            for idx, future in enumerate(as_completed(future_to_path), start=1):
                path_str = future_to_path[future]
                per_surface.extend(future.result())
                print(f"[{idx}/{len(path_strings)}] {Path(path_str).name}", flush=True)

    per_surface.sort(
        key=lambda row: (
            str(row.get("stem", "")),
            int(row.get("rep", 0)),
            METHOD_ORDER.get(str(row.get("method", "")), 99),
        )
    )

    per_csv = outdir / "per_surface.csv"
    _write_csv(per_csv, per_surface)

    metric_keys = ["height_rmse_nm", "bias_Sa_nm", "bias_Sq_nm", "bias_Sz_nm"]
    by_material = _group_summary(per_surface, group_key="material", metric_keys=metric_keys)
    by_treatment = _group_summary(per_surface, group_key="treatment", metric_keys=metric_keys)
    _write_csv(outdir / "by_material.csv", by_material)
    _write_csv(outdir / "by_treatment.csv", by_treatment)

    print(f"Wrote: {per_csv}")
    print(f"Wrote: {outdir / 'by_material.csv'}")
    print(f"Wrote: {outdir / 'by_treatment.csv'}")


if __name__ == "__main__":
    main()
