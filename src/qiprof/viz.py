from __future__ import annotations

from pathlib import Path
from typing import Any, Optional, cast

import numpy as np

from qiprof.surfaces import Surface


def save_surface_height_map(
    path: str | Path,
    surface: Surface,
    *,
    title: str = "Simulated surface height",
    cmap: str = "viridis",
    z_scale: float = 1e9,
    z_unit: str = "nm",
    dpi: int = 180,
) -> None:
    """Save a 2D height map image for a simulated surface.

    For PDF output, use a vector-friendly cell mesh instead of an image so the
    result stays resolution-independent in the manuscript.
    """

    import matplotlib.pyplot as plt

    path = Path(path)

    x_mm = surface.x * 1e3
    y_mm = surface.y * 1e3
    z = surface.h * float(z_scale)
    if getattr(surface, "valid_mask", None) is not None:
        z = np.ma.array(z, mask=~cast(np.ndarray, surface.valid_mask))
    else:
        z = np.ma.masked_invalid(z)

    fig = plt.figure(figsize=(6.0, 5.0), dpi=int(dpi))
    ax = fig.add_subplot(111)
    if path.suffix.lower() == ".pdf":
        xx = np.linspace(float(x_mm.min()), float(x_mm.max()), int(z.shape[1]) + 1)
        yy = np.linspace(float(y_mm.min()), float(y_mm.max()), int(z.shape[0]) + 1)
        im = ax.pcolormesh(xx, yy, z, cmap=cmap, shading="flat")
        ax.set_aspect("auto")
    else:
        im = ax.imshow(
            z,
            cmap=cmap,
            origin="lower",
            extent=(float(x_mm.min()), float(x_mm.max()), float(y_mm.min()), float(y_mm.max())),
            aspect="auto",
        )
    ax.set_xlabel("x (mm)")
    ax.set_ylabel("y (mm)")
    ax.set_title(f"{title} ({z_unit})")
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label(f"Height ({z_unit})")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def save_surface_3d(
    path: str | Path,
    surface: Surface,
    *,
    title: str = "Simulated surface (3D)",
    cmap: str = "viridis",
    z_scale: float = 1e9,
    z_unit: str = "nm",
    stride: int = 4,
    alpha: float = 1.0,
    elev: float = 35.0,
    azim: float = -55.0,
    dpi: int = 180,
    zlim: Optional[tuple[float, float]] = None,
) -> None:
    """Save a 3D surface rendering for a simulated surface."""

    import matplotlib.pyplot as plt

    path = Path(path)

    x_mm = surface.x * 1e3
    y_mm = surface.y * 1e3
    X, Y = np.meshgrid(x_mm, y_mm)
    # NOTE: Matplotlib's 3D `plot_surface` can ignore masked-array masks in some
    # versions/backends, which may result in vertical "drop lines" to extreme
    # values. Using NaNs is robust: triangles touching NaNs are not drawn.
    Z = np.array(surface.h * float(z_scale), dtype=float, copy=True)
    Z[~np.isfinite(Z)] = np.nan
    vm = getattr(surface, "valid_mask", None)
    if vm is not None:
        vm = cast(np.ndarray, vm)
        if vm.shape == Z.shape:
            Z[~vm] = np.nan

    fig = plt.figure(figsize=(7.2, 5.2), dpi=int(dpi))
    ax = cast(Any, fig.add_subplot(111, projection="3d"))

    s = max(int(stride), 1)
    a = float(np.clip(float(alpha), 0.0, 1.0))
    ax.plot_surface(
        X[::s, ::s],
        Y[::s, ::s],
        Z[::s, ::s],
        cmap=cmap,
        alpha=a,
        linewidth=0.0,
        antialiased=True,
        rcount=Z[::s, ::s].shape[0],
        ccount=Z[::s, ::s].shape[1],
    )

    ax.set_xlabel("x (mm)")
    ax.set_ylabel("y (mm)")
    ax.set_zlabel(f"Height ({z_unit})")
    ax.set_title(title)
    ax.view_init(elev=float(elev), azim=float(azim))
    if zlim is not None:
        ax.set_zlim(float(zlim[0]), float(zlim[1]))

    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
