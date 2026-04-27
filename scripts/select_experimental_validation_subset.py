#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class SelectionRule:
    tier: str
    category: str
    rationale: str


def _median(values: list[float]) -> float:
    ordered = sorted(values)
    count = len(ordered)
    mid = count // 2
    if count % 2:
        return ordered[mid]
    return 0.5 * (ordered[mid - 1] + ordered[mid])


def _load_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError(f"No rows found in {path}")
    return rows


def _collapse_rows(path: Path) -> dict[str, dict[str, dict[str, object]]]:
    rows = _load_rows(path)
    grouped: dict[tuple[str, str], list[dict[str, str]]] = {}
    for row in rows:
        grouped.setdefault((row["stem"], row["method"]), []).append(row)

    non_numeric = {
        "file",
        "material",
        "material_code",
        "method",
        "rep",
        "sample_group",
        "stem",
        "sur_resample",
        "treatment",
        "treatment_code",
        "unwrap_method",
    }
    numeric_keys = [key for key in rows[0].keys() if key not in non_numeric]

    collapsed: dict[str, dict[str, dict[str, object]]] = {}
    for (stem, method), entries in sorted(grouped.items()):
        merged: dict[str, object] = {}
        exemplar = entries[0]
        for key in non_numeric:
            if key in exemplar:
                merged[key] = exemplar[key]
        for key in numeric_keys:
            values = [float(entry[key]) for entry in entries]
            merged[key] = _median(values)
        collapsed.setdefault(stem, {})[method] = merged
    return collapsed


def _candidate_metric(row: dict[str, object], key: str) -> float:
    value = row.get(key, 0.0)
    return float(value)


def _pick_first_unused(candidates: Iterable[tuple[str, str]], used: set[str]) -> tuple[str, str]:
    for stem, note in candidates:
        if stem not in used:
            used.add(stem)
            return stem, note
    raise RuntimeError("Unable to pick a unique validation surface for one of the selection rules")


def _surface_note(category: str, *, score: float) -> str:
    if category == "hybrid_best_height_case":
        return "Lowest hybrid height RMSE in the collapsed measured-surface benchmark"
    if category == "hybrid_median_height_case":
        return "Hybrid height RMSE closest to the dataset median"
    if category == "direct_q_catastrophic_failure_case":
        return f"Direct coincidence failure ratio versus best of classical/hybrid = {score:.1f}x"
    if category == "turning_rough_q_exception_case":
        return "Lowest direct coincidence height RMSE inside the turning (roughing) subset"
    if category == "classical_two_colour_nonuniqueness_case":
        return f"Classical two-colour beats direct coincidence on matched-bandwidth |Delta Sz| by {score:.1f} nm"
    if category == "detector_fragility_case":
        return f"Direct coincidence non-ideal detector penalty = +{score:.1f} nm height RMSE"
    if category == "wire_edm_rough_q_exception_case":
        return "Lowest direct coincidence height RMSE inside the wire-EDM (roughing) subset"
    if category == "sz_envelope_following_case":
        return f"Direct coincidence improves native-grid |Delta Sz| by {score:.1f} nm versus the best of classical/hybrid"
    raise KeyError(category)


def _selection_records(
    base_map: dict[str, dict[str, dict[str, object]]],
    classical_control_map: dict[str, dict[str, dict[str, object]]],
    nonideal_map: dict[str, dict[str, dict[str, object]]],
) -> list[dict[str, object]]:
    hybrid_rows = [
        (stem, _candidate_metric(methods["hybrid"], "height_rmse_nm"))
        for stem, methods in base_map.items()
        if "hybrid" in methods
    ]
    hybrid_rows.sort(key=lambda item: item[1])
    hybrid_median = _median([value for _, value in hybrid_rows])

    direct_failure_candidates: list[tuple[str, str]] = []
    turning_rough_candidates: list[tuple[str, str]] = []
    wire_edm_rough_candidates: list[tuple[str, str]] = []
    sz_envelope_candidates: list[tuple[str, str]] = []
    for stem, methods in base_map.items():
        if {"classical", "quantum_like", "hybrid"} <= methods.keys():
            classical_rmse = _candidate_metric(methods["classical"], "height_rmse_nm")
            quantum_rmse = _candidate_metric(methods["quantum_like"], "height_rmse_nm")
            hybrid_rmse = _candidate_metric(methods["hybrid"], "height_rmse_nm")
            best_other = min(classical_rmse, hybrid_rmse)
            failure_ratio = quantum_rmse / best_other if best_other > 0.0 else float("inf")
            direct_failure_candidates.append(
                (stem, _surface_note("direct_q_catastrophic_failure_case", score=failure_ratio))
            )

            treatment = str(methods["quantum_like"].get("treatment", ""))
            if treatment == "Turning (roughing)":
                turning_rough_candidates.append(
                    (stem, _surface_note("turning_rough_q_exception_case", score=quantum_rmse))
                )
            if treatment == "Wire EDM (roughing)":
                wire_edm_rough_candidates.append(
                    (stem, _surface_note("wire_edm_rough_q_exception_case", score=quantum_rmse))
                )

            q_sz = abs(_candidate_metric(methods["quantum_like"], "bias_Sz_nm"))
            best_other_sz = min(
                abs(_candidate_metric(methods["classical"], "bias_Sz_nm")),
                abs(_candidate_metric(methods["hybrid"], "bias_Sz_nm")),
            )
            if q_sz <= 5.0e4 and best_other_sz > q_sz:
                sz_envelope_candidates.append(
                    (stem, _surface_note("sz_envelope_following_case", score=best_other_sz - q_sz))
                )

    direct_failure_candidates.sort(
        key=lambda item: _candidate_metric(base_map[item[0]]["quantum_like"], "height_rmse_nm")
        / min(
            _candidate_metric(base_map[item[0]]["classical"], "height_rmse_nm"),
            _candidate_metric(base_map[item[0]]["hybrid"], "height_rmse_nm"),
        ),
        reverse=True,
    )
    turning_rough_candidates.sort(
        key=lambda item: _candidate_metric(base_map[item[0]]["quantum_like"], "height_rmse_nm")
    )
    wire_edm_rough_candidates.sort(
        key=lambda item: _candidate_metric(base_map[item[0]]["quantum_like"], "height_rmse_nm")
    )
    sz_envelope_candidates.sort(
        key=lambda item: min(
            abs(_candidate_metric(base_map[item[0]]["classical"], "bias_Sz_nm")),
            abs(_candidate_metric(base_map[item[0]]["hybrid"], "bias_Sz_nm")),
        ) - abs(_candidate_metric(base_map[item[0]]["quantum_like"], "bias_Sz_nm")),
        reverse=True,
    )

    classical_two_colour_candidates: list[tuple[str, str]] = []
    for stem, methods in classical_control_map.items():
        if {"classical_two_color", "quantum_like"} <= methods.keys():
            q_sz_bw = abs(_candidate_metric(methods["quantum_like"], "abs_bias_Sz_bw_nm"))
            c2_sz_bw = abs(_candidate_metric(methods["classical_two_color"], "abs_bias_Sz_bw_nm"))
            if q_sz_bw <= 1.0e4 and q_sz_bw > c2_sz_bw:
                classical_two_colour_candidates.append(
                    (
                        stem,
                        _surface_note(
                            "classical_two_colour_nonuniqueness_case",
                            score=q_sz_bw - c2_sz_bw,
                        ),
                    )
                )
    classical_two_colour_candidates.sort(
        key=lambda item: abs(_candidate_metric(classical_control_map[item[0]]["quantum_like"], "abs_bias_Sz_bw_nm"))
        - abs(_candidate_metric(classical_control_map[item[0]]["classical_two_color"], "abs_bias_Sz_bw_nm")),
        reverse=True,
    )

    detector_fragility_candidates: list[tuple[str, str]] = []
    for stem, methods in base_map.items():
        if "quantum_like" not in methods or stem not in nonideal_map or "quantum_like" not in nonideal_map[stem]:
            continue
        base_q = _candidate_metric(methods["quantum_like"], "height_rmse_nm")
        nonideal_q = _candidate_metric(nonideal_map[stem]["quantum_like"], "height_rmse_nm")
        if 5.0e2 <= base_q <= 1.0e3 and nonideal_q > base_q:
            detector_fragility_candidates.append(
                (stem, _surface_note("detector_fragility_case", score=nonideal_q - base_q))
            )
    detector_fragility_candidates.sort(
        key=lambda item: _candidate_metric(nonideal_map[item[0]]["quantum_like"], "height_rmse_nm")
        - _candidate_metric(base_map[item[0]]["quantum_like"], "height_rmse_nm"),
        reverse=True,
    )

    rules = [
        SelectionRule(
            "core",
            "hybrid_best_height_case",
            "Anchor best-case replication of the main fixed-workflow height-RMSE claim.",
        ),
        SelectionRule(
            "core",
            "hybrid_median_height_case",
            "Anchor a typical-case replication near the benchmark median.",
        ),
        SelectionRule(
            "core",
            "direct_q_catastrophic_failure_case",
            "Demonstrate the failure mode that most strongly limits direct coincidence-only reconstruction.",
        ),
        SelectionRule(
            "core",
            "turning_rough_q_exception_case",
            "Test one treatment family where the direct branch is a grouped height-RMSE exception.",
        ),
        SelectionRule(
            "core",
            "classical_two_colour_nonuniqueness_case",
            "Test whether the envelope-following claim can be reproduced by a purely classical synthetic-wavelength baseline.",
        ),
        SelectionRule(
            "core",
            "detector_fragility_case",
            "Test whether realistic detector non-idealities hurt the direct branch more than the hybrid branch.",
        ),
        SelectionRule(
            "extended",
            "wire_edm_rough_q_exception_case",
            "Add the second grouped height-RMSE exception family from the manuscript.",
        ),
        SelectionRule(
            "extended",
            "sz_envelope_following_case",
            "Add a native-grid Sz case where the direct branch has its clearest envelope-following advantage.",
        ),
    ]

    candidate_map: dict[str, list[tuple[str, str]]] = {
        "hybrid_best_height_case": [
            (hybrid_rows[0][0], _surface_note("hybrid_best_height_case", score=hybrid_rows[0][1]))
        ],
        "hybrid_median_height_case": sorted(
            [(stem, _surface_note("hybrid_median_height_case", score=value)) for stem, value in hybrid_rows],
            key=lambda item: abs(
                _candidate_metric(base_map[item[0]]["hybrid"], "height_rmse_nm") - hybrid_median
            ),
        ),
        "direct_q_catastrophic_failure_case": direct_failure_candidates,
        "turning_rough_q_exception_case": turning_rough_candidates,
        "classical_two_colour_nonuniqueness_case": classical_two_colour_candidates,
        "detector_fragility_case": detector_fragility_candidates,
        "wire_edm_rough_q_exception_case": wire_edm_rough_candidates,
        "sz_envelope_following_case": sz_envelope_candidates,
    }

    used: set[str] = set()
    out: list[dict[str, object]] = []
    for rule in rules:
        stem, category_note = _pick_first_unused(candidate_map[rule.category], used)
        base_methods = base_map[stem]
        classical_rmse = _candidate_metric(base_methods["classical"], "height_rmse_nm")
        quantum_rmse = _candidate_metric(base_methods["quantum_like"], "height_rmse_nm")
        hybrid_rmse = _candidate_metric(base_methods["hybrid"], "height_rmse_nm")
        best_other_rmse = min(classical_rmse, hybrid_rmse)
        record = {
            "tier": rule.tier,
            "category": rule.category,
            "stem": stem,
            "file": str(base_methods["hybrid"].get("file", "")),
            "material": str(base_methods["hybrid"].get("material", "")),
            "treatment": str(base_methods["hybrid"].get("treatment", "")),
            "selection_rationale": rule.rationale,
            "selection_note": category_note,
            "classical_height_rmse_nm": classical_rmse,
            "quantum_like_height_rmse_nm": quantum_rmse,
            "hybrid_height_rmse_nm": hybrid_rmse,
            "q_failure_ratio_vs_best_other": quantum_rmse / best_other_rmse if best_other_rmse > 0.0 else "",
            "quantum_like_abs_bias_Sz_native_nm": abs(
                _candidate_metric(base_methods["quantum_like"], "bias_Sz_nm")
            ),
            "best_other_abs_bias_Sz_native_nm": min(
                abs(_candidate_metric(base_methods["classical"], "bias_Sz_nm")),
                abs(_candidate_metric(base_methods["hybrid"], "bias_Sz_nm")),
            ),
            "classical_two_color_abs_bias_Sz_bw_nm": "",
            "quantum_like_abs_bias_Sz_bw_nm": "",
            "nonideal_quantum_like_height_rmse_nm": "",
            "nonideal_quantum_like_delta_nm": "",
        }
        if stem in classical_control_map and {"classical_two_color", "quantum_like"} <= classical_control_map[stem].keys():
            record["classical_two_color_abs_bias_Sz_bw_nm"] = abs(
                _candidate_metric(classical_control_map[stem]["classical_two_color"], "abs_bias_Sz_bw_nm")
            )
            record["quantum_like_abs_bias_Sz_bw_nm"] = abs(
                _candidate_metric(classical_control_map[stem]["quantum_like"], "abs_bias_Sz_bw_nm")
            )
        if stem in nonideal_map and "quantum_like" in nonideal_map[stem]:
            nonideal_q = _candidate_metric(nonideal_map[stem]["quantum_like"], "height_rmse_nm")
            record["nonideal_quantum_like_height_rmse_nm"] = nonideal_q
            record["nonideal_quantum_like_delta_nm"] = nonideal_q - quantum_rmse
        out.append(record)
    return out


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _write_markdown(path: Path, rows: list[dict[str, object]], *, csv_path: Path) -> None:
    lines = [
        "# Reduced Experimental Validation Subset",
        "",
        "This file is auto-generated by `scripts/select_experimental_validation_subset.py`.",
        "",
        "The core subset is the minimum defensible lab set for the manuscript's main claims. The extended subset adds two cases that test the manuscript's strongest conditional exceptions.",
        "",
        f"Source CSV: `{csv_path.relative_to(_ROOT).as_posix()}`",
        "",
        "| Tier | Category | Stem | Material | Treatment | Classical RMSE (nm) | Q-like RMSE (nm) | Hybrid RMSE (nm) | Selection note |",
        "| --- | --- | --- | --- | --- | ---: | ---: | ---: | --- |",
    ]
    for row in rows:
        lines.append(
            "| {tier} | {category} | {stem} | {material} | {treatment} | {classical:.1f} | {quantum:.1f} | {hybrid:.1f} | {note} |".format(
                tier=row["tier"],
                category=row["category"],
                stem=row["stem"],
                material=row["material"],
                treatment=row["treatment"],
                classical=float(row["classical_height_rmse_nm"]),
                quantum=float(row["quantum_like_height_rmse_nm"]),
                hybrid=float(row["hybrid_height_rmse_nm"]),
                note=row["selection_note"],
            )
        )
    lines.extend(
        [
            "",
            "## Regeneration",
            "",
            "```bash",
            "python scripts/select_experimental_validation_subset.py",
            "```",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def _escape_latex(text: str) -> str:
    escaped = text.replace("\\", r"\textbackslash{}")
    replacements = {
        "&": r"\&",
        "%": r"\%",
        "_": r"\_",
        "#": r"\#",
    }
    for old, new in replacements.items():
        escaped = escaped.replace(old, new)
    return escaped


def _pretty_label(raw: str) -> str:
    labels = {
        "hybrid_best_height_case": "Best hybrid height",
        "hybrid_median_height_case": "Median hybrid height",
        "direct_q_catastrophic_failure_case": "Catastrophic direct-Q failure",
        "turning_rough_q_exception_case": "Turning-roughing exception",
        "classical_two_colour_nonuniqueness_case": "Two-colour non-uniqueness",
        "detector_fragility_case": "Detector fragility",
        "wire_edm_rough_q_exception_case": "Wire-EDM roughing exception",
        "sz_envelope_following_case": "Native-grid $S_z$ envelope",
    }
    return labels[raw]


def _write_latex_table(path: Path, rows: list[dict[str, object]]) -> None:
    lines = [
        "% Auto-generated by scripts/select_experimental_validation_subset.py",
        "\\begin{table}[t]",
        "\\centering",
        "\\footnotesize",
        "\\setlength{\\tabcolsep}{4pt}",
        "\\caption{Prepared reduced experimental-validation subset for the next revision-critical laboratory follow-up. The core rows are the minimum set needed to challenge the main architectural claim on real coincidence measurements; the extended rows add the second grouped exception family and the strongest native-grid envelope-following case.}",
        "\\label{tab:experimental_validation_subset}",
        "\\begin{tabularx}{\\textwidth}{>{\\RaggedRight\\arraybackslash}p{0.10\\textwidth}>{\\RaggedRight\\arraybackslash}p{0.24\\textwidth}>{\\RaggedRight\\arraybackslash}p{0.23\\textwidth}X}",
        "\\toprule",
        "Tier & Case & Selected surface & Purpose in reduced validation \\\\",
        "\\midrule",
    ]
    for row in rows:
        tier = _escape_latex(str(row["tier"]).title())
        case = _escape_latex(_pretty_label(str(row["category"])))
        stem = str(row["stem"])
        purpose = _escape_latex(str(row["selection_rationale"]))
        lines.append(f"{tier} & {case} & \\path{{{stem}}} & {purpose} \\\\")
    lines.extend(
        [
            "\\bottomrule",
            "\\end{tabularx}",
            "\\end{table}",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Select a reduced experimental validation subset from the paper benchmark outputs"
    )
    parser.add_argument(
        "--base-per-surface",
        type=Path,
        default=Path("outputs/paper_alicona_benchmark/per_surface.csv"),
    )
    parser.add_argument(
        "--classical-control-per-surface",
        type=Path,
        default=Path("outputs/paper_alicona_benchmark/classical_control/per_surface.csv"),
    )
    parser.add_argument(
        "--nonideal-rate-per-surface",
        type=Path,
        default=Path("outputs/paper_alicona_benchmark/rate_model_control/rates_nonideal/per_surface.csv"),
    )
    parser.add_argument(
        "--out-csv",
        type=Path,
        default=Path("outputs/paper_alicona_benchmark/experimental_validation/validation_subset.csv"),
    )
    parser.add_argument(
        "--out-md",
        type=Path,
        default=Path("outputs/paper_alicona_benchmark/experimental_validation/validation_subset.md"),
    )
    parser.add_argument(
        "--out-tex",
        type=Path,
        default=Path("manuscript/tables/experimental_validation_subset.tex"),
    )
    args = parser.parse_args()

    base_map = _collapse_rows(_ROOT / args.base_per_surface)
    classical_control_map = _collapse_rows(_ROOT / args.classical_control_per_surface)
    nonideal_map = _collapse_rows(_ROOT / args.nonideal_rate_per_surface)
    rows = _selection_records(base_map, classical_control_map, nonideal_map)
    _write_csv(_ROOT / args.out_csv, rows)
    _write_markdown(_ROOT / args.out_md, rows, csv_path=_ROOT / args.out_csv)
    _write_latex_table(_ROOT / args.out_tex, rows)
    print(f"Wrote: {_ROOT / args.out_csv}")
    print(f"Wrote: {_ROOT / args.out_md}")
    print(f"Wrote: {_ROOT / args.out_tex}")


if __name__ == "__main__":
    main()