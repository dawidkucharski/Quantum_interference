from __future__ import annotations

import matplotlib as mpl


def apply_publication_style(*, base_fontsize: float = 8.5) -> None:
    """Apply a compact publication style suitable for MDPI Photonics figures."""

    mpl.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
            "mathtext.fontset": "dejavusans",
            "font.size": base_fontsize,
            "axes.titlesize": base_fontsize + 0.5,
            "axes.labelsize": base_fontsize,
            "xtick.labelsize": base_fontsize - 1.0,
            "ytick.labelsize": base_fontsize - 1.0,
            "legend.fontsize": base_fontsize - 0.5,
            "axes.linewidth": 0.75,
            "lines.linewidth": 1.35,
            "lines.markersize": 3.4,
            "grid.linewidth": 0.5,
            "xtick.major.width": 0.75,
            "ytick.major.width": 0.75,
            "xtick.minor.width": 0.6,
            "ytick.minor.width": 0.6,
            "xtick.direction": "out",
            "ytick.direction": "out",
            "legend.frameon": False,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "svg.fonttype": "none",
            "savefig.bbox": "tight",
            "savefig.pad_inches": 0.08,
        }
    )