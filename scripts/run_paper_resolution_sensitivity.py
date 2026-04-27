#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path
import subprocess
import sys

import numpy as np

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "src"))

from qiprof.plot_style import apply_publication_style


def _run(cmd: list[str]) -> None:
    print(" ".join(cmd))
    subprocess.run(cmd, check=True)


def _expand_inputs(root: Path, patterns: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[Path] = set()
    for pattern in patterns:
        candidate = (root / pattern).resolve()
        if candidate.exists():
            if candidate not in seen:
                out.append(str(candidate))
                seen.add(candidate)
            continue
        matches = sorted(root.glob(pattern))
        for match in matches:
            resolved = match.resolve()
            if resolved not in seen:
                out.append(str(resolved))
                seen.add(resolved)
    if not out:
        raise FileNotFoundError(f"No input surfaces matched: {patterns}")
    return out


def _load_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise ValueError(f"No rows found in {path}")
    return rows


def _collapse_surface_rows(rows: list[dict[str, str]]) -> list[dict[str, float | str]]:
    grouped: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[(row["stem"], row["method"])].append(row)

    out: list[dict[str, float | str]] = []
    for (stem, method), entries in sorted(grouped.items()):
        out.append(
            {
                "stem": stem,
                "method": method,
                "height_rmse_nm": float(np.median([float(e["height_rmse_nm"]) for e in entries])),
                "abs_bias_Sa_nm": float(np.median([abs(float(e["bias_Sa_nm"])) for e in entries])),
                "abs_bias_Sq_nm": float(np.median([abs(float(e["bias_Sq_nm"])) for e in entries])),
                "abs_bias_Sz_nm": float(np.median([abs(float(e["bias_Sz_nm"])) for e in entries])),
            }
        )
    return out


def _method_order(methods: set[str]) -> list[str]:
    preferred = ["classical", "quantum_like", "hybrid"]
    return [m for m in preferred if m in methods] + sorted(m for m in methods if m not in preferred)


def _method_label(method: str) -> str:
    return {
        "classical": "Classical",
        "quantum_like": "Quantum-like",
        "hybrid": "Hybrid",
    }.get(method, method)


def _method_color(method: str) -> str:
    return {
        "classical": "#1f77b4",
        "quantum_like": "#d62728",
        "hybrid": "#2ca02c",
    }.get(method, "0.35")


def _write_summary(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "resolution_px",
        "method",
        "height_rmse_nm_median",
        "abs_bias_Sa_nm_median",
        "abs_bias_Sq_nm_median",
        "abs_bias_Sz_nm_median",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _plot(summary_rows: list[dict[str, object]], outpath: Path) -> None:
    import matplotlib.pyplot as plt

    apply_publication_style(base_fontsize=8.5)
    outpath.parent.mkdir(parents=True, exist_ok=True)

    panels = [
        ("height_rmse_nm_median", "Median height RMSE (nm)"),
        ("abs_bias_Sa_nm_median", "Median $|\\Delta S_a|$ (nm)"),
        ("abs_bias_Sq_nm_median", "Median $|\\Delta S_q|$ (nm)"),
        ("abs_bias_Sz_nm_median", "Median $|\\Delta S_z|$ (nm)"),
    ]
    methods = _method_order({str(row["method"]) for row in summary_rows})
    resolutions = sorted({int(row["resolution_px"]) for row in summary_rows})

    fig, axes = plt.subplots(2, 2, figsize=(6.77, 4.9), constrained_layout=True)
    axes = axes.ravel()
    for ax, (key, ylabel) in zip(axes, panels):
        for method in methods:
            method_rows = {int(row["resolution_px"]): float(row[key]) for row in summary_rows if str(row["method"]) == method}
            yvals = [method_rows[res] for res in resolutions]
            ax.plot(
                resolutions,
                yvals,
                marker="o",
                linewidth=1.3,
                markersize=4.0,
                color=_method_color(method),
                label=_method_label(method),
            )
        ax.set_yscale("log")
        ax.set_xlabel("Benchmark grid (pixels)")
        ax.set_ylabel(ylabel)
        ax.set_xticks(resolutions)
        ax.grid(True, which="both", alpha=0.25)

    axes[0].legend(frameon=False, ncol=3, loc="upper center")
    fig.savefig(outpath)
    plt.close(fig)


def main() -> None:
    ap = argparse.ArgumentParser(description="Targeted measured-benchmark sensitivity to downsampling resolution")
    ap.add_argument("inputs", nargs="*", default=["data/*.sur"], help="SUR files or glob patterns under the repo root")
    ap.add_argument("--tag", type=str, default="paper_alicona_benchmark")
    ap.add_argument("--resolutions", nargs="*", type=int, default=[128, 256, 384])
    ap.add_argument("--nreps", type=int, default=1)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--base-nx", type=int, default=256)
    ap.add_argument("--base-ny", type=int, default=256)
    ap.add_argument("--skip-base-reuse", action="store_true")
    ap.add_argument("--skip-benchmark", action="store_true")
    args = ap.parse_args()

    root = _ROOT
    py = sys.executable
    out_base = root / "outputs" / str(args.tag)
    summary_dir = out_base / "resolution_sensitivity"
    expanded_inputs = _expand_inputs(root, list(args.inputs))
    base_per_surface = out_base / "per_surface.csv"

    summary_rows: list[dict[str, object]] = []
    for res in sorted({int(x) for x in list(args.resolutions)}):
        per_surface = (
            base_per_surface
            if (not bool(args.skip_base_reuse)) and res == int(args.base_nx) == int(args.base_ny) and base_per_surface.exists()
            else summary_dir / f"{res}x{res}" / "per_surface.csv"
        )
        if per_surface is not base_per_surface and not args.skip_benchmark:
            cmd = [
                py,
                str(root / "scripts" / "benchmark_sur_interferometry.py"),
                *expanded_inputs,
                "--outdir",
                str(per_surface.parent),
                "--nx",
                str(res),
                "--ny",
                str(res),
                "--nreps",
                str(int(args.nreps)),
            ]
            if int(args.limit) > 0:
                cmd.extend(["--limit", str(int(args.limit))])
            _run(cmd)
        rows = _load_rows(per_surface)
        collapsed = _collapse_surface_rows(rows)
        for method in _method_order({str(row["method"]) for row in collapsed}):
            mrows = [row for row in collapsed if str(row["method"]) == method]
            summary_rows.append(
                {
                    "resolution_px": res,
                    "method": method,
                    "height_rmse_nm_median": float(np.median([float(row["height_rmse_nm"]) for row in mrows])),
                    "abs_bias_Sa_nm_median": float(np.median([float(row["abs_bias_Sa_nm"]) for row in mrows])),
                    "abs_bias_Sq_nm_median": float(np.median([float(row["abs_bias_Sq_nm"]) for row in mrows])),
                    "abs_bias_Sz_nm_median": float(np.median([float(row["abs_bias_Sz_nm"]) for row in mrows])),
                }
            )

    summary_csv = summary_dir / "summary.csv"
    _write_summary(summary_csv, summary_rows)
    fig_path = out_base / "figures" / "resolution_sensitivity_summary.pdf"
    _plot(summary_rows, fig_path)
    print(f"Wrote: {summary_csv}")
    print(f"Wrote: {fig_path}")


if __name__ == "__main__":
    main()