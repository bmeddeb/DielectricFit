from __future__ import annotations

import logging
from typing import Iterable

import numpy as np

logger = logging.getLogger(__name__)

"""
NOTE: Placeholder implementations
These smoothing functions are minimal, dependency‑light versions intended
for wiring and demos. They are NOT production‑ready. Replace with SciPy
counterparts (e.g., scipy.signal.savgol_filter) for validated behavior
and better numerical performance.
"""


def moving_average(y: Iterable[float], window: int = 5) -> np.ndarray:
    """Simple centered moving average with edge padding.

    Args:
        y: Sequence of values.
        window: Odd window length >= 1.
    Returns:
        Smoothed array.
    """
    y = np.asarray(y, dtype=float)
    window = max(1, int(window))
    if window % 2 == 0:
        window += 1
    if window == 1 or y.size == 0:
        return y.copy()

    pad = window // 2
    ypad = np.pad(y, (pad, pad), mode="edge")
    kernel = np.ones(window, dtype=float) / window
    return np.convolve(ypad, kernel, mode="valid")


def gaussian_smooth(y: Iterable[float], sigma: float = 2.0, radius: int | None = None) -> np.ndarray:
    """Gaussian smoothing via discrete convolution with a Gaussian kernel.

    Args:
        y: Sequence of values.
        sigma: Standard deviation of kernel, in samples.
        radius: Optional kernel radius; defaults to 3*sigma.
    """
    y = np.asarray(y, dtype=float)
    if y.size == 0 or sigma <= 0:
        return y.copy()
    if radius is None:
        radius = int(max(1, round(3 * sigma)))
    x = np.arange(-radius, radius + 1, dtype=float)
    kernel = np.exp(-0.5 * (x / sigma) ** 2)
    kernel /= kernel.sum()
    ypad = np.pad(y, (radius, radius), mode="edge")
    return np.convolve(ypad, kernel, mode="valid")


def median_smooth(y: Iterable[float], window: int = 5) -> np.ndarray:
    """Median filter with edge padding and odd window enforcement."""
    y = np.asarray(y, dtype=float)
    window = max(1, int(window))
    if window % 2 == 0:
        window += 1
    if window == 1 or y.size == 0:
        return y.copy()
    pad = window // 2
    ypad = np.pad(y, (pad, pad), mode="edge")
    out = np.empty_like(y, dtype=float)
    for i in range(out.size):
        out[i] = np.median(ypad[i : i + window])
    return out


def savitzky_golay(y: Iterable[float], window: int = 7, polyorder: int = 3) -> np.ndarray:
    """Savitzky–Golay smoothing.

    Note: This is a lightweight fallback that fits local polynomials via least squares.
    It avoids SciPy dependency; for production accuracy and speed, consider
    replacing with `scipy.signal.savgol_filter` when available.
    """
    y = np.asarray(y, dtype=float)
    n = y.size
    window = max(3, int(window))
    if window % 2 == 0:
        window += 1
    polyorder = max(1, int(polyorder))
    if polyorder >= window:
        polyorder = window - 1
    if n == 0 or window <= 1:
        return y.copy()

    half = window // 2
    ypad = np.pad(y, (half, half), mode="edge")
    x = np.arange(window) - half
    # Precompute Vandermonde pseudoinverse weights for the center sample
    V = np.vander(x, N=polyorder + 1, increasing=True)
    Vinv = np.linalg.pinv(V)
    w_center = Vinv[0]  # coefficient for the constant term at x=0
    # Compute smoothing by sliding dot with polynomial fit evaluated at 0
    out = np.empty(n, dtype=float)
    for i in range(n):
        ywin = ypad[i : i + window]
        coeffs = Vinv @ ywin
        out[i] = coeffs[0]
    return out
