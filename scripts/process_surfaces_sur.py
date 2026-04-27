from __future__ import annotations

import argparse
import csv
from pathlib import Path
import sys

import numpy as np

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "src"))

from qiprof.metrics import roughness_metrics
from qiprof.surfaces import load_surface_sur, read_digital_surf_sur_header
from qiprof.viz import save_surface_3d, save_surface_height_map
from qiprof.labels import decode_sur_stem


def _decode_name(stem: str) -> dict[str, str]:
    label = decode_sur_stem(stem)
    return {
        "sample_group": label.sample_group,
        "material_code": label.material_code,
        "treatment_code": label.treatment_code,
        "material": label.material_en,
        "treatment": label.treatment_en,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Batch-process Mountains/DigitalSurf .sur surfaces into metrics + previews")
    ap.add_argument(
        "inputs",
        nargs="*",
        default=["data/*.sur"],
        help="One or more .sur files or glob patterns (default: data/*.sur)",
    )
    ap.add_argument("--outdir", type=str, default="outputs/surfaces_summary")
    ap.add_argument("--nx", type=int, default=256, help="Downsampled width")
    ap.add_argument("--ny", type=int, default=256, help="Downsampled height")
    ap.add_argument(
        "--no-figs",
        action="store_true",
        help="Skip writing preview figures (faster; still writes summary.csv).",
    )
    ap.add_argument(
        "--stride-3d",
        type=int,
        default=4,
        help="Stride for the 3D preview plot (higher = faster).",
    )
    args = ap.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    paths: list[Path] = []
    for pat in args.inputs:
        p = Path(pat)
        if p.exists():
            paths.append(p)
        else:
            paths.extend(sorted(Path().glob(pat)))

    # De-duplicate while preserving sort order
    seen: set[Path] = set()
    unique_paths: list[Path] = []
    for p in paths:
        rp = p.resolve()
        if rp not in seen:
            unique_paths.append(p)
            seen.add(rp)

    rows: list[dict[str, object]] = []
    for p in unique_paths:
        stem = p.stem
        decoded = _decode_name(stem)
        row: dict[str, object] = {
            "file": str(p.as_posix()),
            "stem": stem,
            **decoded,
            "status": "ok",
            "error": "",
        }
        try:
            hdr = read_digital_surf_sur_header(p)
            row.update(
                {
                    "orig_nx": hdr.nx,
                    "orig_ny": hdr.ny,
                    "orig_size_x": hdr.size_x,
                    "orig_size_y": hdr.size_y,
                    "orig_size_unit_x": hdr.size_unit_x,
                    "orig_size_unit_y": hdr.size_unit_y,
                    "orig_z_unit": hdr.z_unit,
                    "bytes_per_point": hdr.bytes_per_point,
                }
            )

            surface = load_surface_sur(p, target_nx=int(args.nx), target_ny=int(args.ny))
            valid_mask = getattr(surface, "valid_mask", None)
            dx = float(surface.x[1] - surface.x[0]) if surface.x.size > 1 else float("nan")
            dy = float(surface.y[1] - surface.y[0]) if surface.y.size > 1 else float("nan")
            row.update({"nx": int(surface.x.size), "ny": int(surface.y.size), "dx_m": dx, "dy_m": dy})

            m = roughness_metrics(surface.h, valid_mask=valid_mask)
            row.update(
                {
                    "Sa_m": float(m.Sa),
                    "Sq_m": float(m.Sq),
                    "Sz_m": float(m.Sz),
                    "Sa_nm": float(m.Sa * 1e9),
                    "Sq_nm": float(m.Sq * 1e9),
                    "Sz_nm": float(m.Sz * 1e9),
                }
            )

            if not args.no_figs:
                od = outdir / stem
                od.mkdir(parents=True, exist_ok=True)
                save_surface_height_map(od / "surface_map.png", surface, title=stem)
                save_surface_3d(od / "surface_3d.png", surface, title=stem, alpha=0.78, stride=int(args.stride_3d))

        except Exception as e:  # noqa: BLE001
            row["status"] = "error"
            row["error"] = str(e)

        rows.append(row)

    # Determine header order: stable, with metrics near the end.
    keys: list[str] = [
        "file",
        "stem",
        "sample_group",
        "material_code",
        "treatment_code",
        "material",
        "treatment",
        "status",
        "error",
        "orig_nx",
        "orig_ny",
        "orig_size_x",
        "orig_size_y",
        "orig_size_unit_x",
        "orig_size_unit_y",
        "orig_z_unit",
        "bytes_per_point",
        "nx",
        "ny",
        "dx_m",
        "dy_m",
        "Sa_m",
        "Sq_m",
        "Sz_m",
        "Sa_nm",
        "Sq_nm",
        "Sz_nm",
    ]
    # Add any unexpected keys at the end.
    all_keys = {k for r in rows for k in r.keys()}
    for k in sorted(all_keys):
        if k not in keys:
            keys.append(k)

    summary_csv = outdir / "summary.csv"
    with summary_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        for r in rows:
            w.writerow(r)

    n_ok = sum(1 for r in rows if r.get("status") == "ok")
    n_err = sum(1 for r in rows if r.get("status") == "error")
    print(f"Wrote: {summary_csv} (ok={n_ok}, error={n_err})")


if __name__ == "__main__":
    main()
