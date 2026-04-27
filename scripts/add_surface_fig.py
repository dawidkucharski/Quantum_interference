from __future__ import annotations

import argparse
import json
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def _pick_first(x: object, default: float) -> float:
    if isinstance(x, list) and x:
        try:
            return float(x[0])
        except Exception:
            return float(default)
    try:
        return float(x)  # type: ignore[arg-type]
    except Exception:
        return float(default)


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Add representative ground-truth surface figures (2D + 3D) into an existing output folder."
    )
    ap.add_argument("outdir", type=str, help="Existing output folder (e.g., outputs/sweep_... or outputs/demo).")
    ap.add_argument("--nx", type=int, default=256)
    ap.add_argument("--ny", type=int, default=256)
    ap.add_argument("--size-x", type=float, default=1e-3)
    ap.add_argument("--size-y", type=float, default=1e-3)
    ap.add_argument("--corr-len-um", type=float, default=25.0)
    ap.add_argument("--rms-nm", type=float, default=50.0)
    ap.add_argument("--step-nm", type=float, default=0.0)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    outdir = Path(args.outdir)
    if not outdir.exists() or not outdir.is_dir():
        raise SystemExit(f"Not a directory: {outdir}")

    # Try to read sweep params if present
    params_path = outdir / "params.json"
    if params_path.exists():
        try:
            d = json.loads(params_path.read_text(encoding="utf-8"))
            p = d.get("params", {}) if isinstance(d, dict) else {}
            args.rms_nm = float(_pick_first(p.get("rms_nm", args.rms_nm), args.rms_nm))
            args.step_nm = float(_pick_first(p.get("step_nm", args.step_nm), args.step_nm))
        except Exception:
            pass

    import sys

    sys.path.insert(0, str(_ROOT / "src"))

    from qiprof.plot_style import apply_publication_style
    from qiprof.surfaces import make_surface
    from qiprof.viz import save_surface_3d, save_surface_height_map

    apply_publication_style(base_fontsize=8.5)

    surface = make_surface(
        nx=int(args.nx),
        ny=int(args.ny),
        size_x=float(args.size_x),
        size_y=float(args.size_y),
        kind="gaussian_rough",
        rms=float(args.rms_nm) * 1e-9,
        corr_len=float(args.corr_len_um) * 1e-6,
        step_height=float(args.step_nm) * 1e-9,
        seed=int(args.seed),
    )

    title = f"Ground-truth surface (step={float(args.step_nm):g} nm, rms={float(args.rms_nm):g} nm)"
    save_surface_height_map(outdir / "surface_true_map.png", surface, title=title)
    save_surface_height_map(outdir / "surface_true_map.pdf", surface, title=title)
    save_surface_3d(outdir / "surface_true_3d.png", surface, title=title, alpha=0.78)
    save_surface_3d(outdir / "surface_true_3d.pdf", surface, title=title, alpha=0.78)

    print(f"Wrote: {outdir / 'surface_true_map.png'}")
    print(f"Wrote: {outdir / 'surface_true_map.pdf'}")
    print(f"Wrote: {outdir / 'surface_true_3d.png'}")
    print(f"Wrote: {outdir / 'surface_true_3d.pdf'}")


if __name__ == "__main__":
    main()
