from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Iterable, Optional

import matplotlib.pyplot as plt
import matplotlib as mpl
import numpy as np

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "src"))

from qiprof.plot_style import apply_publication_style


_FIGSIZE_OVERRIDE_IN: Optional[tuple[float, float]] = None
_SAVE_TIGHT_BBOX: bool = True
_FIGSIZE_SCALE: float = 1.0

_LINE_WIDTH: Optional[float] = None
_LINE_ALPHA: Optional[float] = None
_MARKER_SIZE: Optional[float] = None
_CAPSIZE: Optional[float] = None
_SCATTER_ALPHA: Optional[float] = None
_SCATTER_SIZE: Optional[float] = None


def _lw(default: float = 1.2) -> float:
    return float(_LINE_WIDTH) if _LINE_WIDTH is not None else float(default)


def _line_alpha(default: float = 1.0) -> float:
    return float(_LINE_ALPHA) if _LINE_ALPHA is not None else float(default)


def _ms(default: float = 3.5) -> float:
    return float(_MARKER_SIZE) if _MARKER_SIZE is not None else float(default)


def _caps(default: float = 2.5) -> float:
    return float(_CAPSIZE) if _CAPSIZE is not None else float(default)


def _scatter_alpha(default: float = 0.30) -> float:
    return float(_SCATTER_ALPHA) if _SCATTER_ALPHA is not None else float(default)


def _scatter_size(default: float = 10.0) -> float:
    return float(_SCATTER_SIZE) if _SCATTER_SIZE is not None else float(default)


@dataclass(frozen=True)
class SweepRow:
    method: str
    step_nm: float
    rms_nm: float
    sample_reflectivity: Optional[float]
    sample_visibility_scale: Optional[float]
    coherence_model: Optional[str]
    incidence_cos: Optional[float]
    lambda_class_nm: Optional[float]
    lambda1_nm: Optional[float]
    lambda2_nm: Optional[float]
    phase_step_sigma_deg: float
    background_drift_frac: float
    amplitude_drift_frac: float
    normalize_frames: Optional[int]
    hybrid_smooth_sigma_px: Optional[float]
    recon: Optional[str]
    rep: int
    lambda_eff_um: Optional[float]
    rmse_h_nm: float
    bias_Sa_nm: float
    bias_Sq_nm: float
    bias_Sz_nm: float
    step_est_nm: Optional[float]
    step_err_nm: Optional[float]


def _to_float(x: str) -> float:
    return float(x.strip())


def _to_int(x: str) -> int:
    return int(float(x.strip()))


def read_sweep_csv(path: Path) -> list[SweepRow]:
    rows: list[SweepRow] = []
    with open(path, "r", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for d in r:
            def opt_float(key: str) -> Optional[float]:
                if key not in d:
                    return None
                v = d[key]
                if v in (None, ""):
                    return None
                return _to_float(v)

            def opt_int(key: str) -> Optional[int]:
                if key not in d:
                    return None
                v = d[key]
                if v in (None, ""):
                    return None
                return _to_int(v)

            lam_eff_um = None
            if "lambda_eff_um" in d and d["lambda_eff_um"] not in (None, ""):
                lam_eff_um = _to_float(d["lambda_eff_um"])

            rows.append(
                SweepRow(
                    method=str(d["method"]),
                    step_nm=_to_float(d["step_nm"]),
                    rms_nm=_to_float(d["rms_nm"]),
                    sample_reflectivity=opt_float("sample_reflectivity"),
                    sample_visibility_scale=opt_float("sample_visibility_scale"),
                    coherence_model=str(d["coherence_model"]) if "coherence_model" in d and d["coherence_model"] not in (None, "") else None,
                    incidence_cos=opt_float("incidence_cos"),
                    lambda_class_nm=opt_float("lambda_class_nm"),
                    lambda1_nm=opt_float("lambda1_nm"),
                    lambda2_nm=opt_float("lambda2_nm"),
                    phase_step_sigma_deg=_to_float(d.get("phase_step_sigma_deg", "0")),
                    background_drift_frac=_to_float(d.get("background_drift_frac", "0")),
                    amplitude_drift_frac=_to_float(d.get("amplitude_drift_frac", "0")),
                    normalize_frames=opt_int("normalize_frames"),
                    hybrid_smooth_sigma_px=opt_float("hybrid_smooth_sigma_px"),
                    recon=str(d["recon"]) if "recon" in d and d["recon"] not in (None, "") else None,
                    rep=_to_int(d["rep"]),
                    lambda_eff_um=lam_eff_um,
                    rmse_h_nm=_to_float(d["rmse_h_nm"]),
                    bias_Sa_nm=_to_float(d["bias_Sa_nm"]),
                    bias_Sq_nm=_to_float(d["bias_Sq_nm"]),
                    bias_Sz_nm=_to_float(d["bias_Sz_nm"]),
                    step_est_nm=opt_float("step_est_nm"),
                    step_err_nm=opt_float("step_err_nm"),
                )
            )
    return rows


def discover_sweep_csvs(inputs: list[str]) -> list[Path]:
    paths: list[Path] = []
    for s in inputs:
        p = Path(s)
        if p.is_file() and p.name.lower().endswith(".csv"):
            paths.append(p)
        elif p.is_dir():
            paths.extend(sorted(p.rglob("sweep.csv")))
        else:
            # allow glob-like patterns via rglob fallback
            base = p.parent if p.parent.exists() else Path(".")
            paths.extend(sorted(base.rglob(p.name)))

    # de-dup preserve order
    out: list[Path] = []
    seen: set[Path] = set()
    for p in paths:
        rp = p.resolve()
        if rp not in seen:
            out.append(rp)
            seen.add(rp)
    return out


def apply_mdpi_style(*, base_fontsize: float = 9.0) -> None:
    apply_publication_style(base_fontsize=base_fontsize)


def apply_photonics_style() -> None:
    """MDPI Photonics-friendly styling.

    Photonics typically accepts the same general MDPI figure requirements.
    We target slightly smaller default text and ensure vector exports keep editable text.
    """

    apply_publication_style(base_fontsize=8.5)


def apply_photonics_style_with_fontsize(*, base_fontsize: float) -> None:
    apply_mdpi_style(base_fontsize=base_fontsize)


def fig_size(layout: str, *, style: str) -> tuple[float, float]:
    """Return figure size in inches for common publication layouts.

    - onecol: ~8.5 cm wide
    - twocol: ~17.5 cm wide
    """

    def _scale(sz: tuple[float, float]) -> tuple[float, float]:
        s = float(_FIGSIZE_SCALE)
        return (sz[0] * s, sz[1] * s)

    if _FIGSIZE_OVERRIDE_IN is not None:
        return _scale(_FIGSIZE_OVERRIDE_IN)

    # Approximate MDPI column widths:
    # - one column ~ 8.3 cm (3.27 in)
    # - two columns ~ 17.2 cm (6.77 in)
    if style == "photonics":
        if layout == "onecol":
            return _scale((3.27, 2.35))
        if layout == "twocol":
            return _scale((6.77, 4.10))

    if layout == "onecol":
        return _scale((3.35, 2.4))
    if layout == "twocol":
        return _scale((6.9, 4.2))
    raise ValueError("layout must be 'onecol' or 'twocol'")


def save_figure(path_base: Path, *, formats: list[str], dpi: int) -> None:
    for fmt in formats:
        fmt = fmt.lower().lstrip(".")
        out = path_base.with_suffix("." + fmt)
        if fmt in {"png", "jpg", "jpeg", "tif", "tiff"}:
            if _SAVE_TIGHT_BBOX:
                plt.savefig(out, dpi=dpi, bbox_inches="tight", pad_inches=0.08)
            else:
                plt.savefig(out, dpi=dpi)
        else:
            # Vector formats ignore dpi for primitives
            if _SAVE_TIGHT_BBOX:
                plt.savefig(out, bbox_inches="tight", pad_inches=0.08)
            else:
                plt.savefig(out)


def _finalize_legend_and_layout(*, n_methods: int, style: str) -> None:
    """Place legend outside (right) and apply a layout that keeps it visible.

    For publication-style figures with multiple methods, legends inside the axes often
    obscure data. This keeps the legend outside the plot box and reserves space.
    """

    ax = plt.gca()

    # Put legend outside for multi-method plots to avoid covering data.
    # IMPORTANT: we do NOT shrink the axes (no right-margin reservation). Instead we rely on
    # savefig(bbox_inches="tight") (set in rcParams) to expand the exported canvas to include
    # the legend while keeping the graph area large.
    legend_outside = n_methods > 1
    if legend_outside:
        if not _SAVE_TIGHT_BBOX:
            # If we keep a fixed canvas size (no tight bbox), reserve space for the legend.
            plt.subplots_adjust(right=0.74)
        ax.legend(
            loc="upper left",
            bbox_to_anchor=(1.0, 1.0),
            borderaxespad=0.0,
            frameon=False,
        )
    else:
        ax.legend(loc="best", frameon=False)
    plt.tight_layout(pad=0.6)


def _scenario_key(r: SweepRow) -> tuple:
    """A key for a single sweep scenario (everything except method/step/rep/metrics)."""

    return (
        r.rms_nm,
        r.sample_reflectivity,
        r.sample_visibility_scale,
        r.coherence_model,
        r.incidence_cos,
        r.lambda_class_nm,
        r.lambda1_nm,
        r.lambda2_nm,
        r.phase_step_sigma_deg,
        r.background_drift_frac,
        r.amplitude_drift_frac,
        r.normalize_frames,
        r.hybrid_smooth_sigma_px,
        r.recon,
    )


def _scenario_key_rms_sweep(r: SweepRow) -> tuple:
    """Scenario key for plotting vs RMS (exclude rms_nm; keep step fixed)."""

    return (
        r.step_nm,
        r.sample_reflectivity,
        r.sample_visibility_scale,
        r.coherence_model,
        r.incidence_cos,
        r.lambda_class_nm,
        r.lambda1_nm,
        r.lambda2_nm,
        r.phase_step_sigma_deg,
        r.background_drift_frac,
        r.amplitude_drift_frac,
        r.normalize_frames,
        r.hybrid_smooth_sigma_px,
        r.recon,
    )


def _scenario_key_lambda_sweep(r: SweepRow) -> tuple:
    """Scenario key for plotting vs synthetic wavelength (exclude lambda1/lambda2/eff)."""

    return (
        r.step_nm,
        r.rms_nm,
        r.sample_reflectivity,
        r.sample_visibility_scale,
        r.coherence_model,
        r.incidence_cos,
        r.lambda_class_nm,
        r.phase_step_sigma_deg,
        r.background_drift_frac,
        r.amplitude_drift_frac,
        r.normalize_frames,
        r.hybrid_smooth_sigma_px,
        r.recon,
    )


def _choose_most_common_scenario(rows: list[SweepRow]) -> Optional[tuple]:
    if not rows:
        return None
    counts: dict[tuple, int] = {}
    for r in rows:
        k = _scenario_key(r)
        counts[k] = counts.get(k, 0) + 1
    return max(counts.items(), key=lambda kv: kv[1])[0]


def _choose_most_common_key(rows: list[SweepRow], key_fn) -> Optional[tuple]:
    if not rows:
        return None
    counts: dict[tuple, int] = {}
    for r in rows:
        k = key_fn(r)
        counts[k] = counts.get(k, 0) + 1
    return max(counts.items(), key=lambda kv: kv[1])[0]


def _top_keys(rows: list[SweepRow], key_fn, *, max_keys: int) -> list[tuple]:
    if max_keys <= 0:
        return []
    counts: dict[tuple, int] = {}
    for r in rows:
        k = key_fn(r)
        counts[k] = counts.get(k, 0) + 1
    keys_sorted = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    return [k for k, _ in keys_sorted[:max_keys]]


def _write_scenarios_csv(*, outdir: Path, name: str, scenario_rows: list[tuple[str, SweepRow]]) -> None:
    """Write a mapping from scenario id -> parameter knobs.

    scenario_rows: list of (scenario_id, representative_row)
    """

    out_path = outdir / name
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "scenario",
                "step_nm",
                "rms_nm",
                "lambda_class_nm",
                "lambda1_nm",
                "lambda2_nm",
                "lambda_eff_um",
                "phase_step_sigma_deg",
                "background_drift_frac",
                "amplitude_drift_frac",
                "normalize_frames",
                "hybrid_smooth_sigma_px",
                "recon",
            ]
        )
        for sid, r in scenario_rows:
            w.writerow(
                [
                    sid,
                    r.step_nm,
                    r.rms_nm,
                    r.lambda_class_nm,
                    r.lambda1_nm,
                    r.lambda2_nm,
                    r.lambda_eff_um,
                    r.phase_step_sigma_deg,
                    r.background_drift_frac,
                    r.amplitude_drift_frac,
                    r.normalize_frames,
                    r.hybrid_smooth_sigma_px,
                    r.recon,
                ]
            )


def _aggregate(rows: Iterable[SweepRow], *, y: str) -> dict[tuple, dict[str, tuple[np.ndarray, np.ndarray]]]:
    """Return mapping group_key -> method -> (x, yvals) where x is reps index."""

    groups: dict[tuple, dict[str, list[float]]] = {}
    for r in rows:
        gk = _scenario_key(r)
        groups.setdefault(gk, {}).setdefault(r.method, []).append(getattr(r, y))

    out: dict[tuple, dict[str, tuple[np.ndarray, np.ndarray]]] = {}
    for gk, by_method in groups.items():
        out[gk] = {}
        for method, vals in by_method.items():
            yv = np.array(vals, dtype=float)
            xv = np.arange(yv.size, dtype=float)
            out[gk][method] = (xv, yv)
    return out


def _mean_std(y: np.ndarray) -> tuple[float, float]:
    if y.size == 0:
        return float("nan"), float("nan")
    return float(np.nanmean(y)), float(np.nanstd(y))


def plot_rmse_vs_step(
    rows: list[SweepRow],
    outdir: Path,
    *,
    scenarios: list[tuple],
    layout: str,
    style: str,
    formats: list[str],
    dpi: int,
) -> None:
    if not scenarios:
        return

    for i, scenario in enumerate(scenarios, start=1):
        rows_s = [r for r in rows if _scenario_key(r) == scenario]
        if not rows_s:
            continue

        methods = sorted({r.method for r in rows_s})
        steps = sorted({r.step_nm for r in rows_s})
        if len(steps) < 2:
            continue

        plt.figure(figsize=fig_size(layout, style=style))
        for method in methods:
            means = []
            stds = []
            for step in steps:
                ys = np.array([r.rmse_h_nm for r in rows_s if r.method == method and r.step_nm == step], dtype=float)
                m, s = _mean_std(ys)
                means.append(m)
                stds.append(s)

            means = np.array(means)
            stds = np.array(stds)
            plt.errorbar(
                steps,
                means,
                yerr=stds,
                marker="o",
                alpha=_line_alpha(1.0),
                linewidth=_lw(1.15),
                elinewidth=_lw(1.0),
                capsize=_caps(2.5),
                markersize=_ms(3.2),
                label=method,
            )

        plt.xlabel("Step height (nm)")
        plt.ylabel("Height RMSE after plane detrend (nm)")
        plt.yscale("log")
        plt.grid(True, which="both", alpha=0.25)
        _finalize_legend_and_layout(n_methods=len(methods), style=style)
        save_figure(outdir / f"rmse_vs_step__sc{i:02d}", formats=formats, dpi=dpi)
        plt.close()


def plot_bias_vs_step(
    rows: list[SweepRow],
    outdir: Path,
    *,
    scenarios: list[tuple],
    metric: str,
    layout: str,
    style: str,
    formats: list[str],
    dpi: int,
) -> None:
    if not scenarios:
        return

    col = {
        "Sa": "bias_Sa_nm",
        "Sq": "bias_Sq_nm",
        "Sz": "bias_Sz_nm",
    }[metric]

    for i, scenario in enumerate(scenarios, start=1):
        rows_s = [r for r in rows if _scenario_key(r) == scenario]
        if not rows_s:
            continue

        methods = sorted({r.method for r in rows_s})
        steps = sorted({r.step_nm for r in rows_s})
        if len(steps) < 2:
            continue

        plt.figure(figsize=fig_size(layout, style=style))
        for method in methods:
            means = []
            stds = []
            for step in steps:
                ys = np.array([getattr(r, col) for r in rows_s if r.method == method and r.step_nm == step], dtype=float)
                m, s = _mean_std(ys)
                means.append(m)
                stds.append(s)

            means = np.array(means)
            stds = np.array(stds)
            plt.errorbar(
                steps,
                means,
                yerr=stds,
                marker="o",
                alpha=_line_alpha(1.0),
                linewidth=_lw(1.15),
                elinewidth=_lw(1.0),
                capsize=_caps(2.5),
                markersize=_ms(3.2),
                label=method,
            )

        plt.axhline(0.0, color="k", linewidth=1.0, alpha=0.5)
        plt.xlabel("Step height (nm)")
        plt.ylabel(f"Bias in {metric} (nm)")
        plt.grid(True, alpha=0.25)
        _finalize_legend_and_layout(n_methods=len(methods), style=style)
        save_figure(outdir / f"bias_{metric}_vs_step__sc{i:02d}", formats=formats, dpi=dpi)
        plt.close()


def plot_rmse_vs_lambda_eff(
    rows: list[SweepRow],
    outdir: Path,
    *,
    scenarios: list[tuple],
    layout: str,
    style: str,
    formats: list[str],
    dpi: int,
) -> None:
    rows0 = [r for r in rows if r.lambda_eff_um is not None]
    if not scenarios:
        return

    for i, scenario in enumerate(scenarios, start=1):
        rows_l = [r for r in rows0 if _scenario_key_lambda_sweep(r) == scenario]
        if not rows_l:
            continue

        lam_vals = sorted({r.lambda_eff_um for r in rows_l if r.lambda_eff_um is not None})
        if len(lam_vals) < 2:
            continue

        methods = sorted({r.method for r in rows_l})

        plt.figure(figsize=fig_size(layout, style=style))
        for method in methods:
            x = np.array([r.lambda_eff_um for r in rows_l if r.method == method], dtype=float)
            y = np.array([r.rmse_h_nm for r in rows_l if r.method == method], dtype=float)
            if x.size == 0:
                continue
            plt.scatter(x, y, s=_scatter_size(10.0), alpha=_scatter_alpha(0.30), label=method)

        plt.xlabel("Synthetic wavelength $\\Lambda$ (µm)")
        plt.ylabel("Height RMSE after plane detrend (nm)")
        plt.yscale("log")
        plt.grid(True, which="both", alpha=0.25)
        _finalize_legend_and_layout(n_methods=len(methods), style=style)
        save_figure(outdir / f"rmse_vs_lambda_eff__sc{i:02d}", formats=formats, dpi=dpi)
        plt.close()


def plot_step_error_vs_step(
    rows: list[SweepRow],
    outdir: Path,
    *,
    scenarios: list[tuple],
    layout: str,
    style: str,
    formats: list[str],
    dpi: int,
) -> None:
    rows_e = [r for r in rows if r.step_err_nm is not None]
    if not rows_e:
        return

    if not scenarios:
        return

    for i, scenario in enumerate(scenarios, start=1):
        rows_s = [r for r in rows_e if _scenario_key(r) == scenario]
        if not rows_s:
            continue

        methods = sorted({r.method for r in rows_s})
        steps = sorted({r.step_nm for r in rows_s})
        if len(steps) < 2:
            continue

        plt.figure(figsize=fig_size(layout, style=style))
        for method in methods:
            means = []
            stds = []
            for step in steps:
                ys = np.array(
                    [
                        r.step_err_nm
                        for r in rows_s
                        if r.method == method and r.step_nm == step and r.step_err_nm is not None
                    ],
                    dtype=float,
                )
                m, s = _mean_std(ys)
                means.append(m)
                stds.append(s)

            means = np.array(means)
            stds = np.array(stds)
            plt.errorbar(
                steps,
                means,
                yerr=stds,
                marker="o",
                alpha=_line_alpha(1.0),
                linewidth=_lw(1.15),
                elinewidth=_lw(1.0),
                capsize=_caps(2.5),
                markersize=_ms(3.2),
                label=method,
            )

        plt.axhline(0.0, color="k", linewidth=1.0, alpha=0.5)
        plt.xlabel("Step height (nm)")
        plt.ylabel("Step-height error (nm)")
        plt.grid(True, alpha=0.25)
        _finalize_legend_and_layout(n_methods=len(methods), style=style)
        save_figure(outdir / f"step_err_vs_step__sc{i:02d}", formats=formats, dpi=dpi)
        plt.close()


def plot_rmse_vs_rms(
    rows: list[SweepRow],
    outdir: Path,
    *,
    scenarios: list[tuple],
    layout: str,
    style: str,
    formats: list[str],
    dpi: int,
) -> None:
    if not scenarios:
        return

    for i, scenario in enumerate(scenarios, start=1):
        rows_s = [r for r in rows if _scenario_key_rms_sweep(r) == scenario]
        if not rows_s:
            continue

        methods = sorted({r.method for r in rows_s})
        rms_vals = sorted({r.rms_nm for r in rows_s})
        if len(rms_vals) < 2:
            continue

        plt.figure(figsize=fig_size(layout, style=style))
        for method in methods:
            means = []
            stds = []
            for rms in rms_vals:
                ys = np.array([r.rmse_h_nm for r in rows_s if r.method == method and r.rms_nm == rms], dtype=float)
                m, s = _mean_std(ys)
                means.append(m)
                stds.append(s)
            plt.errorbar(
                rms_vals,
                means,
                yerr=stds,
                marker="o",
                alpha=_line_alpha(1.0),
                linewidth=_lw(1.15),
                elinewidth=_lw(1.0),
                capsize=_caps(2.5),
                markersize=_ms(3.2),
                label=method,
            )

        plt.xlabel("RMS roughness (nm)")
        plt.ylabel("Height RMSE after plane detrend (nm)")
        plt.yscale("log")
        plt.grid(True, which="both", alpha=0.25)
        _finalize_legend_and_layout(n_methods=len(methods), style=style)
        save_figure(outdir / f"rmse_vs_rms__sc{i:02d}", formats=formats, dpi=dpi)
        plt.close()


def plot_bias_vs_rms(
    rows: list[SweepRow],
    outdir: Path,
    *,
    scenarios: list[tuple],
    metric: str,
    layout: str,
    style: str,
    formats: list[str],
    dpi: int,
) -> None:
    if not scenarios:
        return

    col = {
        "Sa": "bias_Sa_nm",
        "Sq": "bias_Sq_nm",
        "Sz": "bias_Sz_nm",
    }[metric]

    for i, scenario in enumerate(scenarios, start=1):
        rows_s = [r for r in rows if _scenario_key_rms_sweep(r) == scenario]
        if not rows_s:
            continue

        methods = sorted({r.method for r in rows_s})
        rms_vals = sorted({r.rms_nm for r in rows_s})
        if len(rms_vals) < 2:
            continue

        plt.figure(figsize=fig_size(layout, style=style))
        for method in methods:
            means = []
            stds = []
            for rms in rms_vals:
                ys = np.array([getattr(r, col) for r in rows_s if r.method == method and r.rms_nm == rms], dtype=float)
                m, s = _mean_std(ys)
                means.append(m)
                stds.append(s)
            plt.errorbar(
                rms_vals,
                means,
                yerr=stds,
                marker="o",
                alpha=_line_alpha(1.0),
                linewidth=_lw(1.15),
                elinewidth=_lw(1.0),
                capsize=_caps(2.5),
                markersize=_ms(3.2),
                label=method,
            )

        plt.axhline(0.0, color="k", linewidth=1.0, alpha=0.5)
        plt.xlabel("RMS roughness (nm)")
        plt.ylabel(f"Bias in {metric} (nm)")
        plt.grid(True, alpha=0.25)
        _finalize_legend_and_layout(n_methods=len(methods), style=style)
        save_figure(outdir / f"bias_{metric}_vs_rms__sc{i:02d}", formats=formats, dpi=dpi)
        plt.close()


def write_summary_csv(rows: list[SweepRow], outdir: Path) -> None:
    # Summary per (method, step_nm, scenario knobs)
    key_to_vals: dict[tuple, list[SweepRow]] = {}
    for r in rows:
        k = (
            r.method,
            r.step_nm,
            r.rms_nm,
            r.sample_reflectivity,
            r.sample_visibility_scale,
            r.coherence_model,
            r.incidence_cos,
            r.lambda_class_nm,
            r.lambda1_nm,
            r.lambda2_nm,
            r.lambda_eff_um,
            r.phase_step_sigma_deg,
            r.background_drift_frac,
            r.amplitude_drift_frac,
            r.normalize_frames,
            r.hybrid_smooth_sigma_px,
            r.recon,
        )
        key_to_vals.setdefault(k, []).append(r)

    out_path = outdir / "summary.csv"
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "method",
                "step_nm",
                "rms_nm",
                "sample_reflectivity",
                "sample_visibility_scale",
                "coherence_model",
                "incidence_cos",
                "lambda_class_nm",
                "lambda1_nm",
                "lambda2_nm",
                "lambda_eff_um",
                "phase_step_sigma_deg",
                "background_drift_frac",
                "amplitude_drift_frac",
                "normalize_frames",
                "hybrid_smooth_sigma_px",
                "recon",
                "n",
                "rmse_h_nm_mean",
                "rmse_h_nm_std",
                "bias_Sa_nm_mean",
                "bias_Sa_nm_std",
                "bias_Sq_nm_mean",
                "bias_Sq_nm_std",
                "bias_Sz_nm_mean",
                "bias_Sz_nm_std",
                "step_err_nm_mean",
                "step_err_nm_std",
            ]
        )
        for k, vals in sorted(key_to_vals.items()):
            ys_rmse = np.array([v.rmse_h_nm for v in vals], dtype=float)
            ys_sa = np.array([v.bias_Sa_nm for v in vals], dtype=float)
            ys_sq = np.array([v.bias_Sq_nm for v in vals], dtype=float)
            ys_sz = np.array([v.bias_Sz_nm for v in vals], dtype=float)
            ys_step_err = np.array([v.step_err_nm for v in vals if v.step_err_nm is not None], dtype=float)
            w.writerow(
                [
                    k[0],
                    k[1],
                    k[2],
                    k[3],
                    k[4],
                    k[5],
                    k[6],
                    k[7],
                    k[8],
                    k[9],
                    k[10],
                    k[11],
                    k[12],
                    k[13],
                    k[14],
                    k[15],
                    k[16],
                    len(vals),
                    *_mean_std(ys_rmse),
                    *_mean_std(ys_sa),
                    *_mean_std(ys_sq),
                    *_mean_std(ys_sz),
                    *_mean_std(ys_step_err),
                ]
            )


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Plot paper-ready figures from one or more sweep.csv files or output folders."
    )
    ap.add_argument(
        "inputs",
        nargs="+",
        help="Paths to sweep.csv files or directories containing sweep.csv (searched recursively).",
    )
    ap.add_argument("--outdir", type=str, default="outputs/figures")
    ap.add_argument(
        "--style",
        type=str,
        choices=["default", "mdpi", "photonics"],
        default="photonics",
        help="Plot styling preset. 'photonics' targets MDPI Photonics defaults.",
    )
    ap.add_argument(
        "--base-fontsize",
        type=float,
        default=0.0,
        help="Override the base font size (pt). If 0, uses style default.",
    )
    ap.add_argument(
        "--layout",
        type=str,
        choices=["onecol", "twocol"],
        default="twocol",
        help="Target figure width: one-column or two-column.",
    )
    ap.add_argument(
        "--formats",
        type=str,
        default="png,pdf",
        help="Comma-separated output formats, e.g. 'png,pdf' or 'pdf,svg'.",
    )
    ap.add_argument(
        "--dpi",
        type=int,
        default=600,
        help="Raster DPI for png/tiff exports (MDPI commonly expects >=300 dpi).",
    )
    ap.add_argument(
        "--scale",
        type=float,
        default=1.0,
        help="Uniform scale factor applied to the figure canvas (useful for article visibility).",
    )
    ap.add_argument(
        "--figsize-in",
        type=float,
        nargs=2,
        default=None,
        metavar=("W_IN", "H_IN"),
        help="Override all figure sizes in inches (e.g., 6 4.8).",
    )
    ap.add_argument(
        "--figsize-px",
        type=str,
        default=None,
        help="Override raster figure size in pixels as 'W,H' or 'WxH' (e.g., 600x480). Disables tight bbox.",
    )
    ap.add_argument(
        "--fixed-canvas",
        action="store_true",
        help="Keep the figure canvas size fixed on export (disables bbox_inches='tight'). Useful for MDPI one-column PDFs.",
    )
    ap.add_argument("--line-width", type=float, default=0.0, help="Override line width for plotted curves.")
    ap.add_argument(
        "--line-alpha",
        type=float,
        default=0.0,
        help="Override alpha (transparency) for plotted curves and errorbars (0 means no override; typical: 0.6–0.9).",
    )
    ap.add_argument("--marker-size", type=float, default=0.0, help="Override marker size for plotted curves.")
    ap.add_argument("--capsize", type=float, default=0.0, help="Override errorbar cap size.")
    ap.add_argument(
        "--scatter-alpha",
        type=float,
        default=0.0,
        help="Override alpha for scatter plots (0 means style default).",
    )
    ap.add_argument(
        "--scatter-size",
        type=float,
        default=0.0,
        help="Override marker area for scatter plots (Matplotlib 's').",
    )
    ap.add_argument(
        "--max-scenarios",
        type=int,
        default=6,
        help="Plot up to this many distinct sweep scenarios (sorted by how many rows they contain).",
    )
    args = ap.parse_args()

    global _FIGSIZE_OVERRIDE_IN, _SAVE_TIGHT_BBOX, _FIGSIZE_SCALE
    if float(args.scale) <= 0:
        raise SystemExit("--scale must be > 0")
    _FIGSIZE_SCALE = float(args.scale)
    if args.figsize_in is not None:
        w_in, h_in = float(args.figsize_in[0]), float(args.figsize_in[1])
        if w_in <= 0 or h_in <= 0:
            raise SystemExit("--figsize-in must be positive")
        _FIGSIZE_OVERRIDE_IN = (w_in, h_in)

    if args.figsize_px is not None:
        s = str(args.figsize_px).lower().replace(" ", "")
        if "x" in s:
            a, b = s.split("x", 1)
        elif "," in s:
            a, b = s.split(",", 1)
        else:
            raise SystemExit("--figsize-px must look like '600x480' or '600,480'")
        w_px = float(a)
        h_px = float(b)
        if w_px <= 0 or h_px <= 0:
            raise SystemExit("--figsize-px must be positive")
        # Convert pixels to inches using dpi.
        _FIGSIZE_OVERRIDE_IN = (w_px / float(args.dpi), h_px / float(args.dpi))
        # Keep exact pixel dimensions; no tight bbox.
        _SAVE_TIGHT_BBOX = False

    if bool(args.fixed_canvas):
        _SAVE_TIGHT_BBOX = False

    global _LINE_WIDTH, _LINE_ALPHA, _MARKER_SIZE, _CAPSIZE, _SCATTER_ALPHA, _SCATTER_SIZE
    if float(args.line_width) > 0:
        _LINE_WIDTH = float(args.line_width)
    if float(args.line_alpha) > 0:
        a = float(args.line_alpha)
        if not (0.0 < a <= 1.0):
            raise SystemExit("--line-alpha must be in (0, 1]")
        _LINE_ALPHA = a
    if float(args.marker_size) > 0:
        _MARKER_SIZE = float(args.marker_size)
    if float(args.capsize) > 0:
        _CAPSIZE = float(args.capsize)
    if float(args.scatter_alpha) > 0:
        _SCATTER_ALPHA = float(args.scatter_alpha)
    if float(args.scatter_size) > 0:
        _SCATTER_SIZE = float(args.scatter_size)

    csvs = discover_sweep_csvs(args.inputs)
    if not csvs:
        raise SystemExit("No sweep.csv files found for given inputs")

    all_rows: list[SweepRow] = []
    for p in csvs:
        all_rows.extend(read_sweep_csv(p))

    if args.style == "mdpi":
        if float(args.base_fontsize) > 0:
            apply_mdpi_style(base_fontsize=float(args.base_fontsize))
        else:
            apply_mdpi_style()
    elif args.style == "photonics":
        if float(args.base_fontsize) > 0:
            apply_photonics_style_with_fontsize(base_fontsize=float(args.base_fontsize))
        else:
            apply_photonics_style()

    formats = [s.strip() for s in args.formats.split(",") if s.strip()]
    if not formats:
        raise SystemExit("--formats must include at least one format")

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    # Choose the most common scenarios for each plot family.
    scenarios_step = _top_keys(all_rows, _scenario_key, max_keys=int(args.max_scenarios))
    scenarios_rms = _top_keys(all_rows, _scenario_key_rms_sweep, max_keys=int(args.max_scenarios))
    scenarios_lambda = _top_keys(
        [r for r in all_rows if r.lambda_eff_um is not None], _scenario_key_lambda_sweep, max_keys=int(args.max_scenarios)
    )

    # Write scenario mappings (scenario index is the __scXX suffix).
    if scenarios_step:
        reps = [(f"sc{i:02d}", next(r for r in all_rows if _scenario_key(r) == k)) for i, k in enumerate(scenarios_step, 1)]
        _write_scenarios_csv(outdir=outdir, name="scenarios_step.csv", scenario_rows=reps)
    if scenarios_rms:
        reps = [(f"sc{i:02d}", next(r for r in all_rows if _scenario_key_rms_sweep(r) == k)) for i, k in enumerate(scenarios_rms, 1)]
        _write_scenarios_csv(outdir=outdir, name="scenarios_rms.csv", scenario_rows=reps)
    if scenarios_lambda:
        rows0 = [r for r in all_rows if r.lambda_eff_um is not None]
        reps = [(f"sc{i:02d}", next(r for r in rows0 if _scenario_key_lambda_sweep(r) == k)) for i, k in enumerate(scenarios_lambda, 1)]
        _write_scenarios_csv(outdir=outdir, name="scenarios_lambda.csv", scenario_rows=reps)

    write_summary_csv(all_rows, outdir)
    plot_rmse_vs_step(
        all_rows,
        outdir,
        scenarios=scenarios_step,
        layout=args.layout,
        style=args.style,
        formats=formats,
        dpi=args.dpi,
    )
    plot_bias_vs_step(
        all_rows,
        outdir,
        scenarios=scenarios_step,
        metric="Sa",
        layout=args.layout,
        style=args.style,
        formats=formats,
        dpi=args.dpi,
    )
    plot_bias_vs_step(
        all_rows,
        outdir,
        scenarios=scenarios_step,
        metric="Sq",
        layout=args.layout,
        style=args.style,
        formats=formats,
        dpi=args.dpi,
    )
    plot_bias_vs_step(
        all_rows,
        outdir,
        scenarios=scenarios_step,
        metric="Sz",
        layout=args.layout,
        style=args.style,
        formats=formats,
        dpi=args.dpi,
    )
    plot_step_error_vs_step(
        all_rows,
        outdir,
        scenarios=scenarios_step,
        layout=args.layout,
        style=args.style,
        formats=formats,
        dpi=args.dpi,
    )
    plot_rmse_vs_rms(
        all_rows,
        outdir,
        scenarios=scenarios_rms,
        layout=args.layout,
        style=args.style,
        formats=formats,
        dpi=args.dpi,
    )
    plot_bias_vs_rms(
        all_rows,
        outdir,
        scenarios=scenarios_rms,
        metric="Sa",
        layout=args.layout,
        style=args.style,
        formats=formats,
        dpi=args.dpi,
    )
    plot_bias_vs_rms(
        all_rows,
        outdir,
        scenarios=scenarios_rms,
        metric="Sq",
        layout=args.layout,
        style=args.style,
        formats=formats,
        dpi=args.dpi,
    )
    plot_bias_vs_rms(
        all_rows,
        outdir,
        scenarios=scenarios_rms,
        metric="Sz",
        layout=args.layout,
        style=args.style,
        formats=formats,
        dpi=args.dpi,
    )
    plot_rmse_vs_lambda_eff(
        all_rows,
        outdir,
        scenarios=scenarios_lambda,
        layout=args.layout,
        style=args.style,
        formats=formats,
        dpi=args.dpi,
    )

    print(f"Wrote figures to: {outdir}")


if __name__ == "__main__":
    main()
