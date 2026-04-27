#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path

import numpy as np


ROW_END = "\\\\"


METHOD_ORDER = ["classical", "quantum_like", "hybrid"]
METHOD_LABEL = {
    "classical": "Classical",
    "quantum_like": "Quantum-like",
    "hybrid": "Hybrid",
}

METRICS = [
    ("height_rmse_nm", False, "Height RMSE (nm)"),
    ("bias_Sa_nm", True, "$|\\Delta S_a|$ (nm)"),
    ("bias_Sq_nm", True, "$|\\Delta S_q|$ (nm)"),
    ("bias_Sz_nm", True, "$|\\Delta S_z|$ (nm)"),
]

TOLERANCE_SPECS = [
    ("height_rmse_nm", False, "Sq_true_nm", 1.0, r"Height RMSE $> S_q^\mathrm{ref}$"),
    ("bias_Sa_nm", True, "Sa_true_nm", 0.5, r"$|\Delta S_a| > 0.5 S_a^\mathrm{ref}$"),
    ("bias_Sq_nm", True, "Sq_true_nm", 0.5, r"$|\Delta S_q| > 0.5 S_q^\mathrm{ref}$"),
    ("bias_Sz_nm", True, "Sz_true_nm", 0.5, r"$|\Delta S_z| > 0.5 S_z^\mathrm{ref}$"),
]


def _load_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise ValueError(f"No rows found in {path}")
    return rows


def _group_surface_rows(rows: list[dict[str, str]]) -> dict[tuple[str, str], list[dict[str, str]]]:
    grouped: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[(row["stem"], row["method"])].append(row)
    return grouped


def _surface_level_values(rows: list[dict[str, str]]) -> dict[str, dict[str, list[float]]]:
    grouped = _group_surface_rows(rows)
    out: dict[str, dict[str, list[float]]] = {metric: {m: [] for m in METHOD_ORDER} for metric, _, _ in METRICS}
    for (_, method), entries in sorted(grouped.items()):
        if method not in METHOD_ORDER:
            continue
        for metric, use_abs, _ in METRICS:
            vals = np.array([float(entry[metric]) for entry in entries], dtype=float)
            if use_abs:
                vals = np.abs(vals)
            out[metric][method].append(float(np.median(vals)))
    return out


def _surface_level_rows(rows: list[dict[str, str]]) -> list[dict[str, object]]:
    grouped: dict[str, dict[str, list[dict[str, str]]]] = defaultdict(lambda: defaultdict(list))
    for row in rows:
        grouped[row["stem"]][row["method"]].append(row)

    numeric_keys = {
        "height_rmse_nm",
        "bias_Sa_nm",
        "bias_Sq_nm",
        "bias_Sz_nm",
        "Sa_true_nm",
        "Sq_true_nm",
        "Sz_true_nm",
    }
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


def _repeat_count_summary(rows: list[dict[str, str]]) -> tuple[int, int]:
    counts = [len(entries) for entries in _group_surface_rows(rows).values()]
    if not counts:
        return 0, 0
    return int(min(counts)), int(max(counts))


def _bootstrap_ci(values: list[float], *, nboot: int, seed: int) -> tuple[float, float, float]:
    arr = np.array(values, dtype=float)
    if arr.size == 0:
        return float("nan"), float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, arr.size, size=(nboot, arr.size))
    boots = np.median(arr[idx], axis=1)
    return float(np.median(arr)), float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))


def _format_ci(mid: float, lo: float, hi: float, digits: int) -> str:
    fmt = f"{{:.{digits}f}}"
    return f"${fmt.format(mid)}$ [$${fmt.format(lo)}$$, $${fmt.format(hi)}$$]".replace("$$", "$")


def _format_median_iqr(mid: float, q1: float, q3: float, digits: int) -> str:
    if not np.isfinite(mid):
        return "--"
    fmt = f"{{:.{digits}f}}"
    return f"${fmt.format(mid)}$ [$${fmt.format(q1)}$$, $${fmt.format(q3)}$$]".replace("$$", "$")


def _surface_count(surface_values: dict[str, dict[str, list[float]]]) -> int:
    counts = [len(values) for by_method in surface_values.values() for values in by_method.values()]
    return max(counts) if counts else 0


def _method_medians(rows: list[dict[str, object]], *, metric: str, use_abs: bool) -> dict[str, float]:
    medians: dict[str, float] = {}
    for method in METHOD_ORDER:
        vals = [float(row[metric]) for row in rows if str(row["method"]) == method]
        if not vals:
            continue
        arr = np.array(vals, dtype=float)
        if use_abs:
            arr = np.abs(arr)
        medians[method] = float(np.median(arr))
    return medians


def _winning_method(rows: list[dict[str, object]], *, metric: str, use_abs: bool) -> str | None:
    medians = _method_medians(rows, metric=metric, use_abs=use_abs)
    if not medians:
        return None
    return min(medians, key=medians.get)


def _within_surface_dispersion(rows: list[dict[str, str]], *, metric: str, use_abs: bool) -> dict[str, tuple[float, float, float]]:
    grouped = _group_surface_rows(rows)
    out: dict[str, tuple[float, float, float]] = {}
    for method in METHOD_ORDER:
        iqr_values: list[float] = []
        for (_, row_method), entries in grouped.items():
            if row_method != method:
                continue
            vals = np.array([float(entry[metric]) for entry in entries], dtype=float)
            if use_abs:
                vals = np.abs(vals)
            if vals.size < 2:
                continue
            q1, q3 = np.percentile(vals, [25.0, 75.0])
            iqr_values.append(float(q3 - q1))
        if not iqr_values:
            out[method] = (float("nan"), float("nan"), float("nan"))
            continue
        arr = np.array(iqr_values, dtype=float)
        out[method] = (
            float(np.median(arr)),
            float(np.percentile(arr, 25.0)),
            float(np.percentile(arr, 75.0)),
        )
    return out


def _triplet_string(counts: dict[str, int]) -> str:
    return f"${counts['classical']} / {counts['quantum_like']} / {counts['hybrid']}$"


def _write_bootstrap_table(
    path: Path,
    surface_values: dict[str, dict[str, list[float]]],
    *,
    nboot: int,
    seed: int,
    n_surfaces: int,
    rep_summary: str,
) -> None:
    lines = [
        "% Auto-generated by scripts/make_benchmark_stat_tables.py",
        "\\begin{table}[t]",
        "\\centering",
        "\\footnotesize",
        "\\setlength{\\tabcolsep}{4pt}",
        f"\\caption{{Measured-surface benchmark summary using surface-level medians over $n={int(n_surfaces)}$ unique measured surfaces with percentile bootstrap 95\\% confidence intervals. The canonical paper benchmark uses {rep_summary} Monte Carlo realisations per surface and method; repeated runs are collapsed within each surface before between-surface uncertainty is estimated.}}",
        "\\label{tab:benchmark_bootstrap_ci}",
        "\\resizebox{\\textwidth}{!}{%",
        "\\begin{tabular}{lccc}",
        "\\toprule",
        r"Endpoint & Classical & Quantum-like & Hybrid " + ROW_END,
        "\\midrule",
    ]
    for metric, _, label in METRICS:
        row = [label]
        for method_idx, method in enumerate(METHOD_ORDER):
            mid, lo, hi = _bootstrap_ci(surface_values[metric][method], nboot=nboot, seed=seed + 97 * method_idx)
            row.append(_format_ci(mid, lo, hi, 1))
        lines.append(" & ".join(row) + " " + ROW_END)
    lines.extend([
        "\\bottomrule",
        "\\end{tabular}",
        "}%",
        "\\end{table}",
    ])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_tolerance_table(path: Path, surface_rows: list[dict[str, object]], *, n_surfaces: int) -> None:
    rates: dict[str, dict[str, float]] = {metric: {} for metric, _, _, _, _ in TOLERANCE_SPECS}
    for metric, use_abs, ref_key, scale, _ in TOLERANCE_SPECS:
        failures = {method: 0 for method in METHOD_ORDER}
        totals = {method: 0 for method in METHOD_ORDER}
        for row in surface_rows:
            method = str(row["method"])
            if method not in METHOD_ORDER:
                continue
            value = float(row[metric])
            ref_value = float(row[ref_key])
            if use_abs:
                value = abs(value)
            threshold = float(scale) * ref_value
            totals[method] += 1
            if value > threshold:
                failures[method] += 1
        for method in METHOD_ORDER:
            rates[metric][method] = 100.0 * failures[method] / max(totals[method], 1)

    lines = [
        "% Auto-generated by scripts/make_benchmark_stat_tables.py",
        "\\begin{table}[t]",
        "\\centering",
        "\\footnotesize",
        "\\setlength{\\tabcolsep}{5pt}",
        f"\\caption{{Endpoint-referenced tolerance-exceedance rate in the measured-surface benchmark over $n={int(n_surfaces)}$ unique surfaces. For each surface, the reported percentage counts reconstructions whose surface-level error exceeds a descriptor-scaled tolerance band: Height RMSE greater than the FV reference $S_q$, or roughness bias magnitude greater than 50\\% of the corresponding FV reference descriptor. These bands are used here as practical selection thresholds rather than as universal acceptance standards.}}",
        "\\label{tab:benchmark_tolerance_rates}",
        "\\begin{tabular}{lccc}",
        "\\toprule",
        r"Endpoint & Classical & Quantum-like & Hybrid " + ROW_END,
        "\\midrule",
    ]
    for metric, _, _, _, label in TOLERANCE_SPECS:
        row = [label]
        for method in METHOD_ORDER:
            row.append(f"${rates[metric][method]:.1f}$")
        lines.append(" & ".join(row) + " " + ROW_END)
    lines.extend([
        "\\bottomrule",
        "\\end{tabular}",
        "\\end{table}",
    ])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_repeatability_table(path: Path, rows: list[dict[str, str]], *, n_surfaces: int, rep_summary: str) -> None:
    lines = [
        "% Auto-generated by scripts/make_benchmark_stat_tables.py",
        "\\begin{table}[t]",
        "\\centering",
        "\\footnotesize",
        "\\setlength{\\tabcolsep}{4pt}",
        f"\\caption{{Within-surface stochastic dispersion in the measured-surface benchmark over $n={int(n_surfaces)}$ unique surfaces. Entries report the median per-surface interquartile range of repeated-run errors, with first and third quartiles in brackets, using {rep_summary} Monte Carlo realisations per surface and method. Lower values indicate better repeatability under the simulator's stochastic shot-noise model.}}",
        "\\label{tab:benchmark_repeatability}",
        "\\resizebox{\\textwidth}{!}{%",
        "\\begin{tabular}{lccc}",
        "\\toprule",
        r"Endpoint & Classical & Quantum-like & Hybrid " + ROW_END,
        "\\midrule",
    ]
    for metric, use_abs, label in METRICS:
        row = [label]
        dispersion = _within_surface_dispersion(rows, metric=metric, use_abs=use_abs)
        for method in METHOD_ORDER:
            row.append(_format_median_iqr(*dispersion[method], digits=1))
        lines.append(" & ".join(row) + " " + ROW_END)
    lines.extend([
        "\\bottomrule",
        "\\end{tabular}",
        "}%",
        "\\end{table}",
        "",
    ])
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_holdout_table(
    path: Path,
    surface_rows: list[dict[str, object]],
    *,
    group_key: str,
    group_label: str,
    table_label: str,
) -> None:
    groups = sorted({str(row[group_key]) for row in surface_rows if str(row.get(group_key, ""))})
    lines = [
        "% Auto-generated by scripts/make_benchmark_stat_tables.py",
        "\\begin{table}[t]",
        "\\centering",
        "\\footnotesize",
        "\\setlength{\\tabcolsep}{4pt}",
        f"\\caption{{Leave-one-{group_label}-out stability of the measured-surface method ranking across $n={int(len(groups))}$ {group_label} groups. For each endpoint, the table reports the full-dataset winner, the counts of leave-one-{group_label}-out training winners and held-out winners in Classical / Quantum-like / Hybrid order, and the percentage of splits for which the training-set winner matches the held-out winner.}}",
        f"\\label{{{table_label}}}",
        "\\resizebox{\\textwidth}{!}{%",
        "\\begin{tabular}{lcccc}",
        "\\toprule",
        r"Endpoint & Full-data winner & Train winners (C/Q/H) & Holdout winners (C/Q/H) & Match rate (\%) " + ROW_END,
        "\\midrule",
    ]
    for metric, use_abs, label in METRICS:
        global_winner = _winning_method(surface_rows, metric=metric, use_abs=use_abs)
        train_counts = {method: 0 for method in METHOD_ORDER}
        holdout_counts = {method: 0 for method in METHOD_ORDER}
        matches = 0
        valid_splits = 0
        for group in groups:
            train_rows = [row for row in surface_rows if str(row.get(group_key, "")) != group]
            holdout_rows = [row for row in surface_rows if str(row.get(group_key, "")) == group]
            train_winner = _winning_method(train_rows, metric=metric, use_abs=use_abs)
            holdout_winner = _winning_method(holdout_rows, metric=metric, use_abs=use_abs)
            if train_winner is None or holdout_winner is None:
                continue
            train_counts[train_winner] += 1
            holdout_counts[holdout_winner] += 1
            valid_splits += 1
            if train_winner == holdout_winner:
                matches += 1
        match_rate = 100.0 * matches / max(valid_splits, 1)
        lines.append(
            " & ".join(
                [
                    label,
                    METHOD_LABEL.get(str(global_winner), "--"),
                    _triplet_string(train_counts),
                    _triplet_string(holdout_counts),
                    f"${match_rate:.1f}$",
                ]
            )
            + " "
            + ROW_END
        )
    lines.extend([
        "\\bottomrule",
        "\\end{tabular}",
        "}%",
        "\\end{table}",
        "",
    ])
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="Create bootstrap and tolerance-summary LaTeX tables from per_surface.csv")
    ap.add_argument("--per-surface", type=Path, default=Path("outputs/paper_alicona_benchmark/per_surface.csv"))
    ap.add_argument("--bootstrap-out", type=Path, default=Path("manuscript/tables/benchmark_bootstrap_ci.tex"))
    ap.add_argument(
        "--tolerance-out",
        "--failure-out",
        dest="tolerance_out",
        type=Path,
        default=Path("manuscript/tables/benchmark_tolerance_rates.tex"),
    )
    ap.add_argument("--repeatability-out", type=Path, default=Path("manuscript/tables/benchmark_repeatability.tex"))
    ap.add_argument("--holdout-out", type=Path, default=Path("manuscript/tables/benchmark_holdout_material.tex"))
    ap.add_argument(
        "--holdout-treatment-out",
        type=Path,
        default=Path("manuscript/tables/benchmark_holdout_treatment.tex"),
    )
    ap.add_argument("--nboot", type=int, default=4000)
    ap.add_argument("--seed", type=int, default=12345)
    args = ap.parse_args()

    rows = _load_rows(args.per_surface)
    surface_values = _surface_level_values(rows)
    surface_rows = _surface_level_rows(rows)
    n_surfaces = _surface_count(surface_values)
    rep_min, rep_max = _repeat_count_summary(rows)
    rep_summary = f"$n_\\mathrm{{rep}}={rep_min}$" if rep_min == rep_max else f"$n_\\mathrm{{rep}}={rep_min}\\ldots {rep_max}$"
    args.bootstrap_out.parent.mkdir(parents=True, exist_ok=True)
    args.tolerance_out.parent.mkdir(parents=True, exist_ok=True)
    args.repeatability_out.parent.mkdir(parents=True, exist_ok=True)
    args.holdout_out.parent.mkdir(parents=True, exist_ok=True)
    args.holdout_treatment_out.parent.mkdir(parents=True, exist_ok=True)
    _write_bootstrap_table(
        args.bootstrap_out,
        surface_values,
        nboot=int(args.nboot),
        seed=int(args.seed),
        n_surfaces=int(n_surfaces),
        rep_summary=rep_summary,
    )
    _write_tolerance_table(args.tolerance_out, surface_rows, n_surfaces=int(n_surfaces))
    _write_repeatability_table(args.repeatability_out, rows, n_surfaces=int(n_surfaces), rep_summary=rep_summary)
    _write_holdout_table(
        args.holdout_out,
        surface_rows,
        group_key="material",
        group_label="material",
        table_label="tab:benchmark_holdout_material",
    )
    _write_holdout_table(
        args.holdout_treatment_out,
        surface_rows,
        group_key="treatment",
        group_label="treatment",
        table_label="tab:benchmark_holdout_treatment",
    )
    print(f"Wrote: {args.bootstrap_out}")
    print(f"Wrote: {args.tolerance_out}")
    print(f"Wrote: {args.repeatability_out}")
    print(f"Wrote: {args.holdout_out}")
    print(f"Wrote: {args.holdout_treatment_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())