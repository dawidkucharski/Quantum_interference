from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import struct
from typing import Optional, Union

import numpy as np

from .metrics import Roughness


@dataclass(frozen=True)
class Surface:
    x: np.ndarray  # (W,)
    y: np.ndarray  # (H,)
    h: np.ndarray  # (H, W) height in meters
    valid_mask: Optional[np.ndarray] = None  # (H, W) True where measured height is valid


def _rng(seed: Optional[int]) -> np.random.Generator:
    return np.random.default_rng(seed)


def make_surface(
    *,
    nx: int = 256,
    ny: int = 256,
    size_x: float = 1e-3,
    size_y: float = 1e-3,
    kind: str = "gaussian_rough",
    rms: float = 50e-9,
    corr_len: float = 20e-6,
    step_height: float = 0.0,
    step_x: Optional[float] = None,
    seed: Optional[int] = 0,
) -> Surface:
    """Create a synthetic surface height map.

    Parameters
    - rms: target RMS height (meters) for the rough component.
    - corr_len: correlation length (meters) for roughness.
    - step_height: optional step discontinuity height (meters).
    - step_x: x-position of the step; defaults to mid-field.
    """

    x = np.linspace(0.0, size_x, nx, endpoint=False)
    y = np.linspace(0.0, size_y, ny, endpoint=False)

    if kind not in {"flat", "gaussian_rough"}:
        raise ValueError(f"Unknown kind={kind!r}")

    h = np.zeros((ny, nx), dtype=float)

    if kind == "gaussian_rough":
        # White noise filtered by a Gaussian kernel in Fourier domain
        gen = _rng(seed)
        w = gen.standard_normal((ny, nx))

        fx = np.fft.fftfreq(nx, d=size_x / nx)
        fy = np.fft.fftfreq(ny, d=size_y / ny)
        FX, FY = np.meshgrid(fx, fy)
        k2 = (2.0 * np.pi * FX) ** 2 + (2.0 * np.pi * FY) ** 2

        # Gaussian correlation: exp(-(r^2)/(2*L^2)) -> spectrum ~ exp(-k^2 L^2 /2)
        Hk = np.exp(-0.5 * k2 * corr_len**2)
        filtered = np.fft.ifft2(np.fft.fft2(w) * Hk).real

        filtered -= filtered.mean()
        current_rms = np.sqrt(np.mean(filtered**2))
        if current_rms > 0:
            filtered *= (rms / current_rms)
        h += filtered

    if step_height != 0.0:
        if step_x is None:
            step_x = 0.5 * size_x
        h = h + (x[None, :] >= step_x) * step_height

    return Surface(x=x, y=y, h=h)


@dataclass(frozen=True)
class DigitalSurfSurHeader:
    nx: int
    ny: int
    n_total: int
    size_x: float
    size_y: float
    size_unit_x: str
    size_unit_y: str
    z_scale: float
    z_offset: float
    z_unit: str
    data_offset_bytes: int
    bytes_per_point: int
    invalid_u16: int


def _sur_dtype_from_header(hdr: DigitalSurfSurHeader) -> np.dtype:
    if hdr.bytes_per_point == 2:
        return np.dtype("<u2")
    if hdr.bytes_per_point == 4:
        return np.dtype("<i4")
    raise ValueError(f"Unsupported bytes_per_point={hdr.bytes_per_point}")


def _sur_z_scale_m_from_header(hdr: DigitalSurfSurHeader) -> float:
    z_unit_to_m = _unit_to_m(hdr.z_unit)
    z_scale_raw = float(hdr.z_scale)
    if np.isfinite(z_scale_raw) and z_scale_raw != 0.0:
        z_scale_raw = abs(z_scale_raw)
        if z_scale_raw < 1e-6:
            z_scale_m = z_scale_raw
        else:
            z_scale_m = z_scale_raw * z_unit_to_m
    else:
        z_scale_m = z_unit_to_m

    if not (1e-15 <= float(z_scale_m) <= 1e-6):
        z_scale_m = z_unit_to_m
    return float(z_scale_m)


def _open_sur_memmap(path: Union[str, Path], hdr: DigitalSurfSurHeader) -> np.memmap:
    dtype = _sur_dtype_from_header(hdr)
    return np.memmap(
        Path(path),
        dtype=dtype,
        mode="r",
        offset=hdr.data_offset_bytes,
        shape=(hdr.ny, hdr.nx),
        order="C",
    )


def _sur_valid_mask(raw: np.ndarray, *, dtype: np.dtype) -> np.ndarray:
    valid = np.isfinite(raw)
    if dtype == np.dtype("<u2"):
        valid &= (raw != 0xFFFE) & (raw != 0xFFFF)
    return valid


def _downsample_sur_index(mm: np.memmap, hdr: DigitalSurfSurHeader, *, dtype: np.dtype, target_nx: int, target_ny: int) -> tuple[np.ndarray, np.ndarray]:
    iy = np.linspace(0, hdr.ny - 1, int(target_ny), dtype=np.int64)
    ix = np.linspace(0, hdr.nx - 1, int(target_nx), dtype=np.int64)
    raw = np.asarray(mm[np.ix_(iy, ix)], dtype=np.float64)
    valid_mask = _sur_valid_mask(raw, dtype=dtype)
    raw = np.where(valid_mask, raw, np.nan)
    return raw, valid_mask


def _downsample_sur_area(mm: np.memmap, hdr: DigitalSurfSurHeader, *, dtype: np.dtype, target_nx: int, target_ny: int) -> tuple[np.ndarray, np.ndarray]:
    if target_nx > hdr.nx or target_ny > hdr.ny:
        return _downsample_sur_index(mm, hdr, dtype=dtype, target_nx=target_nx, target_ny=target_ny)

    x_edges = np.floor(np.linspace(0, hdr.nx, int(target_nx) + 1)).astype(np.int64)
    y_edges = np.floor(np.linspace(0, hdr.ny, int(target_ny) + 1)).astype(np.int64)
    x_edges[-1] = int(hdr.nx)
    y_edges[-1] = int(hdr.ny)

    if np.any(np.diff(x_edges) <= 0) or np.any(np.diff(y_edges) <= 0):
        return _downsample_sur_index(mm, hdr, dtype=dtype, target_nx=target_nx, target_ny=target_ny)

    x_starts = x_edges[:-1]
    raw_sum = np.zeros((int(target_ny), int(target_nx)), dtype=np.float64)
    valid_sum = np.zeros((int(target_ny), int(target_nx)), dtype=np.float64)

    for out_y, (y0, y1) in enumerate(zip(y_edges[:-1], y_edges[1:])):
        block = np.asarray(mm[int(y0) : int(y1), :], dtype=np.float64)
        valid = _sur_valid_mask(block, dtype=dtype)
        block = np.where(valid, block, 0.0)

        raw_cols = np.add.reduceat(block, x_starts, axis=1)
        valid_cols = np.add.reduceat(valid.astype(np.float64), x_starts, axis=1)
        raw_sum[out_y, :] = np.sum(raw_cols, axis=0)
        valid_sum[out_y, :] = np.sum(valid_cols, axis=0)

    raw = np.divide(raw_sum, valid_sum, out=np.full_like(raw_sum, np.nan), where=valid_sum > 0.0)
    valid_mask = valid_sum > 0.0
    return raw, valid_mask


def roughness_metrics_sur_reference(
    path: Union[str, Path],
    *,
    block_rows: int = 512,
) -> Roughness:
    """Compute strict reference roughness directly from a native-resolution `.sur` file.

    This path is intended for metrological reference values. It keeps the native
    grid, removes only explicit invalid sentinels, detrends by a best-fit plane,
    and then computes Sa, Sq, and Sz over the valid pixels.
    """

    hdr = read_digital_surf_sur_header(path)
    mm = _open_sur_memmap(path, hdr)
    dtype = _sur_dtype_from_header(hdr)
    z_scale_m = _sur_z_scale_m_from_header(hdr)
    nx = int(hdr.nx)
    ny = int(hdr.ny)

    x = np.arange(nx, dtype=np.float64)
    x2 = x * x

    sum_n = 0.0
    sum_x = 0.0
    sum_y = 0.0
    sum_z = 0.0
    sum_xx = 0.0
    sum_yy = 0.0
    sum_xy = 0.0
    sum_xz = 0.0
    sum_yz = 0.0

    for y0 in range(0, ny, int(block_rows)):
        y1 = min(y0 + int(block_rows), ny)
        raw = np.asarray(mm[y0:y1, :], dtype=np.float64)
        if dtype == np.dtype("<u2"):
            valid = (raw != 0xFFFE) & (raw != 0xFFFF)
        else:
            valid = np.ones_like(raw, dtype=bool)

        if not bool(np.any(valid)):
            continue

        z = raw * z_scale_m
        y = np.arange(y0, y1, dtype=np.float64)
        row_counts = np.sum(valid, axis=1, dtype=np.float64)
        col_counts = np.sum(valid, axis=0, dtype=np.float64)

        sum_n += float(np.sum(row_counts))
        sum_x += float(np.dot(col_counts, x))
        sum_y += float(np.dot(row_counts, y))
        sum_xx += float(np.dot(col_counts, x2))
        sum_yy += float(np.dot(row_counts, y * y))
        sum_xy += float(np.dot(np.sum(valid * x[None, :], axis=1, dtype=np.float64), y))

        z_valid = np.where(valid, z, 0.0)
        sum_z += float(np.sum(z_valid, dtype=np.float64))
        sum_xz += float(np.sum(z_valid * x[None, :], dtype=np.float64))
        sum_yz += float(np.sum(z_valid * y[:, None], dtype=np.float64))

    if sum_n < 3.0:
        return Roughness(Sa=float("nan"), Sq=float("nan"), Sz=float("nan"))

    normal = np.array(
        [[sum_xx, sum_xy, sum_x], [sum_xy, sum_yy, sum_y], [sum_x, sum_y, sum_n]],
        dtype=np.float64,
    )
    rhs = np.array([sum_xz, sum_yz, sum_z], dtype=np.float64)
    coeff = np.linalg.solve(normal, rhs)

    sum_abs = 0.0
    sum_sq = 0.0
    min_res = float("inf")
    max_res = float("-inf")
    n_valid = 0.0

    for y0 in range(0, ny, int(block_rows)):
        y1 = min(y0 + int(block_rows), ny)
        raw = np.asarray(mm[y0:y1, :], dtype=np.float64)
        if dtype == np.dtype("<u2"):
            valid = (raw != 0xFFFE) & (raw != 0xFFFF)
        else:
            valid = np.ones_like(raw, dtype=bool)

        if not bool(np.any(valid)):
            continue

        z = raw * z_scale_m
        y = np.arange(y0, y1, dtype=np.float64)
        plane = coeff[0] * x[None, :] + coeff[1] * y[:, None] + coeff[2]
        res = z - plane
        vals = res[valid]
        if vals.size == 0:
            continue

        sum_abs += float(np.sum(np.abs(vals), dtype=np.float64))
        sum_sq += float(np.sum(vals * vals, dtype=np.float64))
        min_res = min(min_res, float(np.min(vals)))
        max_res = max(max_res, float(np.max(vals)))
        n_valid += float(vals.size)

    if n_valid == 0.0:
        return Roughness(Sa=float("nan"), Sq=float("nan"), Sz=float("nan"))

    return Roughness(
        Sa=float(sum_abs / n_valid),
        Sq=float(np.sqrt(sum_sq / n_valid)),
        Sz=float(max_res - min_res),
    )


def _read_fixed_str(buf: bytes, offset: int, length: int) -> str:
    raw = buf[offset : offset + length]
    raw = raw.split(b"\x00", 1)[0]
    return raw.decode("latin1", errors="replace").strip()


def _unit_to_m(unit: str) -> float:
    u = unit.strip().lower().replace("µ", "u")
    if u in {"m", "meter", "metre"}:
        return 1.0
    if u in {"mm"}:
        return 1e-3
    if u in {"um", "micrometer", "micrometre"}:
        return 1e-6
    if u in {"nm"}:
        return 1e-9
    raise ValueError(f"Unsupported unit in .sur header: {unit!r}")


def read_digital_surf_sur_header(path: Union[str, Path]) -> DigitalSurfSurHeader:
    """Parse a Digital Surf / MountainsMap `.sur` file header.

    This implementation is intentionally minimal and targets the common
    'DIGITAL SURF' 512-byte header layout.
    """

    p = Path(path)
    with p.open("rb") as f:
        header = f.read(512)
    if len(header) < 512:
        raise ValueError(".sur file is too small to contain a 512-byte header")
    sig = _read_fixed_str(header, 0x00, 12)
    if sig != "DIGITAL SURF":
        raise ValueError(f"Not a Digital Surf/Mountains .sur file (signature={sig!r})")

    nx = struct.unpack_from("<I", header, 0x6C)[0]
    ny = struct.unpack_from("<I", header, 0x70)[0]
    n_total = struct.unpack_from("<I", header, 0x74)[0]
    if nx <= 0 or ny <= 0:
        raise ValueError(f"Invalid .sur dimensions nx={nx}, ny={ny}")
    if n_total != nx * ny:
        raise ValueError(f"Header n_total={n_total} does not match nx*ny={nx*ny}")

    size_x = struct.unpack_from("<f", header, 0x78)[0]
    size_y = struct.unpack_from("<f", header, 0x7C)[0]

    # Units appear as 16-byte fixed strings; for MountainsMap exports,
    # the lateral size units are typically stored at 0xE0/0xF0.
    size_unit_x = _read_fixed_str(header, 0xE0, 16) or "m"
    size_unit_y = _read_fixed_str(header, 0xF0, 16) or "m"

    # In practice (for the provided dataset), the height unit label is stored
    # as 'nm' in the 0xB0/0xC0 region, while 0x100 may contain a different unit.
    # We'll treat 0xB0 as the primary Z unit label.
    z_unit = _read_fixed_str(header, 0xB0, 16) or _read_fixed_str(header, 0xC0, 16) or "m"

    # Common layout: z_scale (float32) at 0x1D8 and z_offset (uint32) at 0x1DC.
    # Note: some exports encode z_scale directly in meters/count (~1e-10), while
    # others encode it in e.g. nm/count (order ~1e-1 to 1e2 with z_unit='nm').
    z_scale = struct.unpack_from("<f", header, 0x1D8)[0]
    z_offset = float(struct.unpack_from("<I", header, 0x1DC)[0])

    data_offset_bytes = 512
    file_size = p.stat().st_size
    payload = file_size - data_offset_bytes
    if payload <= 0:
        raise ValueError(".sur file has no payload after header")
    if payload % n_total != 0:
        raise ValueError(
            f".sur payload size {payload} is not divisible by n_total={n_total}; cannot infer point size"
        )
    bytes_per_point = payload // n_total
    if bytes_per_point not in {2, 4}:
        raise ValueError(f"Unsupported bytes_per_point={bytes_per_point} (expected 2 or 4)")

    # MountainsMap commonly uses 0xFFFE as an invalid sentinel for unsigned 16-bit.
    invalid_u16 = 0xFFFE

    return DigitalSurfSurHeader(
        nx=int(nx),
        ny=int(ny),
        n_total=int(n_total),
        size_x=float(size_x),
        size_y=float(size_y),
        size_unit_x=size_unit_x,
        size_unit_y=size_unit_y,
        z_scale=float(z_scale),
        z_offset=float(z_offset),
        z_unit=z_unit,
        data_offset_bytes=int(data_offset_bytes),
        bytes_per_point=int(bytes_per_point),
        invalid_u16=int(invalid_u16),
    )


def load_surface_sur(
    path: Union[str, Path],
    *,
    target_nx: int = 256,
    target_ny: int = 256,
    resample: str = "area",
    fill_invalid: str = "median",
) -> Surface:
    """Load a Mountains/DigitalSurf `.sur` file and return a `Surface`.

    The on-disk grids can be extremely large; by default this function downsamples
    to `target_nx` x `target_ny` via streaming area averaging, which better matches
    the reduced benchmark bandwidth than raw index subsampling.

    Invalid points are detected (including common uint16 sentinels and typical
    missing-data "plateaus") and tracked via `Surface.valid_mask`.

    `resample` may be:
    - 'area': area-averaged downsampling on the native grid (default)
    - 'index': legacy linspace index sampling for reproducibility checks

    Invalid points are replaced according to `fill_invalid`:
    - 'median': replace with the median of valid points in the *downsampled* grid
    - 'zero': replace with 0
    - 'nan': keep as NaN (may break algorithms that assume finite heights)
    """

    hdr = read_digital_surf_sur_header(path)
    p = Path(path)

    if target_nx <= 0 or target_ny <= 0:
        raise ValueError("target_nx and target_ny must be positive")

    # Infer dtype from bytes/point. This repo currently supports the common
    # uint16 (2 bytes) payload.
    if hdr.bytes_per_point == 2:
        dtype = np.dtype("<u2")
    elif hdr.bytes_per_point == 4:
        # Some SUR variants store int32 heights.
        dtype = np.dtype("<i4")
    else:
        raise ValueError(f"Unsupported bytes_per_point={hdr.bytes_per_point}")

    mm = np.memmap(
        p,
        dtype=dtype,
        mode="r",
        offset=hdr.data_offset_bytes,
        shape=(hdr.ny, hdr.nx),
        order="C",
    )

    if resample == "area":
        raw, valid_mask = _downsample_sur_area(mm, hdr, dtype=dtype, target_nx=int(target_nx), target_ny=int(target_ny))
    elif resample == "index":
        raw, valid_mask = _downsample_sur_index(mm, hdr, dtype=dtype, target_nx=int(target_nx), target_ny=int(target_ny))
    else:
        raise ValueError("resample must be one of: area, index")

    # Heuristic missing-data detection beyond explicit sentinels.
    # Many exports (both uint16 and int32) encode invalid regions as a constant
    # extreme value (often the minimum, sometimes the maximum) that occupies a
    # small but non-negligible fraction of the grid.
    finite = raw[np.isfinite(raw)]
    if finite.size > 0:
        min_val = float(np.nanmin(finite))
        max_val = float(np.nanmax(finite))
        min_frac = float(np.mean(finite == min_val))
        max_frac = float(np.mean(finite == max_val))
        p1, p5, p50, p95, p99 = [float(x) for x in np.nanpercentile(finite, [1.0, 5.0, 50.0, 95.0, 99.0])]
        spread = float(p99 - p1)

        # Treat a repeated extreme value as invalid when it is both:
        # (a) present in more than a tiny fraction of pixels, and
        # (b) separated from the bulk of the distribution.
        plateau_frac = 5e-4  # 0.05% of pixels (~33 px at 256x256)
        gap_frac = 0.15
        if spread > 0.0:
            if min_frac >= plateau_frac and (p5 - min_val) > gap_frac * spread:
                raw = np.where(raw == min_val, np.nan, raw)
            if max_frac >= plateau_frac and (max_val - p95) > gap_frac * spread:
                raw = np.where(raw == max_val, np.nan, raw)

    # Backward-compatible special-case for zeros as missing data.
    # Keep this conservative: only treat zeros as invalid if they are
    # frequent enough and clearly separated from the valid population.
    if dtype == np.dtype("<u2"):
        zero_frac = float(np.mean(raw == 0.0))
        if zero_frac > 0.001 and np.isfinite(raw).any():
            raw_nonzero = raw[(raw != 0.0) & np.isfinite(raw)]
            if raw_nonzero.size > 0 and float(np.nanpercentile(raw_nonzero, 1.0)) > 10.0:
                raw = np.where(raw == 0.0, np.nan, raw)

    valid_mask = np.isfinite(raw)

    # Robust offset: center the data around the median count.
    # (Absolute offset does not affect roughness or RMSE-after-detrend, but a
    # bad header offset can unnecessarily inflate phase values.)
    if np.isfinite(raw).any():
        offset_counts = float(np.nanmedian(raw))
    else:
        offset_counts = 0.0

    # Robust z-scale: some files have nonsense values in the nominal z_scale
    # header field (e.g. ~1e21). Fall back to 1 * z_unit per count.
    z_unit_to_m = _unit_to_m(hdr.z_unit)
    z_scale_raw = float(hdr.z_scale)
    if np.isfinite(z_scale_raw) and z_scale_raw != 0.0:
        z_scale_raw = abs(z_scale_raw)
        if z_scale_raw < 1e-6:
            z_scale_m = z_scale_raw
        else:
            z_scale_m = z_scale_raw * z_unit_to_m
    else:
        z_scale_m = z_unit_to_m

    if not (1e-15 <= float(z_scale_m) <= 1e-6):
        z_scale_m = z_unit_to_m

    h_m = (raw - float(offset_counts)) * float(z_scale_m)

    # Robust outlier suppression: in measured maps, a tiny number of pixels may
    # take extreme values (e.g., line artifacts) while still looking "finite".
    # Mark these as invalid so they are excluded from plots/metrics.
    finite_h = h_m[valid_mask]
    if finite_h.size >= 100:
        p1_h, p99_h = [float(x) for x in np.nanpercentile(finite_h, [1.0, 99.0])]
        span_h = float(p99_h - p1_h)
        if np.isfinite(span_h) and span_h > 0.0:
            lo = p1_h - span_h
            hi = p99_h + span_h
            outliers = (h_m < lo) | (h_m > hi)
            if bool(np.any(outliers)):
                h_m = np.where(outliers, np.nan, h_m)
                valid_mask = valid_mask & (~outliers)

    if not np.isfinite(h_m).all():
        if fill_invalid == "nan":
            pass
        else:
            if fill_invalid == "median":
                if np.isfinite(h_m).any():
                    fill = float(np.nanmedian(h_m))
                else:
                    fill = 0.0
            elif fill_invalid == "zero":
                fill = 0.0
            else:
                raise ValueError("fill_invalid must be one of: median, zero, nan")
            h_m = np.nan_to_num(h_m, nan=fill, posinf=fill, neginf=fill)

    size_x_m = hdr.size_x * _unit_to_m(hdr.size_unit_x)
    size_y_m = hdr.size_y * _unit_to_m(hdr.size_unit_y)
    x = np.linspace(0.0, float(size_x_m), int(target_nx), endpoint=False)
    y = np.linspace(0.0, float(size_y_m), int(target_ny), endpoint=False)
    return Surface(x=x, y=y, h=h_m, valid_mask=valid_mask)
