#!/usr/bin/env python3

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def _run(cmd: list[str]) -> None:
    print(" ".join(cmd))
    subprocess.run(cmd, check=True)


def _run_scenario(
    *,
    py: str,
    root: Path,
    sweep_out: Path,
    fig_out: Path,
    nx: int,
    ny: int,
    nreps: int,
    rms_nm: float,
    sample_reflectivity: float,
    sample_visibility_scale: float,
    extra_args: list[str],
    style: str,
    layout: str,
) -> Path:
    _run(
        [
            py,
            str(root / "scripts" / "run_sweep.py"),
            "--outdir",
            str(sweep_out),
            "--nx",
            str(int(nx)),
            "--ny",
            str(int(ny)),
            "--nreps",
            str(int(nreps)),
            "--rms-nm",
            str(float(rms_nm)),
            "--step-nm",
            "0.0",
            "--sample-reflectivity",
            str(float(sample_reflectivity)),
            "--sample-visibility-scale",
            str(float(sample_visibility_scale)),
            "--quant-interferometer",
            "noon2",
            "--coherence-model",
            "rayleigh",
            "--no-surface-fig",
            *extra_args,
        ]
    )

    _run(
        [
            py,
            str(root / "scripts" / "plot_sweep.py"),
            "--outdir",
            str(fig_out),
            "--style",
            str(style),
            "--layout",
            str(layout),
            "--formats",
            "pdf",
            str(sweep_out),
        ]
    )
    return fig_out / "summary.csv"


def main() -> None:
    ap = argparse.ArgumentParser(description="Paper detector sensitivity: regenerate rate-model artefacts")
    ap.add_argument("--tag", type=str, default="paper_optprops_detector_sensitivity", help="Output tag under outputs/")
    ap.add_argument("--nx", type=int, default=128)
    ap.add_argument("--ny", type=int, default=128)
    ap.add_argument("--nreps", type=int, default=10)
    ap.add_argument("--rms-nm", type=float, default=80.0)
    ap.add_argument("--sample-reflectivity", type=float, default=1.0)
    ap.add_argument("--sample-visibility-scale", type=float, default=1.0)
    ap.add_argument("--gate-time-s", type=float, default=1e-3)
    ap.add_argument("--quant-target-mean-counts", type=float, default=3e4)
    ap.add_argument("--tau-c-s", type=float, default=20e-9)
    ap.add_argument("--eta1", type=float, default=0.70)
    ap.add_argument("--eta2", type=float, default=0.50)
    ap.add_argument("--deadtime-s", type=float, default=5e-9)
    ap.add_argument("--style", type=str, default="photonics", choices=["default", "mdpi", "photonics"])
    ap.add_argument("--layout", type=str, default="onecol", choices=["onecol", "twocol"])
    args = ap.parse_args()

    root = Path(__file__).resolve().parents[1]
    py = sys.executable
    out_base = root / "outputs" / str(args.tag)

    baseline_summary = _run_scenario(
        py=py,
        root=root,
        sweep_out=out_base / "simple" / "sweep",
        fig_out=out_base / "simple" / "figures",
        nx=int(args.nx),
        ny=int(args.ny),
        nreps=int(args.nreps),
        rms_nm=float(args.rms_nm),
        sample_reflectivity=float(args.sample_reflectivity),
        sample_visibility_scale=float(args.sample_visibility_scale),
        extra_args=[],
        style=str(args.style),
        layout=str(args.layout),
    )

    rate_common = [
        "--quant-detector-model",
        "rates",
        "--quant-target-mean-counts",
        str(float(args.quant_target_mean_counts)),
        "--gate-time-s",
        str(float(args.gate_time_s)),
    ]

    rate_summary = _run_scenario(
        py=py,
        root=root,
        sweep_out=out_base / "rate" / "sweep",
        fig_out=out_base / "rate" / "figures",
        nx=int(args.nx),
        ny=int(args.ny),
        nreps=int(args.nreps),
        rms_nm=float(args.rms_nm),
        sample_reflectivity=float(args.sample_reflectivity),
        sample_visibility_scale=float(args.sample_visibility_scale),
        extra_args=[*rate_common, "--tau-c-s", "0.0"],
        style=str(args.style),
        layout=str(args.layout),
    )

    accidentals_summary = _run_scenario(
        py=py,
        root=root,
        sweep_out=out_base / "accidentals" / "sweep",
        fig_out=out_base / "accidentals" / "figures",
        nx=int(args.nx),
        ny=int(args.ny),
        nreps=int(args.nreps),
        rms_nm=float(args.rms_nm),
        sample_reflectivity=float(args.sample_reflectivity),
        sample_visibility_scale=float(args.sample_visibility_scale),
        extra_args=[*rate_common, "--tau-c-s", str(float(args.tau_c_s))],
        style=str(args.style),
        layout=str(args.layout),
    )

    imbalance_summary = _run_scenario(
        py=py,
        root=root,
        sweep_out=out_base / "imbalance" / "sweep",
        fig_out=out_base / "imbalance" / "figures",
        nx=int(args.nx),
        ny=int(args.ny),
        nreps=int(args.nreps),
        rms_nm=float(args.rms_nm),
        sample_reflectivity=float(args.sample_reflectivity),
        sample_visibility_scale=float(args.sample_visibility_scale),
        extra_args=[
            *rate_common,
            "--tau-c-s",
            str(float(args.tau_c_s)),
            "--eta1",
            str(float(args.eta1)),
            "--eta2",
            str(float(args.eta2)),
        ],
        style=str(args.style),
        layout=str(args.layout),
    )

    deadtime_summary = _run_scenario(
        py=py,
        root=root,
        sweep_out=out_base / "deadtime" / "sweep",
        fig_out=out_base / "deadtime" / "figures",
        nx=int(args.nx),
        ny=int(args.ny),
        nreps=int(args.nreps),
        rms_nm=float(args.rms_nm),
        sample_reflectivity=float(args.sample_reflectivity),
        sample_visibility_scale=float(args.sample_visibility_scale),
        extra_args=[
            *rate_common,
            "--tau-c-s",
            str(float(args.tau_c_s)),
            "--deadtime1-s",
            str(float(args.deadtime_s)),
            "--deadtime2-s",
            str(float(args.deadtime_s)),
        ],
        style=str(args.style),
        layout=str(args.layout),
    )

    _run(
        [
            py,
            str(root / "scripts" / "make_detector_sensitivity_artifacts.py"),
            "--baseline-summary",
            str(baseline_summary),
            "--rate-summary",
            str(rate_summary),
            "--accidentals-summary",
            str(accidentals_summary),
            "--imbalance-summary",
            str(imbalance_summary),
            "--deadtime-summary",
            str(deadtime_summary),
            "--out-table",
            str(root / "manuscript" / "tables" / "optprops_detector_sensitivity.tex"),
            "--out-figure",
            str(out_base / "detector_sensitivity_summary.pdf"),
            "--sample-reflectivity",
            str(float(args.sample_reflectivity)),
            "--sample-visibility-scale",
            str(float(args.sample_visibility_scale)),
            "--rms-nm",
            str(float(args.rms_nm)),
            "--gate-time-ms",
            str(float(args.gate_time_s) * 1e3),
            "--tau-c-ns",
            str(float(args.tau_c_s) * 1e9),
            "--eta1",
            str(float(args.eta1)),
            "--eta2",
            str(float(args.eta2)),
            "--deadtime-ns",
            str(float(args.deadtime_s) * 1e9),
        ]
    )

    print(f"Wrote detector sensitivity artefacts under: {out_base}")


if __name__ == "__main__":
    main()