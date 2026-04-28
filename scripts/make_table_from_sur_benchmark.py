"""Generate LaTeX tables from measured benchmark CSV outputs.

The script supports two input shapes:
    1) grouped CSVs like by_material.csv / by_treatment.csv with legacy
         ``*_mean`` / ``*_std`` columns,
    2) per_surface.csv, from which robust surface-level summaries are computed
         after collapsing repeated runs within each surface and method.

Example:
    python scripts/make_table_from_sur_benchmark.py \
        --grouped outputs/paper_alicona_benchmark/per_surface.csv \
        --out manuscript/tables/alicona_rmse_by_material.tex \
        --group-key material \
        --metric height_rmse_nm \
        --summary-style median_iqr
"""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple, TypedDict

import numpy as np


class GroupedCell(TypedDict):
    n: int
    mean: float
    std: float


class RobustCell(TypedDict):
    n: int
    median: float
    q1: float
    q3: float


def _f(x: str) -> float:
    return float(x.strip())


def _i(x: str) -> int:
    return int(float(x.strip()))


def _latex_escape(s: str) -> str:
    return s.replace("_", "\\_")


def _fmt_num(x: float, *, digits: int) -> str:
    return f"{x:.{digits}f}"


def _pretty_method(m: str) -> str:
    if m == "classical":
        return "Classical"
    if m == "quantum_like":
        return "Coincidence-proxy"
    if m == "hybrid":
        return "Hybrid"
    return _latex_escape(m)


def _group_order(groups_set: set[str], *, group_key: str) -> List[str]:
    groups = sorted(groups_set)
    if group_key == "treatment":
        preferred_groups = [
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
        order = {g: i for i, g in enumerate(preferred_groups)}
        groups.sort(key=lambda g: (order.get(g, 10_000), g))
    return groups


def _method_order(methods_set: set[str]) -> List[str]:
    preferred = ["classical", "quantum_like", "hybrid"]
    return [m for m in preferred if m in methods_set] + sorted([m for m in methods_set if m not in preferred])


def read_grouped_csv(path: Path, *, group_key: str, metric: str) -> Tuple[List[str], List[str], Dict[Tuple[str, str], GroupedCell]]:
    """Return (groups, methods, lookup[(group,method)] -> {n, mean, std})."""

    lookup: Dict[Tuple[str, str], GroupedCell] = {}
    groups_set: set[str] = set()
    methods_set: set[str] = set()

    with path.open("r", encoding="utf-8") as f:
        r = csv.DictReader(f)
        mean_k = f"{metric}_mean"
        std_k = f"{metric}_std"
        for d in r:
            g = str(d.get(group_key, ""))
            m = str(d.get("method", ""))
            if g == "" or m == "":
                continue
            groups_set.add(g)
            methods_set.add(m)
            lookup[(g, m)] = {
                "n": _i(str(d.get("n", "0"))),
                "mean": _f(str(d.get(mean_k, "nan"))),
                "std": _f(str(d.get(std_k, "nan"))),
            }

    groups = _group_order(groups_set, group_key=group_key)
    methods = _method_order(methods_set)
    return groups, methods, lookup


def read_per_surface_robust_csv(
    path: Path,
    *,
    group_key: str,
    metric: str,
) -> Tuple[List[str], List[str], Dict[Tuple[str, str], RobustCell]]:
    """Return robust summaries over unique surfaces.

    Repeated runs within each (stem, method) are collapsed by the median first,
    then group-level medians and quartiles are computed across surfaces.
    """

    with path.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise SystemExit(f"No rows found in {path}")

    if any(key not in rows[0] for key in ("stem", "method", group_key, metric)):
        missing = [key for key in ("stem", "method", group_key, metric) if key not in rows[0]]
        raise SystemExit(f"Missing required columns for robust summary in {path}: {missing}")

    by_surface: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        stem = str(row.get("stem", "")).strip()
        method = str(row.get("method", "")).strip()
        if not stem or not method:
            continue
        by_surface[(stem, method)].append(row)

    collapsed: list[dict[str, object]] = []
    for (_, method), entries in sorted(by_surface.items()):
        first = entries[0]
        values = np.array([float(entry[metric]) for entry in entries], dtype=float)
        collapsed.append(
            {
                group_key: str(first[group_key]),
                "method": str(method),
                "metric": float(np.median(values)),
            }
        )

    grouped_values: dict[tuple[str, str], list[float]] = defaultdict(list)
    groups_set: set[str] = set()
    methods_set: set[str] = set()
    for row in collapsed:
        group = str(row[group_key])
        method = str(row["method"])
        groups_set.add(group)
        methods_set.add(method)
        grouped_values[(group, method)].append(float(row["metric"]))

    lookup: Dict[Tuple[str, str], RobustCell] = {}
    for key, values in grouped_values.items():
        arr = np.array(values, dtype=float)
        lookup[key] = {
            "n": int(arr.size),
            "median": float(np.median(arr)),
            "q1": float(np.percentile(arr, 25.0)),
            "q3": float(np.percentile(arr, 75.0)),
        }

    groups = _group_order(groups_set, group_key=group_key)
    methods = _method_order(methods_set)
    return groups, methods, lookup


def write_table(
    *,
    grouped_csv: Path,
    out: Path,
    group_key: str,
    metric: str,
    caption: str,
    label: str,
    digits: int,
    include_n: bool,
    summary_style: str,
) -> None:
    with grouped_csv.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])

    source_is_grouped = f"{metric}_mean" in fieldnames
    if summary_style == "median_iqr":
        if source_is_grouped:
            raise SystemExit("median_iqr summary requires per_surface.csv input, not grouped mean/std CSVs")
        groups, methods, lookup = read_per_surface_robust_csv(grouped_csv, group_key=group_key, metric=metric)
    else:
        groups, methods, lookup = read_grouped_csv(grouped_csv, group_key=group_key, metric=metric)

    if not groups:
        raise SystemExit(f"No groups found in {grouped_csv}")

    out.parent.mkdir(parents=True, exist_ok=True)

    if summary_style == "median_iqr":
        colspec = "l" + ("r" if include_n else "") + ("c" * len(methods))
    else:
        # Align the \pm symbols by splitting each method column into:
        #   mean  (right-aligned)  ±  std (left-aligned)
        pm_col = "r@{\\,\\ensuremath{\\pm}\\,}r"
        colspec = "l" + ("r" if include_n else "") + (pm_col * len(methods))

    lines: List[str] = []
    lines.append("% Auto-generated by scripts/make_table_from_sur_benchmark.py")
    lines.append("\\begin{table}[H]")
    lines.append("\\centering")
    lines.append("\\footnotesize")
    lines.append("\\setlength{\\tabcolsep}{2.8pt}")
    lines.append(f"\\caption{{{caption}}}")
    lines.append(f"\\label{{{label}}}")
    lines.append("\\resizebox{\\textwidth}{!}{%")
    lines.append(f"\\begin{{tabular}}{{{colspec}}}")
    lines.append("\\toprule")

    header = [_latex_escape(group_key.title())]
    if include_n:
        header.append("n")
    if summary_style == "median_iqr":
        header += [_pretty_method(m) for m in methods]
    else:
        header += [f"\\multicolumn{{2}}{{c}}{{{_pretty_method(m)}}}" for m in methods]
    lines.append(" & ".join(header) + " \\\\")
    lines.append("\\midrule")

    for g in groups:
        row = [_latex_escape(g)]
        if include_n:
            ns = [int(lookup[(g, m)]["n"]) for m in methods if (g, m) in lookup]
            n = max(ns) if ns else 0
            row.append(str(n))
        for m in methods:
            cell = lookup.get((g, m))
            if cell is None:
                if summary_style == "median_iqr":
                    row.append("--")
                else:
                    row.append("--")
                    row.append("--")
            else:
                if summary_style == "median_iqr":
                    median_s = _fmt_num(float(cell["median"]), digits=digits)
                    q1_s = _fmt_num(float(cell["q1"]), digits=digits)
                    q3_s = _fmt_num(float(cell["q3"]), digits=digits)
                    row.append(f"${median_s}$ [${q1_s}$, ${q3_s}$]")
                else:
                    mean_s = _fmt_num(float(cell["mean"]), digits=digits)
                    std_s = _fmt_num(float(cell["std"]), digits=digits)
                    row.append(f"${mean_s}$")
                    row.append(f"${std_s}$")
        lines.append(" & ".join(row) + " \\\\")

    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    lines.append("}%")
    lines.append("\\end{table}")
    lines.append("")

    out.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate LaTeX table from sur benchmark grouped CSV")
    ap.add_argument("--grouped", type=str, required=True, help="Path to by_material.csv or by_treatment.csv")
    ap.add_argument("--out", type=str, required=True, help="Output .tex file")
    ap.add_argument("--group-key", type=str, required=True, choices=["material", "treatment"], help="Grouping key")
    ap.add_argument("--metric", type=str, default="height_rmse_nm", help="Metric base name (e.g. height_rmse_nm)")
    ap.add_argument("--digits", type=int, default=1)
    ap.add_argument(
        "--caption",
        type=str,
        default="Height RMSE (after plane detrending), mean $\\pm$ std over repeats.",
    )
    ap.add_argument(
        "--summary-style",
        type=str,
        choices=["mean_std", "median_iqr"],
        default="mean_std",
        help="Whether to render legacy mean±std summaries or robust median [Q1, Q3] summaries.",
    )
    ap.add_argument(
        "--include-n",
        action="store_true",
        help="Include an 'n' column with the number of surfaces per group.",
    )
    ap.add_argument("--label", type=str, default="tab:alicona_rmse")

    args = ap.parse_args()

    write_table(
        grouped_csv=Path(args.grouped),
        out=Path(args.out),
        group_key=str(args.group_key),
        metric=str(args.metric),
        caption=str(args.caption),
        label=str(args.label),
        digits=int(args.digits),
        include_n=bool(args.include_n),
        summary_style=str(args.summary_style),
    )
    print(f"Wrote: {args.out}")


if __name__ == "__main__":
    main()
