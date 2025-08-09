from __future__ import annotations

from typing import Iterable

import numpy as np

"""
NOTE: Placeholder implementations
Interpolation routines here avoid SciPy to keep the project lightweight.
`pchip_interpolate` currently falls back to linear interpolation and is NOT
production‑ready. Use `scipy.interpolate.PchipInterpolator` when available.
"""


def linear_interpolate(x: Iterable[float], y: Iterable[float], x_new: Iterable[float]) -> np.ndarray:
    """1D linear interpolation using numpy.interp.

    Args:
        x: Strictly increasing x grid.
        y: Values at x.
        x_new: New x grid to interpolate to.
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    x_new = np.asarray(x_new, dtype=float)
    return np.interp(x_new, x, y)


def pchip_interpolate(x: Iterable[float], y: Iterable[float], x_new: Iterable[float]) -> np.ndarray:
    """Placeholder for PCHIP (monotone) interpolation.

    For production use, prefer scipy.interpolate.PchipInterpolator. This
    placeholder currently falls back to linear interpolation to avoid extra deps.
    """
    # Fallback: linear interpolation
    return linear_interpolate(x, y, x_new)
