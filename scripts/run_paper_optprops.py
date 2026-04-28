"""Run a paper-style sweep grid including sample optical properties and emit a LaTeX table.

This script orchestrates:
  1) scripts/run_sweep.py
  2) scripts/plot_sweep.py
  3) scripts/make_table_from_summary.py

Defaults are chosen to be paper-friendly but still tractable.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def _run(cmd: list[str]) -> None:
    print(" ".join(cmd))
    subprocess.run(cmd, check=True)


def main() -> None:
    ap = argparse.ArgumentParser(description="Paper sweep: roughness × reflectivity × visibility-scale × interferometer")
    ap.add_argument("--tag", type=str, default="paper_optprops", help="Output tag under outputs/")
    ap.add_argument("--nx", type=int, default=128)
    ap.add_argument("--ny", type=int, default=128)
    ap.add_argument("--nreps", type=int, default=10)
    ap.add_argument("--rms-grid", type=str, default="paper", choices=["smoke", "paper", "dense"])
    ap.add_argument("--step-nm", type=float, default=0.0, help="Fix step height (nm). Use 0 for step-free.")
    ap.add_argument("--sample-reflectivity", type=str, default="1.0,0.5,0.2")
    ap.add_argument("--sample-visibility-scale", type=str, default="1.0,0.7")
    ap.add_argument("--quant-interferometer", type=str, default="diff,noon2")
    ap.add_argument("--coherence-model", type=str, default="rayleigh", choices=["none", "rayleigh"])
    ap.add_argument("--incidence-cos", type=float, default=1.0)
    ap.add_argument("--style", type=str, default="photonics", choices=["default", "mdpi", "photonics"])
    ap.add_argument("--layout", type=str, default="onecol", choices=["onecol", "twocol"])
    ap.add_argument("--skip-lambda-sensitivity", action="store_true")
    ap.add_argument("--skip-budget-sensitivity", action="store_true")
    ap.add_argument("--skip-step-regime-control", action="store_true")

    args = ap.parse_args()

    root = Path(__file__).resolve().parents[1]
    py = sys.executable

    out_base = root / "outputs" / str(args.tag)
    sweep_out = out_base / "sweep"
    fig_out = out_base / "figures"

    refl = [x.strip() for x in str(args.sample_reflectivity).split(",") if x.strip()]
    vis = [x.strip() for x in str(args.sample_visibility_scale).split(",") if x.strip()]
    qints = [x.strip() for x in str(args.quant_interferometer).split(",") if x.strip()]

    _run(
        [
            py,
            str(root / "scripts" / "run_sweep.py"),
            "--outdir",
            str(sweep_out),
            "--nx",
            str(int(args.nx)),
            "--ny",
            str(int(args.ny)),
            "--nreps",
            str(int(args.nreps)),
            "--rms-grid",
            str(args.rms_grid),
            "--step-nm",
            str(float(args.step_nm)),
            "--sample-reflectivity",
            *refl,
            "--sample-visibility-scale",
            *vis,
            "--quant-interferometer",
            *qints,
            "--coherence-model",
            str(args.coherence_model),
            "--incidence-cos",
            str(float(args.incidence_cos)),
            "--no-surface-fig",
        ]
    )

    _run(
        [
            py,
            str(root / "scripts" / "plot_sweep.py"),
            "--outdir",
            str(fig_out),
            "--style",
            str(args.style),
            "--layout",
            str(args.layout),
            "--formats",
            "png,pdf",
            str(sweep_out),
        ]
    )

    out_table = root / "manuscript" / "tables" / "optprops_rmse_step0.tex"
    _run(
        [
            py,
            str(root / "scripts" / "make_table_from_summary.py"),
            "--summary",
            str(fig_out / "summary.csv"),
            "--out",
            str(out_table),
            "--step-nm",
            str(float(args.step_nm)),
            "--methods",
            "classical,quant_diff,quant_noon2,hybrid_diff,hybrid_noon2",
            "--digits",
            "2",
            "--label",
            "tab:optprops_rmse_step0",
            "--caption",
            "Height RMSE (after plane detrending) for step-free surfaces. Entries are mean $\\pm$ std over repeats; columns compare classical PSI with coincidence-proxy and hybrid pipelines for different interferometer models.",
        ]
    )

    if not args.skip_lambda_sensitivity:
        _run(
            [
                py,
                str(root / "scripts" / "run_paper_lambda_visibility_sensitivity.py"),
                "--outdir",
                str(out_base / "lambda_spacing_control"),
                "--table-out",
                str(root / "manuscript" / "tables" / "optprops_lambda_sensitivity.tex"),
                "--nreps",
                str(int(args.nreps)),
                "--nx",
                str(int(args.nx)),
                "--ny",
                str(int(args.ny)),
                "--coherence-model",
                str(args.coherence_model),
            ]
        )

    if not args.skip_budget_sensitivity:
        _run(
            [
                py,
                str(root / "scripts" / "run_paper_budget_sensitivity.py"),
                "--outdir",
                str(out_base / "budget_sensitivity"),
                "--table-out",
                str(root / "manuscript" / "tables" / "optprops_budget_sensitivity.tex"),
                "--nreps",
                str(int(args.nreps)),
                "--nx",
                str(int(args.nx)),
                "--ny",
                str(int(args.ny)),
            ]
        )

    if not args.skip_step_regime_control:
        _run(
            [
                py,
                str(root / "scripts" / "run_paper_step_regime_control.py"),
                "--nx",
                str(int(args.nx)),
                "--ny",
                str(int(args.ny)),
                "--nreps",
                str(int(args.nreps)),
            ]
        )

    print(f"Wrote figures: {fig_out}")
    print(f"Wrote table:   {out_table}")


if __name__ == "__main__":
    main()
