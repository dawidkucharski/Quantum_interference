#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from collections import defaultdict
from pathlib import Path

import numpy as np

_ROOT = Path(__file__).resolve().parents[1]
import sys

sys.path.insert(0, str(_ROOT / "src"))

from qiprof.plot_style import apply_publication_style


def _load_per_surface_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    if not rows:
        raise ValueError(f"No rows in {path}")
    return rows


@dataclass(frozen=True)
class MethodSeries:
    method: str
    rmse_nm: np.ndarray
    sq_true_nm: np.ndarray


@dataclass(frozen=True)
class RoughnessSeries:
    method: str
    sa_true_nm: np.ndarray
    sa_est_nm: np.ndarray
    sq_true_nm: np.ndarray
    sq_est_nm: np.ndarray
    sz_true_nm: np.ndarray
    sz_est_nm: np.ndarray


def _collapse_surface_rows(rows: list[dict[str, str]]) -> list[dict[str, object]]:
    grouped: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[(row["stem"], row["method"])].append(row)

    numeric_keys = [
        "height_rmse_nm",
        "Sq_true_nm",
        "Sq_true_bw_nm",
        "Sa_true_nm",
        "Sa_true_bw_nm",
        "Sa_est_nm",
        "Sq_est_nm",
        "Sz_true_nm",
        "Sz_true_bw_nm",
        "Sz_est_nm",
        "bias_Sa_nm",
        "bias_Sa_bw_nm",
        "bias_Sq_nm",
        "bias_Sq_bw_nm",
        "bias_Sz_nm",
        "bias_Sz_bw_nm",
    ]
    out: list[dict[str, object]] = []
    for (stem, method), entries in sorted(grouped.items()):
        collapsed: dict[str, object] = {
            "stem": stem,
            "method": method,
            "material": entries[0].get("material", ""),
            "treatment": entries[0].get("treatment", ""),
        }
        for key in numeric_keys:
            vals = np.array([float(entry[key]) for entry in entries], dtype=float)
            collapsed[key] = float(np.median(vals))
        out.append(collapsed)
    return out


def _collapsed_method_map(rows: list[dict[str, str]]) -> dict[str, dict[str, dict[str, object]]]:
    surface_map: dict[str, dict[str, dict[str, object]]] = defaultdict(dict)
    for row in _collapse_surface_rows(rows):
        stem = str(row["stem"])
        method = str(row["method"])
        surface_map[stem][method] = row
    return dict(surface_map)


def _series_by_method(rows: list[dict[str, str]]) -> list[MethodSeries]:
    methods = _method_order({r["method"] for r in rows})
    out: list[MethodSeries] = []
    for method in methods:
        mrows = [r for r in rows if r["method"] == method]
        rmse = np.array([float(r["height_rmse_nm"]) for r in mrows], dtype=float)
        sq_true = np.array([float(r["Sq_true_nm"]) for r in mrows], dtype=float)
        out.append(MethodSeries(method=method, rmse_nm=rmse, sq_true_nm=sq_true))
    return out


def _roughness_by_method(rows: list[dict[str, str]], *, true_suffix: str) -> list[RoughnessSeries]:
    methods = _method_order({r["method"] for r in rows})
    out: list[RoughnessSeries] = []
    for method in methods:
        mrows = [r for r in rows if r["method"] == method]
        out.append(
            RoughnessSeries(
                method=method,
                sa_true_nm=np.array([float(r[f"Sa_true{true_suffix}_nm"]) for r in mrows], dtype=float),
                sa_est_nm=np.array([float(r["Sa_est_nm"]) for r in mrows], dtype=float),
                sq_true_nm=np.array([float(r[f"Sq_true{true_suffix}_nm"]) for r in mrows], dtype=float),
                sq_est_nm=np.array([float(r["Sq_est_nm"]) for r in mrows], dtype=float),
                sz_true_nm=np.array([float(r[f"Sz_true{true_suffix}_nm"]) for r in mrows], dtype=float),
                sz_est_nm=np.array([float(r["Sz_est_nm"]) for r in mrows], dtype=float),
            )
        )
    return out


def _method_label(method: str) -> str:
    return {
        "classical": "Classical",
        "quantum_like": "Coincidence-proxy",
        "hybrid": "Hybrid",
    }.get(method, method)


def _method_color(method: str) -> str:
    return {
        "classical": "#1f77b4",
        "quantum_like": "#d62728",
        "hybrid": "#2ca02c",
    }.get(method, "0.35")


def _method_order(methods: set[str]) -> list[str]:
    preferred = ["classical", "quantum_like", "hybrid"]
    return [m for m in preferred if m in methods] + sorted([m for m in methods if m not in preferred])


def _treatment_order(groups: set[str]) -> list[str]:
    preferred = [
        "Grinding",
        "Honed",
        "Glass bead blasted",
        "Burnishing",
        "Turning (roughing)",
        "Turning (finishing)",
        "Milling (roughing)",
        "Milling (finishing)",
        "Wire EDM (roughing)",
        "Wire EDM (finishing)",
    ]
    return [g for g in preferred if g in groups] + sorted([g for g in groups if g not in preferred])


def _treatment_label(group: str) -> str:
    return {
        "Glass bead blasted": "Glass bead",
        "Turning (roughing)": "Turning rough",
        "Turning (finishing)": "Turning finish",
        "Milling (roughing)": "Milling rough",
        "Milling (finishing)": "Milling finish",
        "Wire EDM (roughing)": "WEDM rough",
        "Wire EDM (finishing)": "WEDM finish",
    }.get(group, group)


def _plot(outpath: Path, series: list[MethodSeries]) -> None:
    import matplotlib.pyplot as plt

    outpath.parent.mkdir(parents=True, exist_ok=True)
    apply_publication_style(base_fontsize=8.5)

    methods = [s.method for s in series]
    labels = [_method_label(m) for m in methods]

    fig, axes = plt.subplots(1, 2, figsize=(6.77, 2.95), constrained_layout=True)

    # (a) RMSE distribution by method (log scale)
    ax = axes[0]
    data = [s.rmse_nm for s in series]
    ax.boxplot(
        data,
        tick_labels=labels,
        showfliers=False,
        whis=(10, 90),
        widths=0.55,
    )
    ax.set_yscale("log")
    ax.set_ylabel("Height RMSE (nm) [log]")
    ax.set_title("(a) RMSE distribution")
    ax.grid(True, which="both", axis="y", alpha=0.25)

    # (b) RMSE vs true Sq (roughness) across surfaces
    ax = axes[1]
    for s in series:
        ax.scatter(
            s.sq_true_nm,
            s.rmse_nm,
            s=14,
            alpha=0.72,
            label=_method_label(s.method),
        )
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("True Sq (nm) [log]")
    ax.set_ylabel("Height RMSE (nm) [log]")
    ax.set_title("(b) RMSE vs roughness")
    ax.grid(True, which="both", alpha=0.25)
    ax.legend(frameon=False)

    fig.savefig(outpath)
    plt.close(fig)


def _positive_limits(series: list[RoughnessSeries], attr_true: str, attr_est: str) -> tuple[float, float]:
    vals: list[np.ndarray] = []
    for item in series:
        vals.append(getattr(item, attr_true))
        vals.append(getattr(item, attr_est))
    merged = np.concatenate(vals)
    merged = merged[np.isfinite(merged) & (merged > 0.0)]
    if merged.size == 0:
        return 1.0, 10.0
    lo = float(np.min(merged))
    hi = float(np.max(merged))
    return lo * 0.8, hi * 1.25


def _plot_roughness(outpath: Path, series: list[RoughnessSeries], *, reference_label: str) -> None:
    import matplotlib.pyplot as plt

    outpath.parent.mkdir(parents=True, exist_ok=True)
    apply_publication_style(base_fontsize=8.5)

    fig, axes = plt.subplots(1, 3, figsize=(6.77, 2.9), constrained_layout=True)
    panels = [
        (r"(a) $S_a$", "sa_true_nm", "sa_est_nm"),
        (r"(b) $S_q$", "sq_true_nm", "sq_est_nm"),
        (r"(c) $S_z$", "sz_true_nm", "sz_est_nm"),
    ]

    for ax, (label, attr_true, attr_est) in zip(axes, panels):
        lo, hi = _positive_limits(series, attr_true, attr_est)
        for item in series:
            xs = getattr(item, attr_true)
            ys = getattr(item, attr_est)
            mask = np.isfinite(xs) & np.isfinite(ys) & (xs > 0.0) & (ys > 0.0)
            ax.scatter(
                xs[mask],
                ys[mask],
                s=13,
                alpha=0.72,
                label=_method_label(item.method),
            )
        ax.plot([lo, hi], [lo, hi], linestyle="--", linewidth=0.9, color="0.35")
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlim(lo, hi)
        ax.set_ylim(lo, hi)
        ax.set_title(label)
        ax.grid(True, which="both", alpha=0.25)

    fig.supxlabel(f"{reference_label.capitalize()} parameter (nm) [log]")
    fig.supylabel("Estimated parameter (nm) [log]")
    handles, labels = axes[0].get_legend_handles_labels()
    if handles:
        axes[-1].legend(handles, labels, frameon=False, loc="lower right")

    fig.savefig(outpath)
    plt.close(fig)


def _plot_roughness_bland_altman(
    outpath: Path,
    rows: list[dict[str, str]],
    *,
    true_suffix: str,
    reference_label: str,
) -> None:
    import matplotlib.pyplot as plt

    outpath.parent.mkdir(parents=True, exist_ok=True)
    apply_publication_style(base_fontsize=8.5)

    collapsed = _collapse_surface_rows(rows)
    methods = _method_order({str(row["method"]) for row in collapsed})
    fig, axes = plt.subplots(1, 3, figsize=(6.77, 2.9), constrained_layout=True)
    panels = [
        (r"(a) $S_a$ bias", f"Sa_true{true_suffix}_nm", "Sa_est_nm"),
        (r"(b) $S_q$ bias", f"Sq_true{true_suffix}_nm", "Sq_est_nm"),
        (r"(c) $S_z$ bias", f"Sz_true{true_suffix}_nm", "Sz_est_nm"),
    ]

    for ax, (label, true_key, est_key) in zip(axes, panels):
        x_values: list[np.ndarray] = []
        y_values: list[np.ndarray] = []
        for method in methods:
            mrows = [row for row in collapsed if row["method"] == method]
            true_vals = np.array([float(str(row[true_key])) for row in mrows], dtype=float)
            est_vals = np.array([float(str(row[est_key])) for row in mrows], dtype=float)
            means = 0.5 * (true_vals + est_vals)
            bias = est_vals - true_vals
            mask = np.isfinite(means) & np.isfinite(bias) & (means > 0.0)
            if not np.any(mask):
                continue
            means = means[mask]
            bias = bias[mask]
            x_values.append(means)
            y_values.append(bias)
            ax.scatter(
                means,
                bias,
                s=15,
                alpha=0.72,
                color=_method_color(method),
                label=_method_label(method),
            )
            median_bias = float(np.median(bias))
            ax.axhline(median_bias, color=_method_color(method), linestyle=":", linewidth=0.9, alpha=0.85)

        ax.axhline(0.0, color="0.35", linestyle="--", linewidth=0.9)
        if x_values:
            merged_x = np.concatenate(x_values)
            x_lo = float(np.min(merged_x)) * 0.8
            x_hi = float(np.max(merged_x)) * 1.25
            ax.set_xscale("log")
            ax.set_xlim(x_lo, x_hi)
        if y_values:
            merged_y = np.concatenate(y_values)
            y_span = float(np.percentile(np.abs(merged_y), 98))
            if y_span <= 0.0:
                y_span = float(np.max(np.abs(merged_y))) if merged_y.size else 1.0
            ax.set_ylim(-1.15 * y_span, 1.15 * y_span)
        ax.set_title(label)
        ax.grid(True, which="both", alpha=0.25)

    fig.supxlabel(f"Mean of estimate and {reference_label} (nm) [log]")
    fig.supylabel(f"Estimated $-$ {reference_label} (nm)")
    handles, labels = axes[0].get_legend_handles_labels()
    if handles:
        axes[-1].legend(handles, labels, frameon=False, loc="upper left")

    fig.savefig(outpath)
    plt.close(fig)


def _plot_roughness_by_treatment(
    outpath: Path,
    rows: list[dict[str, str]],
    *,
    bias_suffix: str,
    reference_label: str,
) -> None:
    import matplotlib.pyplot as plt

    outpath.parent.mkdir(parents=True, exist_ok=True)
    apply_publication_style(base_fontsize=8.3)

    treatments = _treatment_order({r["treatment"] for r in rows})
    methods = _method_order({r["method"] for r in rows})
    metrics = [
        ("Sa", "Median $|\\Delta S_a|$ (nm)"),
        ("Sq", "Median $|\\Delta S_q|$ (nm)"),
        ("Sz", "Median $|\\Delta S_z|$ (nm)"),
    ]

    x = np.arange(len(treatments), dtype=float)
    fig, axes = plt.subplots(3, 1, figsize=(6.77, 5.35), sharex=True, constrained_layout=True)

    for ax, (metric, ylabel) in zip(axes, metrics):
        for method in methods:
            ys: list[float] = []
            for treatment in treatments:
                vals = [
                    abs(float(r[f"bias_{metric}{bias_suffix}_nm"]))
                    for r in rows
                    if r["treatment"] == treatment and r["method"] == method
                ]
                ys.append(float(np.median(vals)) if vals else np.nan)
            arr = np.array(ys, dtype=float)
            arr = np.where(np.isfinite(arr) & (arr > 0.0), arr, np.nan)
            ax.plot(x, arr, marker="o", markersize=3.8, linewidth=1.2, label=_method_label(method))
        ax.set_yscale("log")
        ax.set_ylabel(ylabel)
        ax.grid(True, which="both", axis="y", alpha=0.25)

    axes[0].set_title(f"Per-treatment roughness error against {reference_label}")
    axes[0].legend(frameon=False, ncol=3, loc="upper left")
    axes[-1].set_xticks(x, [_treatment_label(g) for g in treatments], rotation=24, ha="right")
    axes[-1].set_xlabel("Surface treatment")

    fig.savefig(outpath)
    plt.close(fig)


def _plot_pairwise_method_comparison(outpath: Path, rows: list[dict[str, str]]) -> None:
    import matplotlib.pyplot as plt

    outpath.parent.mkdir(parents=True, exist_ok=True)
    apply_publication_style(base_fontsize=8.3)

    surface_map = _collapsed_method_map(rows)
    paired_keys = [
        ("classical", "hybrid", "(a) Hybrid vs classical"),
        ("quantum_like", "hybrid", "(b) Hybrid vs coincidence-proxy"),
    ]

    fig, axes = plt.subplots(1, 3, figsize=(6.77, 2.85), constrained_layout=True)

    for ax, (ref_method, test_method, title) in zip(axes[:2], paired_keys):
        x_vals: list[float] = []
        y_vals: list[float] = []
        for method_map in surface_map.values():
            if ref_method not in method_map or test_method not in method_map:
                continue
            x_vals.append(float(str(method_map[ref_method]["height_rmse_nm"])))
            y_vals.append(float(str(method_map[test_method]["height_rmse_nm"])))
        xs = np.array(x_vals, dtype=float)
        ys = np.array(y_vals, dtype=float)
        mask = np.isfinite(xs) & np.isfinite(ys) & (xs > 0.0) & (ys > 0.0)
        xs = xs[mask]
        ys = ys[mask]
        ax.scatter(
            xs,
            ys,
            s=16,
            alpha=0.78,
            color=_method_color(test_method),
        )
        if xs.size:
            lo = 0.9 * float(np.min(np.concatenate([xs, ys])))
            hi = 1.1 * float(np.max(np.concatenate([xs, ys])))
            ax.plot([lo, hi], [lo, hi], linestyle="--", linewidth=0.9, color="0.35")
            ax.set_xscale("log")
            ax.set_yscale("log")
            ax.set_xlim(lo, hi)
            ax.set_ylim(lo, hi)
        ax.set_title(title)
        ax.set_xlabel(f"{_method_label(ref_method)} RMSE (nm) [log]")
        ax.grid(True, which="both", alpha=0.25)

    axes[0].set_ylabel("Hybrid RMSE (nm) [log]")

    predictor_ax = axes[2]
    sq_vals: list[float] = []
    gain_hc: list[float] = []
    gain_hq: list[float] = []
    for method_map in surface_map.values():
        if "hybrid" not in method_map:
            continue
        if "classical" in method_map:
            sq_vals.append(
                float(str(method_map["hybrid"].get("Sq_true_bw_nm", method_map["hybrid"]["Sq_true_nm"])))
            )
            gain_hc.append(
                float(str(method_map["hybrid"]["height_rmse_nm"]))
                - float(str(method_map["classical"]["height_rmse_nm"]))
            )
        if "quantum_like" in method_map:
            gain_hq.append(
                float(str(method_map["hybrid"]["height_rmse_nm"]))
                - float(str(method_map["quantum_like"]["height_rmse_nm"]))
            )

    xs = np.array(sq_vals, dtype=float)
    ys_hc = np.array(gain_hc, dtype=float)
    ys_hq = np.array(gain_hq, dtype=float)
    mask_hc = np.isfinite(xs) & np.isfinite(ys_hc) & (xs > 0.0)
    mask_hq = np.isfinite(xs) & np.isfinite(ys_hq) & (xs > 0.0)
    predictor_ax.scatter(
        xs[mask_hc],
        ys_hc[mask_hc],
        s=15,
        alpha=0.74,
        color="#355070",
        label="Hybrid - Classical",
    )
    predictor_ax.scatter(
        xs[mask_hq],
        ys_hq[mask_hq],
        s=15,
        alpha=0.74,
        color="#b56576",
        label="Hybrid - Coincidence-proxy",
    )
    predictor_ax.axhline(0.0, color="0.35", linestyle="--", linewidth=0.9)
    predictor_ax.set_xscale("log")
    predictor_ax.set_title("(c) Hybrid gain vs benchmark-grid $S_q$")
    predictor_ax.set_xlabel("Benchmark-grid $S_q$ (nm) [log]")
    predictor_ax.set_ylabel("RMSE difference (nm)")
    predictor_ax.grid(True, which="both", alpha=0.25)
    predictor_ax.legend(frameon=False, loc="upper right")

    fig.savefig(outpath)
    plt.close(fig)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Generate manuscript-ready figures from the Alicona measured-surface benchmark CSV."
    )
    ap.add_argument(
        "--per-surface",
        type=Path,
        default=Path("outputs/paper_alicona_benchmark/per_surface.csv"),
        help="Path to per_surface.csv produced by scripts/benchmark_sur_interferometry.py",
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=Path("outputs/paper_alicona_benchmark/figures/rmse_measured_summary.pdf"),
        help="Output figure path (.pdf recommended for LaTeX)",
    )
    ap.add_argument(
        "--roughness-out",
        type=Path,
        default=Path("outputs/paper_alicona_benchmark/figures/roughness_measured_summary.pdf"),
        help="Output path for the roughness-parameter comparison figure (.pdf recommended for LaTeX)",
    )
    ap.add_argument(
        "--roughness-bias-out",
        type=Path,
        default=Path("outputs/paper_alicona_benchmark/figures/roughness_measured_bland_altman.pdf"),
        help="Output path for the roughness residual / Bland-Altman-style figure (.pdf recommended for LaTeX)",
    )
    ap.add_argument(
        "--roughness-by-treatment-out",
        type=Path,
        default=Path("outputs/paper_alicona_benchmark/figures/roughness_measured_by_treatment.pdf"),
        help="Output path for the treatment-split roughness-error figure (.pdf recommended for LaTeX)",
    )
    ap.add_argument(
        "--pairwise-out",
        type=Path,
        default=Path("outputs/paper_alicona_benchmark/figures/paired_method_comparison.pdf"),
        help="Output path for the paired per-surface RMSE comparison figure (.pdf recommended for LaTeX)",
    )
    ap.add_argument(
        "--roughness-suffix",
        type=str,
        default="",
        help="Optional suffix selecting alternate roughness reference columns, e.g. '_bw' for matched-bandwidth fields.",
    )
    ap.add_argument(
        "--roughness-reference-label",
        type=str,
        default="FV reference",
        help="Human-readable label for the roughness-reference domain used in figure titles and axis labels.",
    )
    args = ap.parse_args()

    rows = _load_per_surface_csv(args.per_surface)
    for k in ("method", "height_rmse_nm", "Sq_true_nm"):
        if k not in rows[0]:
            raise ValueError(f"Missing column {k!r} in {args.per_surface}")
    true_suffix = str(args.roughness_suffix)
    for k in (f"Sa_true{true_suffix}_nm", "Sa_est_nm", f"Sq_true{true_suffix}_nm", "Sq_est_nm", f"Sz_true{true_suffix}_nm", "Sz_est_nm"):
        if k not in rows[0]:
            raise ValueError(f"Missing column {k!r} in {args.per_surface}")

    series = _series_by_method(rows)
    roughness = _roughness_by_method(rows, true_suffix=true_suffix)
    _plot(args.out, series)
    _plot_roughness(
        args.roughness_out,
        roughness,
        reference_label=str(args.roughness_reference_label),
    )
    _plot_roughness_bland_altman(
        args.roughness_bias_out,
        rows,
        true_suffix=true_suffix,
        reference_label=str(args.roughness_reference_label),
    )
    _plot_roughness_by_treatment(
        args.roughness_by_treatment_out,
        rows,
        bias_suffix=true_suffix,
        reference_label=str(args.roughness_reference_label),
    )
    _plot_pairwise_method_comparison(args.pairwise_out, rows)
    print(f"Wrote: {args.out}")
    print(f"Wrote: {args.roughness_out}")
    print(f"Wrote: {args.roughness_bias_out}")
    print(f"Wrote: {args.roughness_by_treatment_out}")
    print(f"Wrote: {args.pairwise_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
