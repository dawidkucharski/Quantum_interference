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


CLASSICAL_VARIANTS = [
    ("classical_default", "Classical default"),
    ("classical_ls_unwrap", "Classical LS unwrap"),
    ("classical_lsq_norm", "Classical LSQ + norm + LS unwrap"),
    ("classical_two_color", "Classical 2-colour"),
]

ENDPOINTS = [
    ("height_rmse_nm", "Height RMSE (nm)"),
    ("abs_bias_Sa_nm", r"$|\Delta S_a|$ (nm)"),
    ("abs_bias_Sq_nm", r"$|\Delta S_q|$ (nm)"),
    ("abs_bias_Sz_nm", r"$|\Delta S_z|$ (nm)"),
]


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
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise ValueError(f"No rows found in {path}")
    return rows


def _collapse_benchmark_rows(rows: list[dict[str, str]], *, method: str) -> dict[str, dict[str, float | str]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        if str(row.get("method", "")) != method:
            continue
        grouped[str(row["stem"])] += [row]

    out: dict[str, dict[str, float | str]] = {}
    for stem, entries in sorted(grouped.items()):
        first = entries[0]
        out[stem] = {
            "material": str(first.get("material", "")),
            "treatment": str(first.get("treatment", "")),
            "height_rmse_nm": float(np.median([float(e["height_rmse_nm"]) for e in entries])),
            "abs_bias_Sa_nm": float(np.median([abs(float(e["bias_Sa_nm"])) for e in entries])),
            "abs_bias_Sq_nm": float(np.median([abs(float(e["bias_Sq_nm"])) for e in entries])),
            "abs_bias_Sz_nm": float(np.median([abs(float(e["bias_Sz_nm"])) for e in entries])),
        }
    return out


def _collapse_two_color_rows(rows: list[dict[str, str]], *, method: str) -> dict[str, dict[str, float | str]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        if str(row.get("method", "")) != method:
            continue
        grouped[str(row["stem"])] += [row]

    out: dict[str, dict[str, float | str]] = {}
    for stem, entries in sorted(grouped.items()):
        first = entries[0]
        out[stem] = {
            "material": str(first.get("material", "")),
            "treatment": str(first.get("treatment", "")),
            "height_rmse_nm": float(np.median([float(e["height_rmse_nm"]) for e in entries])),
            "abs_bias_Sa_nm": float(np.median([float(e["abs_bias_Sa_bw_nm"]) for e in entries])),
            "abs_bias_Sq_nm": float(np.median([float(e["abs_bias_Sq_bw_nm"]) for e in entries])),
            "abs_bias_Sz_nm": float(np.median([float(e["abs_bias_Sz_bw_nm"]) for e in entries])),
        }
    return out


def _surface_level_medians(surface_map: dict[str, dict[str, float | str]], *, metric: str) -> float:
    values = [float(row[metric]) for row in surface_map.values()]
    if not values:
        return float("nan")
    return float(np.median(np.array(values, dtype=float)))


def _compose_frontier(
    variants: dict[str, dict[str, dict[str, float | str]]],
) -> tuple[list[dict[str, object]], dict[str, dict[str, float | str]]]:
    stems = sorted({stem for surface_map in variants.values() for stem in surface_map.keys()})
    frontier_rows: list[dict[str, object]] = []
    summary: dict[str, dict[str, float | str]] = {}
    for metric, _ in ENDPOINTS:
        best_values: list[float] = []
        variant_wins: dict[str, int] = {name: 0 for name, _ in CLASSICAL_VARIANTS}
        for stem in stems:
            candidates: list[tuple[float, str, dict[str, float | str]]] = []
            for variant_name, _ in CLASSICAL_VARIANTS:
                surface_map = variants.get(variant_name, {})
                row = surface_map.get(stem)
                if row is None:
                    continue
                candidates.append((float(row[metric]), variant_name, row))
            if not candidates:
                continue
            best_value, best_variant, best_row = min(candidates, key=lambda item: item[0])
            variant_wins[best_variant] += 1
            best_values.append(best_value)
            frontier_rows.append(
                {
                    "stem": stem,
                    "metric": metric,
                    "best_variant": best_variant,
                    "best_value": best_value,
                    "material": str(best_row["material"]),
                    "treatment": str(best_row["treatment"]),
                }
            )
        if not best_values:
            continue
        summary[metric] = {
            "median": float(np.median(np.array(best_values, dtype=float))),
            "winner": max(variant_wins.items(), key=lambda item: item[1])[0],
        }
    return frontier_rows, summary


def _write_summary_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["stem", "metric", "best_variant", "best_value", "material", "treatment"]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _write_table(
    path: Path,
    *,
    summary_variants: dict[str, dict[str, float]],
    frontier_summary: dict[str, dict[str, float | str]],
    hybrid_summary: dict[str, float],
    n_surfaces: int,
) -> None:
    def _fmt(value: float) -> str:
        return f"${value:.1f}$"

    lines = [
        "% Auto-generated by scripts/run_paper_classical_frontier_control.py",
        "\\begin{table}[t]",
        "\\centering",
        "\\footnotesize",
        "\\setlength{\\tabcolsep}{4pt}",
        f"\\caption{{Classical-frontier control over $n={int(n_surfaces)}$ measured surfaces. The table compares the default classical paper workflow, a classical least-squares unwrap, a stronger classical least-squares plus frame-normalised workflow, and a classical two-colour synthetic-wavelength baseline. The `Best classical frontier (oracle)` column is an optimistic upper bound formed by taking the per-surface minimum for each endpoint across these classical baselines and then reporting the resulting dataset median; it is therefore not a single deployable workflow. The final column shows the main hybrid branch for reference.}}",
        "\\label{tab:classical_frontier_control}",
        "\\resizebox{\\textwidth}{!}{%",
        "\\begin{tabular}{lcccccc}",
        "\\toprule",
            "Endpoint & Classical default & Classical LS unwrap & Classical LSQ + norm & Classical 2-colour & Best classical frontier (oracle) & Hybrid \\\\",
        "\\midrule",
    ]
    variant_order = [name for name, _ in CLASSICAL_VARIANTS]
    for metric, label in ENDPOINTS:
        row = [label]
        for variant_name in variant_order:
            row.append(_fmt(float(summary_variants[variant_name][metric])))
        row.append(_fmt(float(frontier_summary[metric]["median"])))
        row.append(_fmt(float(hybrid_summary[metric])))
        lines.append(" & ".join(row) + r" \\")
    lines.extend([
        "\\bottomrule",
        "\\end{tabular}",
        "}%",
        "\\end{table}",
        "",
    ])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description="Paper-facing classical frontier control for the measured benchmark")
    ap.add_argument("inputs", nargs="*", default=["data/*.sur"], help="SUR files or glob patterns under the repo root")
    ap.add_argument("--tag", type=str, default="paper_alicona_benchmark")
    ap.add_argument("--nx", type=int, default=256)
    ap.add_argument("--ny", type=int, default=256)
    ap.add_argument("--nreps", type=int, default=1)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--skip-benchmark", action="store_true")
    ap.add_argument("--out-table", type=Path, default=Path("manuscript/tables/classical_frontier_control.tex"))
    args = ap.parse_args()

    root = _ROOT
    py = sys.executable
    out_base = root / "outputs" / str(args.tag)
    expanded_inputs = _expand_inputs(root, list(args.inputs))

    base_per_surface = out_base / "per_surface.csv"
    ls_unwrap_per_surface = out_base / "unwrap_control" / "least_squares" / "per_surface.csv"
    robust_dir = out_base / "classical_frontier" / "classical_lsq_norm"
    robust_per_surface = robust_dir / "per_surface.csv"
    classical_control_per_surface = out_base / "classical_control" / "per_surface.csv"

    if not args.skip_benchmark and not base_per_surface.exists():
        cmd = [
            py,
            str(root / "scripts" / "benchmark_sur_interferometry.py"),
            *expanded_inputs,
            "--outdir",
            str(out_base),
            "--nx",
            str(int(args.nx)),
            "--ny",
            str(int(args.ny)),
            "--nreps",
            str(int(args.nreps)),
        ]
        if int(args.limit) > 0:
            cmd.extend(["--limit", str(int(args.limit))])
        _run(cmd)

    if not args.skip_benchmark and not ls_unwrap_per_surface.exists():
        cmd = [
            py,
            str(root / "scripts" / "run_paper_unwrap_control.py"),
            *expanded_inputs,
            "--tag",
            str(args.tag),
            "--nx",
            str(int(args.nx)),
            "--ny",
            str(int(args.ny)),
            "--nreps",
            str(int(args.nreps)),
            "--out-table",
            str(out_base / "classical_frontier" / "benchmark_unwrap_control.tex"),
        ]
        if int(args.limit) > 0:
            cmd.extend(["--limit", str(int(args.limit))])
        _run(cmd)

    if not args.skip_benchmark and not classical_control_per_surface.exists():
        cmd = [
            py,
            str(root / "scripts" / "run_paper_classical_two_color_control.py"),
            *expanded_inputs,
            "--outdir",
            str(out_base / "classical_control"),
            "--table-out",
            str(out_base / "classical_frontier" / "classical_two_color_control.tex"),
            "--nx",
            str(int(args.nx)),
            "--ny",
            str(int(args.ny)),
            "--nreps",
            str(int(args.nreps)),
            "--sur-resample",
            "area",
        ]
        if int(args.limit) > 0:
            cmd.extend(["--limit", str(int(args.limit))])
        _run(cmd)

    if not args.skip_benchmark and not robust_per_surface.exists():
        cmd = [
            py,
            str(root / "scripts" / "benchmark_sur_interferometry.py"),
            *expanded_inputs,
            "--outdir",
            str(robust_dir),
            "--nx",
            str(int(args.nx)),
            "--ny",
            str(int(args.ny)),
            "--nreps",
            str(int(args.nreps)),
            "--recon",
            "lsq",
            "--normalize-frames",
            "--unwrap-method",
            "least_squares",
        ]
        if int(args.limit) > 0:
            cmd.extend(["--limit", str(int(args.limit))])
        _run(cmd)

    required = [base_per_surface, ls_unwrap_per_surface, robust_per_surface, classical_control_per_surface]
    missing = [path for path in required if not path.exists()]
    if missing:
        missing_str = ", ".join(str(path) for path in missing)
        raise FileNotFoundError(f"Required benchmark artefacts are missing: {missing_str}")

    base_rows = _load_rows(base_per_surface)
    ls_unwrap_rows = _load_rows(ls_unwrap_per_surface)
    robust_rows = _load_rows(robust_per_surface)
    classical_control_rows = _load_rows(classical_control_per_surface)

    variants = {
        "classical_default": _collapse_benchmark_rows(base_rows, method="classical"),
        "classical_ls_unwrap": _collapse_benchmark_rows(ls_unwrap_rows, method="classical"),
        "classical_lsq_norm": _collapse_benchmark_rows(robust_rows, method="classical"),
        "classical_two_color": _collapse_two_color_rows(classical_control_rows, method="classical_two_color"),
    }
    hybrid_map = _collapse_benchmark_rows(base_rows, method="hybrid")

    summary_variants = {
        variant_name: {metric: _surface_level_medians(surface_map, metric=metric) for metric, _ in ENDPOINTS}
        for variant_name, surface_map in variants.items()
    }
    hybrid_summary = {metric: _surface_level_medians(hybrid_map, metric=metric) for metric, _ in ENDPOINTS}
    frontier_rows, frontier_summary = _compose_frontier(variants)

    summary_csv = out_base / "classical_frontier" / "summary.csv"
    _write_summary_csv(summary_csv, frontier_rows)
    _write_table(
        root / args.out_table,
        summary_variants=summary_variants,
        frontier_summary=frontier_summary,
        hybrid_summary=hybrid_summary,
        n_surfaces=len(hybrid_map),
    )
    print(f"Wrote: {summary_csv}")
    print(f"Wrote: {root / args.out_table}")


if __name__ == "__main__":
    main()