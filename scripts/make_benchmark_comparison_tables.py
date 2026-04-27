#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import math
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy.stats import wilcoxon


METHOD_ORDER = ["classical", "quantum_like", "hybrid"]
METHOD_LABEL = {
    "classical": "Classical",
    "quantum_like": "Quantum-like",
    "hybrid": "Hybrid",
}

ROW_END = "\\\\"

METRICS = [
    ("Height RMSE", "height_rmse_nm", False),
    (r"$|\Delta S_a|$", "bias_Sa_nm", True),
    (r"$|\Delta S_q|$", "bias_Sq_nm", True),
    (r"$|\Delta S_z|$", "bias_Sz_nm", True),
]

PAIR_ORDER = [
    ("hybrid", "classical", "Hybrid vs Classical"),
    ("hybrid", "quantum_like", "Hybrid vs Quantum-like"),
    ("quantum_like", "classical", "Quantum-like vs Classical"),
]


def _load_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise ValueError(f"No rows found in {path}")
    return rows


def _collapse_surface_rows(rows: list[dict[str, str]]) -> dict[str, dict[str, dict[str, float]]]:
    grouped: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[(str(row["stem"]), str(row["method"]))].append(row)

    out: dict[str, dict[str, dict[str, float]]] = defaultdict(dict)
    for (stem, method), entries in grouped.items():
        if method not in METHOD_ORDER:
            continue
        collapsed = {
            "Sa_true_nm": float(np.median([float(entry["Sa_true_nm"]) for entry in entries])),
            "height_rmse_nm": float(np.median([float(entry["height_rmse_nm"]) for entry in entries])),
            "bias_Sa_nm": float(np.median([float(entry["bias_Sa_nm"]) for entry in entries])),
            "bias_Sq_nm": float(np.median([float(entry["bias_Sq_nm"]) for entry in entries])),
            "bias_Sz_nm": float(np.median([float(entry["bias_Sz_nm"]) for entry in entries])),
        }
        out[stem][method] = collapsed
    return dict(out)


def _surface_count(surface_map: dict[str, dict[str, dict[str, float]]]) -> int:
    return sum(1 for method_map in surface_map.values() if any(method in method_map for method in METHOD_ORDER))


def _winner_counts(
    surface_map: dict[str, dict[str, dict[str, float]]],
    *,
    metric_key: str,
    use_abs: bool,
    sa_min: float | None,
    sa_max: float | None,
) -> dict[str, int]:
    counts = {method: 0 for method in METHOD_ORDER}
    for _, method_map in surface_map.items():
        if len(method_map) < 2:
            continue
        sa_true = float(np.mean([vals["Sa_true_nm"] for vals in method_map.values()]))
        if sa_min is not None and sa_true < sa_min:
            continue
        if sa_max is not None and sa_true >= sa_max:
            continue
        best_method = None
        best_value = None
        for method in METHOD_ORDER:
            vals = method_map.get(method)
            if vals is None:
                continue
            value = float(vals[metric_key])
            if use_abs:
                value = abs(value)
            if best_value is None or value < best_value:
                best_value = value
                best_method = method
        if best_method is not None:
            counts[best_method] += 1
    return counts


def _format_pvalue(pvalue: float) -> str:
    if pvalue < 0.05:
        exponent = int(math.floor(math.log10(pvalue)))
        mantissa = pvalue / (10 ** exponent)
        return f"${mantissa:.1f}\\times 10^{{{exponent}}}$"
    return f"${pvalue:.3f}$"


def _paired_values(
    surface_map: dict[str, dict[str, dict[str, float]]],
    *,
    metric_key: str,
    use_abs: bool,
    method_a: str,
    method_b: str,
) -> tuple[np.ndarray, np.ndarray]:
    vals_a: list[float] = []
    vals_b: list[float] = []
    for _, method_map in sorted(surface_map.items()):
        if method_a not in method_map or method_b not in method_map:
            continue
        a = float(method_map[method_a][metric_key])
        b = float(method_map[method_b][metric_key])
        if use_abs:
            a = abs(a)
            b = abs(b)
        vals_a.append(a)
        vals_b.append(b)
    return np.array(vals_a, dtype=float), np.array(vals_b, dtype=float)


def _paired_effect_summary(
    surface_map: dict[str, dict[str, dict[str, float]]],
    *,
    metric_key: str,
    use_abs: bool,
    method_a: str,
    method_b: str,
) -> tuple[float, float, int]:
    vals_a, vals_b = _paired_values(
        surface_map,
        metric_key=metric_key,
        use_abs=use_abs,
        method_a=method_a,
        method_b=method_b,
    )
    if vals_a.size == 0:
        return float("nan"), float("nan"), 0
    diff = vals_a - vals_b
    wins = int(np.sum(vals_a < vals_b))
    return float(np.median(diff)), float(100.0 * wins / vals_a.size), int(vals_a.size)


def _write_dominance_table(path: Path, surface_map: dict[str, dict[str, dict[str, float]]]) -> None:
    lines = [
        "% Auto-generated by scripts/make_benchmark_comparison_tables.py",
        "\\begin{table}[t]",
        "\\centering",
        "\\footnotesize",
        "\\setlength{\\tabcolsep}{4pt}",
        "\\caption{Per-surface winner counts in the measured-surface benchmark. For each measured \\texttt{.sur} surface, the ``winner'' is the method with the lowest height RMSE or the smallest absolute roughness bias for the stated endpoint. The low-roughness column isolates the smoother group ($S_a<500$~nm), whereas the rougher column aggregates the two highest roughness bins ($S_a\\geq 1000$~nm).}",
        "\\label{tab:dominance_summary}",
        "\\resizebox{\\textwidth}{!}{%",
        "\\begin{tabular}{p{3.4cm}ccc ccc ccc}",
        "\\toprule",
        r"& \multicolumn{3}{c}{All measured surfaces} & \multicolumn{3}{c}{$S_a<500$~nm} & \multicolumn{3}{c}{$S_a\geq 1000$~nm}" + ROW_END,
        r"Endpoint & Classical & Quantum-like & Hybrid & Classical & Quantum-like & Hybrid & Classical & Quantum-like & Hybrid" + ROW_END,
        "\\midrule",
    ]
    for endpoint, metric_key, use_abs in METRICS:
        all_counts = _winner_counts(surface_map, metric_key=metric_key, use_abs=use_abs, sa_min=None, sa_max=None)
        low_counts = _winner_counts(surface_map, metric_key=metric_key, use_abs=use_abs, sa_min=None, sa_max=500.0)
        rough_counts = _winner_counts(surface_map, metric_key=metric_key, use_abs=use_abs, sa_min=1000.0, sa_max=None)
        row = [endpoint]
        row.extend(str(all_counts[m]) for m in METHOD_ORDER)
        row.extend(str(low_counts[m]) for m in METHOD_ORDER)
        row.extend(str(rough_counts[m]) for m in METHOD_ORDER)
        lines.append(" & ".join(row) + " " + ROW_END)
    lines.extend([
        "\\bottomrule",
        "\\end{tabular}",
        "}%",
        "\\end{table}",
        "",
    ])
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_wilcoxon_table(path: Path, surface_map: dict[str, dict[str, dict[str, float]]]) -> None:
    n_surfaces = _surface_count(surface_map)
    lines = [
        "% Auto-generated by scripts/make_benchmark_comparison_tables.py",
        "\\begin{table}[t]",
        "\\centering",
        "\\footnotesize",
        "\\setlength{\\tabcolsep}{5pt}",
        f"\\caption{{Exploratory paired Wilcoxon signed-rank tests across $n={int(n_surfaces)}$ measured surfaces. Reported are uncorrected two-sided $p$-values for paired surface-level errors after collapsing repeated runs within each surface and method; they are included as descriptive checks rather than as multiplicity-controlled confirmatory inference.}}",
        "\\label{tab:benchmark_wilcoxon}",
        "\\begin{tabular}{lccc}",
        "\\toprule",
        "Endpoint & Hybrid vs Classical & Hybrid vs Quantum-like & Quantum-like vs Classical " + ROW_END,
        "\\midrule",
    ]
    for endpoint, metric_key, use_abs in METRICS:
        row = [endpoint]
        for method_a, method_b, _ in PAIR_ORDER:
            vals_a, vals_b = _paired_values(
                surface_map,
                metric_key=metric_key,
                use_abs=use_abs,
                method_a=method_a,
                method_b=method_b,
            )
            _, pvalue = wilcoxon(vals_a, vals_b, alternative="two-sided")
            row.append(_format_pvalue(float(pvalue)))
        lines.append(" & ".join(row) + " " + ROW_END)
    lines.extend([
        "\\bottomrule",
        "\\end{tabular}",
        "\\end{table}",
        "",
    ])
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_effects_table(path: Path, surface_map: dict[str, dict[str, dict[str, float]]]) -> None:
    n_surfaces = _surface_count(surface_map)
    lines = [
        "% Auto-generated by scripts/make_benchmark_comparison_tables.py",
        "\\begin{table}[t]",
        "\\centering",
        "\\footnotesize",
        "\\setlength{\\tabcolsep}{4pt}",
        f"\\caption{{Paired effect summary across $n={int(n_surfaces)}$ measured surfaces. Each entry reports the median signed surface-level error difference (first method minus second; negative values favour the first method) together with the percentage of surfaces on which the first method attains the lower error.}}",
        "\\label{tab:benchmark_paired_effects}",
        "\\resizebox{\\textwidth}{!}{%",
        "\\begin{tabular}{lrr r r r r}",
        "\\toprule",
        r"& \multicolumn{2}{c}{Hybrid $-$ Classical} & \multicolumn{2}{c}{Hybrid $-$ Quantum-like} & \multicolumn{2}{c}{Quantum-like $-$ Classical}" + ROW_END,
        r"Endpoint & Median $\Delta$ (nm) & Wins (\%) & Median $\Delta$ (nm) & Wins (\%) & Median $\Delta$ (nm) & Wins (\%)" + ROW_END,
        "\\midrule",
    ]
    for endpoint, metric_key, use_abs in METRICS:
        row = [endpoint]
        for method_a, method_b, _ in PAIR_ORDER:
            median_diff, win_rate, _ = _paired_effect_summary(
                surface_map,
                metric_key=metric_key,
                use_abs=use_abs,
                method_a=method_a,
                method_b=method_b,
            )
            row.append(f"${median_diff:.1f}$")
            row.append(f"${win_rate:.1f}$")
        lines.append(" & ".join(row) + " " + ROW_END)
    lines.extend([
        "\\bottomrule",
        "\\end{tabular}",
        "}%",
        "\\end{table}",
        "",
    ])
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="Create dominance and Wilcoxon LaTeX tables from per_surface.csv")
    ap.add_argument("--per-surface", type=Path, default=Path("outputs/paper_alicona_benchmark/per_surface.csv"))
    ap.add_argument("--dominance-out", type=Path, default=Path("manuscript/tables/dominance_summary.tex"))
    ap.add_argument("--wilcoxon-out", type=Path, default=Path("manuscript/tables/benchmark_wilcoxon.tex"))
    ap.add_argument("--effects-out", type=Path, default=Path("manuscript/tables/benchmark_paired_effects.tex"))
    args = ap.parse_args()

    rows = _load_rows(args.per_surface)
    surface_map = _collapse_surface_rows(rows)
    args.dominance_out.parent.mkdir(parents=True, exist_ok=True)
    args.wilcoxon_out.parent.mkdir(parents=True, exist_ok=True)
    args.effects_out.parent.mkdir(parents=True, exist_ok=True)
    _write_dominance_table(args.dominance_out, surface_map)
    _write_wilcoxon_table(args.wilcoxon_out, surface_map)
    _write_effects_table(args.effects_out, surface_map)
    print(f"Wrote: {args.dominance_out}")
    print(f"Wrote: {args.wilcoxon_out}")
    print(f"Wrote: {args.effects_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())