#!/usr/bin/env python3

"""Run an approximate Gaussian roughness-filter sensitivity control for the paper benchmark.

This control is intentionally narrower than a full traceable roughness workflow.
It reruns the measured-surface benchmark with approximate Gaussian S/L nesting
indices on the benchmark grid, then compares the filtered roughness medians and
leave-one-group-out stability against the canonical matched-bandwidth benchmark.
"""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path
import subprocess
import sys

import numpy as np


ROW_END = "\\\\"
METHOD_ORDER = ["classical", "quantum_like", "hybrid"]
METHOD_LABEL = {
    "classical": "Classical",
    "quantum_like": "Coincidence-proxy",
    "hybrid": "Hybrid",
}
METRICS = [
    (r"$|\Delta S_a|$", "bias_Sa_bw_nm", "bias_Sa_iso_nm"),
    (r"$|\Delta S_q|$", "bias_Sq_bw_nm", "bias_Sq_iso_nm"),
    (r"$|\Delta S_z|$", "bias_Sz_bw_nm", "bias_Sz_iso_nm"),
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


def _surface_level_rows(rows: list[dict[str, str]], numeric_keys: list[str]) -> list[dict[str, object]]:
    grouped: dict[str, dict[str, list[dict[str, str]]]] = defaultdict(lambda: defaultdict(list))
    for row in rows:
        grouped[row["stem"]][row["method"]].append(row)

    out: list[dict[str, object]] = []
    for stem, method_rows in sorted(grouped.items()):
        for method, entries in method_rows.items():
            first = entries[0]
            collapsed: dict[str, object] = {
                "stem": stem,
                "method": method,
                "material": str(first.get("material", "")),
                "treatment": str(first.get("treatment", "")),
            }
            for key in numeric_keys:
                vals = np.array([float(entry[key]) for entry in entries], dtype=float)
                collapsed[key] = float(np.median(vals))
            out.append(collapsed)
    return out


def _method_medians(rows: list[dict[str, object]], *, metric: str) -> dict[str, float]:
    medians: dict[str, float] = {}
    for method in METHOD_ORDER:
        vals = [float(row[metric]) for row in rows if str(row["method"]) == method]
        if not vals:
            continue
        medians[method] = float(np.median(np.abs(np.array(vals, dtype=float))))
    return medians


def _winning_method(rows: list[dict[str, object]], *, metric: str) -> str | None:
    medians = _method_medians(rows, metric=metric)
    if not medians:
        return None
    return min(medians, key=medians.get)


def _holdout_rate(rows: list[dict[str, object]], *, metric: str, group_key: str) -> float:
    groups = sorted({str(row[group_key]) for row in rows if str(row.get(group_key, ""))})
    matches = 0
    valid_splits = 0
    for group in groups:
        train_rows = [row for row in rows if str(row.get(group_key, "")) != group]
        holdout_rows = [row for row in rows if str(row.get(group_key, "")) == group]
        train_winner = _winning_method(train_rows, metric=metric)
        holdout_winner = _winning_method(holdout_rows, metric=metric)
        if train_winner is None or holdout_winner is None:
            continue
        valid_splits += 1
        if train_winner == holdout_winner:
            matches += 1
    return 100.0 * matches / max(valid_splits, 1)


def _triplet(medians: dict[str, float]) -> str:
    return (
        f"${medians['classical']:.1f} / {medians['quantum_like']:.1f} / {medians['hybrid']:.1f}$"
    )


def _write_summary(
    path: Path,
    *,
    baseline_rows: list[dict[str, object]],
    filtered_rows: list[dict[str, object]],
) -> None:
    fieldnames = [
        "endpoint",
        "baseline_classical_median_abs_nm",
        "baseline_coincidence_proxy_median_abs_nm",
        "baseline_hybrid_median_abs_nm",
        "baseline_material_match_pct",
        "baseline_treatment_match_pct",
        "baseline_winner",
        "filtered_classical_median_abs_nm",
        "filtered_coincidence_proxy_median_abs_nm",
        "filtered_hybrid_median_abs_nm",
        "filtered_material_match_pct",
        "filtered_treatment_match_pct",
        "filtered_winner",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for label, baseline_metric, filtered_metric in METRICS:
            baseline_medians = _method_medians(baseline_rows, metric=baseline_metric)
            filtered_medians = _method_medians(filtered_rows, metric=filtered_metric)
            writer.writerow(
                {
                    "endpoint": label,
                    "baseline_classical_median_abs_nm": f"{baseline_medians['classical']:.6f}",
                    "baseline_coincidence_proxy_median_abs_nm": f"{baseline_medians['quantum_like']:.6f}",
                    "baseline_hybrid_median_abs_nm": f"{baseline_medians['hybrid']:.6f}",
                    "baseline_material_match_pct": f"{_holdout_rate(baseline_rows, metric=baseline_metric, group_key='material'):.6f}",
                    "baseline_treatment_match_pct": f"{_holdout_rate(baseline_rows, metric=baseline_metric, group_key='treatment'):.6f}",
                    "baseline_winner": METHOD_LABEL[str(_winning_method(baseline_rows, metric=baseline_metric))],
                    "filtered_classical_median_abs_nm": f"{filtered_medians['classical']:.6f}",
                    "filtered_coincidence_proxy_median_abs_nm": f"{filtered_medians['quantum_like']:.6f}",
                    "filtered_hybrid_median_abs_nm": f"{filtered_medians['hybrid']:.6f}",
                    "filtered_material_match_pct": f"{_holdout_rate(filtered_rows, metric=filtered_metric, group_key='material'):.6f}",
                    "filtered_treatment_match_pct": f"{_holdout_rate(filtered_rows, metric=filtered_metric, group_key='treatment'):.6f}",
                    "filtered_winner": METHOD_LABEL[str(_winning_method(filtered_rows, metric=filtered_metric))],
                }
            )


def _write_table(
    path: Path,
    *,
    baseline_rows: list[dict[str, object]],
    filtered_rows: list[dict[str, object]],
    n_surfaces: int,
    n_reps: str,
    s_filter_um: float,
    l_filter_um: float,
) -> None:
    lines = [
        "% Auto-generated by scripts/run_paper_roughness_filter_control.py",
        "\\begin{table}[t]",
        "\\centering",
        "\\footnotesize",
        "\\setlength{\\tabcolsep}{4pt}",
        (
            "\\caption{Approximate Gaussian roughness-filter sensitivity control for the measured-surface benchmark over "
            f"$n={int(n_surfaces)}$ unique surfaces using {n_reps} Monte Carlo realisations per surface and method. "
            "Baseline entries use the canonical matched-bandwidth benchmark-grid roughness reference. Filtered entries apply "
            f"an approximate Gaussian S/L control with $\\lambda_s={float(s_filter_um):.1f}\\,\\mu\\mathrm{{m}}$ and "
            f"$\\lambda_c={float(l_filter_um):.1f}\\,\\mu\\mathrm{{m}}$ on the same benchmark grid before computing "
            "$S_a$, $S_q$, and $S_z$. Median-error cells report Classical / Coincidence-proxy / Hybrid surface-level median absolute bias in nm, while holdout cells report leave-one-material-out / leave-one-treatment-out winner-match rates in percent. This is a standards-aligned sensitivity check rather than a traceable ISO closure.}"
        ),
        "\\label{tab:benchmark_roughness_filter_control}",
        "\\resizebox{\\textwidth}{!}{%",
        "\\begin{tabular}{lcccc}",
        "\\toprule",
        r"Endpoint & Baseline median $|\Delta|$ C/P/H (nm) & Filtered median $|\Delta|$ C/P/H (nm) & Baseline holdout M/T (\%) & Filtered holdout M/T (\%) " + ROW_END,
        "\\midrule",
    ]
    for label, baseline_metric, filtered_metric in METRICS:
        baseline_medians = _method_medians(baseline_rows, metric=baseline_metric)
        filtered_medians = _method_medians(filtered_rows, metric=filtered_metric)
        baseline_holdout = (
            _holdout_rate(baseline_rows, metric=baseline_metric, group_key="material"),
            _holdout_rate(baseline_rows, metric=baseline_metric, group_key="treatment"),
        )
        filtered_holdout = (
            _holdout_rate(filtered_rows, metric=filtered_metric, group_key="material"),
            _holdout_rate(filtered_rows, metric=filtered_metric, group_key="treatment"),
        )
        lines.append(
            " & ".join(
                [
                    label,
                    _triplet(baseline_medians),
                    _triplet(filtered_medians),
                    f"${baseline_holdout[0]:.1f} / {baseline_holdout[1]:.1f}$",
                    f"${filtered_holdout[0]:.1f} / {filtered_holdout[1]:.1f}$",
                ]
            )
            + " "
            + ROW_END
        )
    lines.extend(
        [
            "\\bottomrule",
            "\\end{tabular}",
            "}%",
            "\\end{table}",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def _repeat_summary(rows: list[dict[str, str]]) -> str:
    counts: list[int] = []
    grouped: dict[tuple[str, str], int] = defaultdict(int)
    for row in rows:
        grouped[(row["stem"], row["method"])] += 1
    counts = sorted(grouped.values())
    if not counts:
        return "$n_\\mathrm{rep}=0$"
    if counts[0] == counts[-1]:
        return f"$n_\\mathrm{{rep}}={counts[0]}$"
    return f"$n_\\mathrm{{rep}}={counts[0]}\\ldots {counts[-1]}$"


def main() -> None:
    ap = argparse.ArgumentParser(description="Run the paper roughness-filter sensitivity control")
    ap.add_argument("inputs", nargs="*", default=["data/*.sur"], help="SUR files or glob patterns under the repo root")
    ap.add_argument("--baseline-per-surface", type=Path, default=Path("outputs/paper_alicona_benchmark/per_surface.csv"))
    ap.add_argument("--tag", type=str, default="paper_alicona_benchmark")
    ap.add_argument("--subdir", type=str, default="roughness_filter_control")
    ap.add_argument("--table-out", type=Path, default=Path("manuscript/tables/benchmark_roughness_filter_control.tex"))
    ap.add_argument("--summary-out", type=Path, default=None)
    ap.add_argument("--nx", type=int, default=256)
    ap.add_argument("--ny", type=int, default=256)
    ap.add_argument("--jobs", type=int, default=0)
    ap.add_argument("--nreps", type=int, default=4)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--s-filter-um", type=float, default=2.5)
    ap.add_argument("--l-filter-um", type=float, default=80.0)
    args = ap.parse_args()

    root = Path(__file__).resolve().parents[1]
    py = sys.executable
    expanded_inputs = _expand_inputs(root, list(args.inputs))
    outdir = root / "outputs" / str(args.tag) / str(args.subdir)
    filtered_per_surface = outdir / "per_surface.csv"
    summary_out = args.summary_out or (outdir / "summary.csv")

    cmd = [
        py,
        str(root / "scripts" / "benchmark_sur_interferometry.py"),
        *expanded_inputs,
        "--outdir",
        str(outdir),
        "--nx",
        str(int(args.nx)),
        "--ny",
        str(int(args.ny)),
        "--sur-resample",
        "area",
        "--nreps",
        str(int(args.nreps)),
        "--jobs",
        str(int(args.jobs)),
        "--roughness-s-filter-um",
        str(float(args.s_filter_um)),
        "--roughness-l-filter-um",
        str(float(args.l_filter_um)),
    ]
    if int(args.limit) > 0:
        cmd.extend(["--limit", str(int(args.limit))])
    _run(cmd)

    baseline_rows_raw = _load_rows((root / args.baseline_per_surface).resolve() if not args.baseline_per_surface.is_absolute() else args.baseline_per_surface)
    filtered_rows_raw = _load_rows(filtered_per_surface)
    baseline_rows = _surface_level_rows(baseline_rows_raw, ["bias_Sa_bw_nm", "bias_Sq_bw_nm", "bias_Sz_bw_nm"])
    filtered_rows = _surface_level_rows(
        filtered_rows_raw,
        ["bias_Sa_bw_nm", "bias_Sq_bw_nm", "bias_Sz_bw_nm", "bias_Sa_iso_nm", "bias_Sq_iso_nm", "bias_Sz_iso_nm"],
    )
    n_surfaces = len({str(row["stem"]) for row in baseline_rows})
    rep_summary = _repeat_summary(filtered_rows_raw)
    table_out = (root / args.table_out).resolve() if not args.table_out.is_absolute() else args.table_out
    _write_summary(summary_out if summary_out.is_absolute() else (root / summary_out), baseline_rows=baseline_rows, filtered_rows=filtered_rows)
    _write_table(
        table_out,
        baseline_rows=baseline_rows,
        filtered_rows=filtered_rows,
        n_surfaces=n_surfaces,
        n_reps=rep_summary,
        s_filter_um=float(args.s_filter_um),
        l_filter_um=float(args.l_filter_um),
    )
    print(f"Wrote: {filtered_per_surface}")
    print(f"Wrote: {summary_out}")
    print(f"Wrote: {table_out}")


if __name__ == "__main__":
    main()