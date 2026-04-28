"""Run the measured-surface paper benchmark and regenerate manuscript artefacts.

This script orchestrates:
  1) scripts/benchmark_sur_interferometry.py
  2) scripts/plot_alicona_benchmark.py
  3) scripts/plot_benchmark_psd.py
    4) manuscript table generators fed from per_surface.csv
        5) exploratory AI method-selection artefacts derived from the same benchmark

The defaults reproduce the paper-facing measured-surface branch.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


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


def main() -> None:
    ap = argparse.ArgumentParser(description="Paper measured-surface benchmark: regenerate figures and tables")
    ap.add_argument("inputs", nargs="*", default=["data/*.sur"], help="SUR files or glob patterns under the repo root")
    ap.add_argument("--tag", type=str, default="paper_alicona_benchmark", help="Output tag under outputs/")
    ap.add_argument("--nx", type=int, default=256)
    ap.add_argument("--ny", type=int, default=256)
    ap.add_argument("--jobs", type=int, default=0, help="Parallel workers for the main benchmark; 0 uses the benchmark default")
    ap.add_argument("--nreps", type=int, default=4, help="Monte-Carlo repetitions for the canonical benchmark and two-colour control")
    ap.add_argument("--control-nreps", type=int, default=1, help="Monte-Carlo repetitions for auxiliary grid and unwrap controls")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--resolution-grid", nargs="*", type=int, default=[128, 256, 384])
    ap.add_argument(
        "--psd-surface-sur",
        nargs="*",
        default=["data/1.4301_szlifowane.sur", "data/P1-Ti6A14V_t_wyk.sur"],
    )
    ap.add_argument("--skip-benchmark", action="store_true", help="Reuse an existing per_surface.csv instead of rerunning the forward benchmark")
    ap.add_argument("--skip-resolution-sensitivity", action="store_true")
    ap.add_argument("--skip-unwrap-control", action="store_true")
    ap.add_argument("--skip-rate-model-control", action="store_true")
    ap.add_argument("--skip-nonideal-control", action="store_true")
    ap.add_argument("--skip-roughness-filter-control", action="store_true")
    ap.add_argument("--skip-classical-frontier", action="store_true")
    ap.add_argument("--skip-surface-metadata", action="store_true")
    args = ap.parse_args()

    root = Path(__file__).resolve().parents[1]
    py = sys.executable
    out_base = root / "outputs" / str(args.tag)
    per_surface = out_base / "per_surface.csv"
    expanded_inputs = _expand_inputs(root, list(args.inputs))

    if not args.skip_benchmark:
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
            "--sur-resample",
            "area",
            "--nreps",
            str(int(args.nreps)),
            "--jobs",
            str(int(args.jobs)),
        ]
        if int(args.limit) > 0:
            cmd.extend(["--limit", str(int(args.limit))])
        _run(cmd)

    _run(
        [
            py,
            str(root / "scripts" / "plot_alicona_benchmark.py"),
            "--per-surface",
            str(per_surface),
            "--out",
            str(out_base / "figures" / "rmse_measured_summary.pdf"),
            "--roughness-out",
            str(out_base / "figures" / "roughness_measured_summary.pdf"),
            "--roughness-bias-out",
            str(out_base / "figures" / "roughness_measured_bland_altman.pdf"),
            "--roughness-by-treatment-out",
            str(out_base / "figures" / "roughness_measured_by_treatment.pdf"),
            "--pairwise-out",
            str(out_base / "figures" / "paired_method_comparison.pdf"),
            "--roughness-suffix",
            "_bw",
            "--roughness-reference-label",
            "benchmark-grid reference",
        ]
    )

    _run(
        [
            py,
            str(root / "scripts" / "plot_benchmark_residual_maps.py"),
            "--per-surface",
            str(per_surface),
            "--out",
            str(out_base / "figures" / "residual_maps_representative.pdf"),
            "--nx",
            str(int(args.nx)),
            "--ny",
            str(int(args.ny)),
        ]
    )

    _run(
        [
            py,
            str(root / "scripts" / "plot_benchmark_psd.py"),
            "--surface-sur",
            *[str((root / str(path)).resolve()) for path in list(args.psd_surface_sur)],
            "--out",
            str(out_base / "figures" / "psd_representative.pdf"),
            "--nx",
            str(int(args.nx)),
            "--ny",
            str(int(args.ny)),
        ]
    )

    _run(
        [
            py,
            str(root / "scripts" / "make_table_from_sur_benchmark.py"),
            "--grouped",
            str(per_surface),
            "--out",
            str(root / "manuscript" / "tables" / "alicona_rmse_by_material.tex"),
            "--group-key",
            "material",
            "--metric",
            "height_rmse_nm",
            "--label",
            "tab:alicona_rmse_by_material",
            "--caption",
            "Height RMSE (after plane detrending) grouped by material. Entries report the median surface-level RMSE with the first and third quartiles in brackets after collapsing repeated runs within each measured surface and method.",
            "--digits",
            "1",
            "--summary-style",
            "median_iqr",
            "--include-n",
        ]
    )

    _run(
        [
            py,
            str(root / "scripts" / "make_table_from_sur_benchmark.py"),
            "--grouped",
            str(per_surface),
            "--out",
            str(root / "manuscript" / "tables" / "alicona_rmse_by_treatment.tex"),
            "--group-key",
            "treatment",
            "--metric",
            "height_rmse_nm",
            "--label",
            "tab:alicona_rmse_by_treatment",
            "--caption",
            "Height RMSE (after plane detrending) grouped by treatment class. Entries report the median surface-level RMSE with the first and third quartiles in brackets after collapsing repeated runs within each measured surface and method.",
            "--digits",
            "1",
            "--summary-style",
            "median_iqr",
            "--include-n",
        ]
    )

    _run(
        [
            py,
            str(root / "scripts" / "make_table_from_sur_roughness.py"),
            "--per-surface",
            str(per_surface),
            "--out",
            str(root / "manuscript" / "tables" / "alicona_roughness_median_abs.tex"),
            "--label",
            "tab:alicona_roughness_median_abs",
            "--digits",
            "1",
            "--caption",
            "Native-grid diagnostic stress test for the measured-surface benchmark: median absolute roughness-parameter error relative to roughness values computed on the native FV \\texttt{.sur} height maps after masking explicit invalid pixels and removing a best-fit plane. This comparison is intentionally stricter than the forward-model bandwidth and is retained as a reference-sensitivity diagnostic rather than as the primary roughness ranking.",
        ]
    )

    _run(
        [
            py,
            str(root / "scripts" / "make_table_from_sur_roughness.py"),
            "--per-surface",
            str(per_surface),
            "--out",
            str(root / "manuscript" / "tables" / "alicona_roughness_median_abs_bw.tex"),
            "--label",
            "tab:alicona_roughness_median_abs_bw",
            "--digits",
            "1",
            "--bias-suffix",
            "_bw",
            "--caption",
            "Matched-bandwidth control for the measured-surface benchmark: median absolute roughness-parameter error relative to roughness values computed on the same area-averaged benchmark grid used by the interferometric forward model.",
        ]
    )

    _run(
        [
            py,
            str(root / "scripts" / "make_benchmark_stat_tables.py"),
            "--per-surface",
            str(per_surface),
            "--bootstrap-out",
            str(root / "manuscript" / "tables" / "benchmark_bootstrap_ci.tex"),
            "--tolerance-out",
            str(root / "manuscript" / "tables" / "benchmark_tolerance_rates.tex"),
            "--repeatability-out",
            str(root / "manuscript" / "tables" / "benchmark_repeatability.tex"),
            "--holdout-out",
            str(root / "manuscript" / "tables" / "benchmark_holdout_material.tex"),
            "--holdout-treatment-out",
            str(root / "manuscript" / "tables" / "benchmark_holdout_treatment.tex"),
        ]
    )

    if not args.skip_roughness_filter_control:
        _run(
            [
                py,
                str(root / "scripts" / "run_paper_roughness_filter_control.py"),
                *expanded_inputs,
                "--baseline-per-surface",
                str(per_surface),
                "--tag",
                str(args.tag),
                "--nx",
                str(int(args.nx)),
                "--ny",
                str(int(args.ny)),
                "--nreps",
                str(int(args.nreps)),
                "--jobs",
                str(int(args.jobs)),
            ]
        )

    if not args.skip_surface_metadata:
        _run(
            [
                py,
                str(root / "scripts" / "run_paper_surface_metadata.py"),
                *expanded_inputs,
                "--tag",
                str(args.tag),
                "--target-nx",
                str(int(args.nx)),
                "--target-ny",
                str(int(args.ny)),
                "--out-table",
                str(root / "manuscript" / "tables" / "measured_surface_metadata.tex"),
            ]
        )

    _run(
        [
            py,
            str(root / "scripts" / "make_benchmark_comparison_tables.py"),
            "--per-surface",
            str(per_surface),
            "--dominance-out",
            str(root / "manuscript" / "tables" / "dominance_summary.tex"),
            "--wilcoxon-out",
            str(root / "manuscript" / "tables" / "benchmark_wilcoxon.tex"),
            "--effects-out",
            str(root / "manuscript" / "tables" / "benchmark_paired_effects.tex"),
        ]
    )

    _run(
        [
            py,
            str(root / "scripts" / "run_paper_classical_two_color_control.py"),
            *expanded_inputs,
            "--outdir",
            str(out_base / "classical_control"),
            "--table-out",
            str(root / "manuscript" / "tables" / "classical_two_color_control.tex"),
            "--nx",
            str(int(args.nx)),
            "--ny",
            str(int(args.ny)),
            "--nreps",
            str(int(args.nreps)),
            "--sur-resample",
            "area",
        ]
    )

    if not args.skip_classical_frontier:
        _run(
            [
                py,
                str(root / "scripts" / "run_paper_classical_frontier_control.py"),
                *expanded_inputs,
                "--tag",
                str(args.tag),
                "--nx",
                str(int(args.nx)),
                "--ny",
                str(int(args.ny)),
                "--nreps",
                str(int(args.control_nreps)),
                "--out-table",
                str(root / "manuscript" / "tables" / "classical_frontier_control.tex"),
            ]
        )

    _run(
        [
            py,
            str(root / "scripts" / "make_ai_selection_artifacts.py"),
            "--per-surface",
            str(per_surface),
            "--outdir",
            str(out_base / "ai_selection"),
            "--out-table",
            str(root / "manuscript" / "tables" / "ai_method_selection.tex"),
            "--label",
            "tab:ai_method_selection",
        ]
    )

    if not args.skip_resolution_sensitivity:
        _run(
            [
                py,
                str(root / "scripts" / "run_paper_resolution_sensitivity.py"),
                *expanded_inputs,
                "--tag",
                str(args.tag),
                "--base-nx",
                str(int(args.nx)),
                "--base-ny",
                str(int(args.ny)),
                "--nreps",
                str(int(args.control_nreps)),
                "--resolutions",
                *[str(int(v)) for v in list(args.resolution_grid)],
            ]
        )

    if not args.skip_unwrap_control:
        _run(
            [
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
                str(int(args.control_nreps)),
            ]
        )

    if not args.skip_rate_model_control:
        _run(
            [
                py,
                str(root / "scripts" / "run_paper_measured_rate_control.py"),
                *expanded_inputs,
                "--tag",
                str(args.tag),
                "--nx",
                str(int(args.nx)),
                "--ny",
                str(int(args.ny)),
                "--nreps",
                str(int(args.control_nreps)),
                "--jobs",
                str(int(args.jobs)),
            ]
        )

    if not args.skip_nonideal_control:
        _run(
            [
                py,
                str(root / "scripts" / "run_paper_measured_nonideal_control.py"),
                *expanded_inputs,
                "--tag",
                str(args.tag),
                "--nx",
                str(int(args.nx)),
                "--ny",
                str(int(args.ny)),
                "--nreps",
                str(int(args.control_nreps)),
                "--jobs",
                str(int(args.jobs)),
            ]
        )

    print(f"Wrote benchmark artefacts from: {per_surface}")
    print(f"Updated manuscript tables under: {root / 'manuscript' / 'tables'}")


if __name__ == "__main__":
    main()