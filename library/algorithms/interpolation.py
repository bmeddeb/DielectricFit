"""Interpolation utilities with dedup options and unified extrapolation modes.

This module adds two "fancy" knobs across functions:
  1) `deduplicate`: how to handle duplicate x-values ("raise" | "first" | "mean").
  2) `extrapolation`: unified out-of-bounds behavior across methods:
     - "extrapolate": evaluate the underlying interpolant out of range
                      (for linear, we do true linear extension).
     - "const":       clamp to the end values (constant extension).
     - "nan":         fill out-of-range with NaN.
     - "periodic":    wrap x_new into the data domain assuming period = x[-1]-x[0].

Notes
-----
- Many SciPy 1D interpolators require strictly increasing x.
- We enforce "strictly increasing" (no duplicates) by default, but you can
  set `deduplicate` to "first" or "mean" to resolve duplicates.
- For Cubic/BSpline periodic BCs, we pre-check y[0] == y[-1].
- RBF: If the chosen kernel needs `epsilon` and it's None, we infer a reasonable
  value from the median spacing of unique x's.
"""

from __future__ import annotations

from typing import Literal, Tuple
import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy import interpolate

Extrapolation = Literal['extrapolate', 'const', 'nan', 'periodic']
DedupHow = Literal['raise', 'first', 'mean']

__all__ = [
    'linear_interpolate',
    'pchip_interpolate',
    'cubic_spline_interpolate',
    'bspline_interpolate',
    'akima_interpolate',
    'rbf_interpolate',
    'nearest_neighbor_interpolate',
    'barycentric_interpolate',
    'krogh_interpolate',
    'logarithmic_interpolate',
    'resample_uniform',
    # Backwards-compat alias:
    'make_interp_spline',
]

# ---------------------
# small private helpers
# ---------------------

def _as_1d_float(a: ArrayLike, name: str) -> NDArray[np.float64]:
    arr = np.asarray(a, dtype=float).reshape(-1)
    if arr.size == 0:
        raise ValueError(f"{name} is empty")
    if not np.all(np.isfinite(arr)):
        # Allow NaNs in y for some contexts? Here we keep it strict for simplicity.
        if name == 'y':
            # y may sometimes include NaNs in certain workflows; don't blanket-reject.
            pass
        else:
            if np.any(~np.isfinite(arr)):
                raise ValueError(f"{name} contains non-finite values")
    return arr

def _require_sorted_increasing(x: NDArray[np.float64]) -> None:
    if not np.all(np.diff(x) >= 0):
        raise ValueError("x must be sorted in ascending order")

def _require_strictly_increasing(x: NDArray[np.float64]) -> None:
    if not np.all(np.diff(x) > 0):
        raise ValueError("x must be strictly increasing (no duplicates)")

def _dedup_xy(x: NDArray[np.float64],
              y: NDArray[np.float64],
              how: DedupHow) -> Tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Resolve duplicates in x according to `how`."""
    if np.all(np.diff(x) > 0):
        return x, y  # already strictly increasing
    if how == 'raise':
        raise ValueError("x contains duplicates; set deduplicate to 'first' or 'mean'")
    xu, inv = np.unique(x, return_inverse=True)
    if how == 'first':
        # keep the first occurrence's y
        yi = np.empty_like(xu, dtype=float)
        seen = np.full(xu.shape, False, dtype=bool)
        for i, xi in enumerate(x):
            j = inv[i]
            if not seen[j]:
                yi[j] = y[i]
                seen[j] = True
        return xu, yi
    # mean
    yi = np.array([y[inv == j].mean() for j in range(xu.size)], dtype=float)
    return xu, yi

def _prepare_xy(
    x: ArrayLike,
    y: ArrayLike,
    *,
    require_strict: bool,
    deduplicate: DedupHow
) -> Tuple[NDArray[np.float64], NDArray[np.float64]]:
    x = _as_1d_float(x, 'x')
    y = _as_1d_float(y, 'y')
    if x.size != y.size:
        raise ValueError(f"x and y must have the same length, got {x.size} and {y.size}")
    _require_sorted_increasing(x)
    if require_strict:
        if not np.all(np.diff(x) > 0):
            x, y = _dedup_xy(x, y, deduplicate)
            # after dedup, ensure strictly increasing:
            _require_strictly_increasing(x)
    return x, y

def _fold_periodic(x_new: NDArray[np.float64], x0: float, xN: float) -> NDArray[np.float64]:
    T = xN - x0
    if T <= 0:
        raise ValueError("Cannot apply periodic extrapolation when x[-1] <= x[0]")
    return ((x_new - x0) % T) + x0

def _apply_const(y: NDArray[np.float64],
                 x: NDArray[np.float64],
                 x_new: NDArray[np.float64]) -> NDArray[np.float64]:
    x0, xN = x[0], x[-1]
    left_mask = x_new < x0
    right_mask = x_new > xN
    y0, yN = y[0], y[-1]
    out = np.interp(np.clip(x_new, x0, xN), x, y)
    out[left_mask] = y0
    out[right_mask] = yN
    return out

def _evaluate_with_extrapolation(
    evaluate_fn,
    x: NDArray[np.float64],
    y: NDArray[np.float64],
    x_new: NDArray[np.float64],
    extrapolation: Extrapolation
) -> NDArray[np.float64]:
    x0, xN = x[0], x[-1]
    if extrapolation == 'periodic':
        xn = _fold_periodic(x_new, x0, xN)
        return evaluate_fn(xn)
    elif extrapolation == 'const':
        # clamp to domain bounds
        xn = np.clip(x_new, x0, xN)
        return evaluate_fn(xn)
    elif extrapolation == 'nan':
        xn = np.clip(x_new, x0, xN)
        out = evaluate_fn(xn)
        oob = (x_new < x0) | (x_new > xN)
        if np.isscalar(out):
            return np.nan if oob else out
        out = np.asarray(out, dtype=float)
        out[oob] = np.nan
        return out
    else:  # 'extrapolate'
        return evaluate_fn(x_new)

# ---------------------
# public API functions
# ---------------------

def linear_interpolate(
    x: ArrayLike,
    y: ArrayLike,
    x_new: ArrayLike,
    *,
    extrapolation: Extrapolation = 'const',
    deduplicate: DedupHow = 'raise'
) -> NDArray[np.float64]:
    """Piecewise-linear interpolation with unified extrapolation options.

    Default matches numpy.interp's constant extension behavior.
    """
    x, y = _prepare_xy(x, y, require_strict=True, deduplicate=deduplicate)
    x_new = _as_1d_float(x_new, 'x_new')
    x0, xN = x[0], x[-1]

    if extrapolation == 'periodic':
        xn = _fold_periodic(x_new, x0, xN)
        return np.interp(xn, x, y)

    if extrapolation == 'const':
        return np.interp(x_new, x, y, left=y[0], right=y[-1])

    if extrapolation == 'nan':
        out = np.interp(x_new, x, y, left=np.nan, right=np.nan)
        return out

    # 'extrapolate' -> true linear extension using end slopes
    out = np.interp(np.clip(x_new, x0, xN), x, y)
    left_mask = x_new < x0
    right_mask = x_new > xN
    if np.any(left_mask):
        slope_left = (y[1] - y[0]) / (x[1] - x[0])
        out[left_mask] = y[0] + slope_left * (x_new[left_mask] - x0)
    if np.any(right_mask):
        slope_right = (y[-1] - y[-2]) / (x[-1] - x[-2])
        out[right_mask] = y[-1] + slope_right * (x_new[right_mask] - xN)
    return out

def pchip_interpolate(
    x: ArrayLike,
    y: ArrayLike,
    x_new: ArrayLike,
    *,
    extrapolation: Extrapolation = 'nan',
    deduplicate: DedupHow = 'raise'
) -> NDArray[np.float64]:
    """PCHIP monotone cubic interpolation with extrapolation control (default NaN)."""
    x, y = _prepare_xy(x, y, require_strict=True, deduplicate=deduplicate)
    x_new = _as_1d_float(x_new, 'x_new')
    p = interpolate.PchipInterpolator(x, y, extrapolate=True)
    return _evaluate_with_extrapolation(p.__call__, x, y, x_new, extrapolation)

def cubic_spline_interpolate(
    x: ArrayLike,
    y: ArrayLike,
    x_new: ArrayLike,
    *,
    bc_type: str | Tuple[str, float] | Tuple[str, float, str, float] = 'not-a-knot',
    extrapolation: Extrapolation = 'extrapolate',
    deduplicate: DedupHow = 'raise'
) -> NDArray[np.float64]:
    """Cubic spline interpolation.

    Parameters
    ----------
    bc_type : str or tuple
        Boundary condition: e.g., 'not-a-knot', 'natural', 'clamped', or
        'periodic'. If 'periodic', requires y[0] == y[-1].
    extrapolation : {'extrapolate','const','nan','periodic'}
        Out-of-bounds behavior (wrapper-level). Under the hood, we always
        construct with extrapolate=True and then post-process.
    """
    x, y = _prepare_xy(x, y, require_strict=True, deduplicate=deduplicate)
    if bc_type == 'periodic' and not np.isclose(y[0], y[-1], rtol=0, atol=np.finfo(float).eps * 10):
        raise ValueError("For bc_type='periodic', y[0] must equal y[-1].")
    x_new = _as_1d_float(x_new, 'x_new')
    cs = interpolate.CubicSpline(x, y, bc_type=bc_type, extrapolate=True)
    return _evaluate_with_extrapolation(cs.__call__, x, y, x_new, extrapolation)

def bspline_interpolate(
    x: ArrayLike,
    y: ArrayLike,
    x_new: ArrayLike,
    *,
    k: int = 3,
    bc_type: str | Tuple[str, float] | Tuple[str, float, str, float] | None = None,
    extrapolation: Extrapolation = 'extrapolate',
    deduplicate: DedupHow = 'raise'
) -> NDArray[np.float64]:
    """B-spline interpolation via make_interp_spline with k guardrails.

    Notes
    -----
    - Requires 1 <= k <= 5 and len(x) >= k+1.
    - If bc_type == 'periodic', requires y[0] == y[-1].
    """
    x, y = _prepare_xy(x, y, require_strict=True, deduplicate=deduplicate)
    k = int(k)
    if not (1 <= k <= 5):
        raise ValueError(f"k must be in [1, 5], got {k}")
    if x.size < k + 1:
        raise ValueError(f"Need at least {k+1} points for degree {k} spline")
    if bc_type == 'periodic' and not np.isclose(y[0], y[-1], rtol=0, atol=np.finfo(float).eps * 10):
        raise ValueError("For bc_type='periodic', y[0] must equal y[-1].")
    x_new = _as_1d_float(x_new, 'x_new')
    bspline = interpolate.make_interp_spline(x, y, k=k, bc_type=bc_type)
    return _evaluate_with_extrapolation(bspline.__call__, x, y, x_new, extrapolation)

# Backwards-compat alias to avoid breaking existing imports
make_interp_spline = bspline_interpolate

def akima_interpolate(
    x: ArrayLike,
    y: ArrayLike,
    x_new: ArrayLike,
    *,
    extrapolation: Extrapolation = 'extrapolate',
    deduplicate: DedupHow = 'raise'
) -> NDArray[np.float64]:
    """Akima 1D interpolation with extrapolation control."""
    x, y = _prepare_xy(x, y, require_strict=True, deduplicate=deduplicate)
    x_new = _as_1d_float(x_new, 'x_new')
    ak = interpolate.Akima1DInterpolator(x, y)  # Akima extrapolates by default
    return _evaluate_with_extrapolation(ak.__call__, x, y, x_new, extrapolation)

def nearest_neighbor_interpolate(
    x: ArrayLike,
    y: ArrayLike,
    x_new: ArrayLike,
    *,
    extrapolation: Extrapolation = 'const',
    deduplicate: DedupHow = 'raise'
) -> NDArray[np.float64]:
    """Nearest-neighbor interpolation with unified extrapolation."""
    x, y = _prepare_xy(x, y, require_strict=True, deduplicate=deduplicate)
    x_new = _as_1d_float(x_new, 'x_new')
    if extrapolation == 'periodic':
        xn = _fold_periodic(x_new, x[0], x[-1])
        f = interpolate.interp1d(x, y, kind='nearest', bounds_error=False, fill_value=(y[0], y[-1]))
        return f(xn)
    if extrapolation == 'const':
        f = interpolate.interp1d(x, y, kind='nearest', bounds_error=False, fill_value=(y[0], y[-1]))
        return f(x_new)
    if extrapolation == 'nan':
        f = interpolate.interp1d(x, y, kind='nearest', bounds_error=False, fill_value=np.nan)
        return f(x_new)
    # extrapolate
    f = interpolate.interp1d(x, y, kind='nearest', bounds_error=False, fill_value='extrapolate')
    return f(x_new)

def barycentric_interpolate(
    x: ArrayLike,
    y: ArrayLike,
    x_new: ArrayLike,
    *,
    extrapolation: Extrapolation = 'extrapolate',
    deduplicate: DedupHow = 'raise'
) -> NDArray[np.float64]:
    """Polynomial interpolation using barycentric form.

    Note: This method can oscillate for high-degree polynomials.
    """
    x, y = _prepare_xy(x, y, require_strict=True, deduplicate=deduplicate)
    x_new = _as_1d_float(x_new, 'x_new')
    def eval_bary(z):
        return interpolate.barycentric_interpolate(x, y, z)
    return _evaluate_with_extrapolation(eval_bary, x, y, x_new, extrapolation)

def krogh_interpolate(
    x: ArrayLike,
    y: ArrayLike,
    x_new: ArrayLike,
    *,
    extrapolation: Extrapolation = 'extrapolate',
    deduplicate: DedupHow = 'raise'
) -> NDArray[np.float64]:
    """Polynomial interpolation using Krogh's method (Hermite form)."""
    x, y = _prepare_xy(x, y, require_strict=True, deduplicate=deduplicate)
    x_new = _as_1d_float(x_new, 'x_new')
    ki = interpolate.KroghInterpolator(x, y)
    return _evaluate_with_extrapolation(ki.__call__, x, y, x_new, extrapolation)

def logarithmic_interpolate(
    x: ArrayLike,
    y: ArrayLike,
    x_new: ArrayLike,
    *,
    base: float = 10.0,
    extrapolation: Extrapolation = 'const',
    deduplicate: DedupHow = 'raise'
) -> NDArray[np.float64]:
    """Interpolate linearly on a logarithmic x-scale.

    Requires x > 0 and x_new > 0.
    """
    if base <= 0 or base == 1:
        raise ValueError(f"base must be > 0 and != 1, got {base}")
    x, y = _prepare_xy(x, y, require_strict=True, deduplicate=deduplicate)
    if np.any(x <= 0):
        raise ValueError("All x must be > 0 for logarithmic interpolation")
    x_new = _as_1d_float(x_new, 'x_new')
    if np.any(x_new <= 0):
        raise ValueError("All x_new must be > 0 for logarithmic interpolation")

    lx = np.log(x) / np.log(base)
    lx_new = np.log(x_new) / np.log(base)

    # Reuse linear implementation on transformed grid
    return linear_interpolate(lx, y, lx_new, extrapolation=extrapolation, deduplicate='raise')

def rbf_interpolate(
    x: ArrayLike,
    y: ArrayLike,
    x_new: ArrayLike,
    *,
    function: str = 'multiquadric',
    epsilon: float | None = None,
    smooth: float = 0.0,
    deduplicate: DedupHow = 'raise'
) -> NDArray[np.float64]:
    """Radial Basis Function interpolation with auto-epsilon when needed.

    Parameters
    ----------
    function : str
        Kernel name (e.g., 'multiquadric', 'inverse', 'gaussian', 'linear',
        'cubic', 'quintic', 'thin_plate_spline').
    epsilon : float | None
        If None and the kernel requires it, we infer epsilon from data spacing.
    smooth : float
        Smoothing parameter passed to RBFInterpolator.
    """
    x, y = _prepare_xy(x, y, require_strict=True, deduplicate=deduplicate)
    x_new = _as_1d_float(x_new, 'x_new')
    # RBFInterpolator expects 2D X of shape (n_samples, n_features)
    X = x.reshape(-1, 1)
    Xn = x_new.reshape(-1, 1)

    # Determine if epsilon is required for the chosen kernel
    scale_invariant = {'cubic', 'quintic', 'linear', 'thin_plate_spline'}
    if epsilon is None and function not in scale_invariant:
        xu = np.unique(x)
        if xu.size > 1:
            eps = float(np.median(np.diff(xu)))
        else:
            eps = 1.0
        if not np.isfinite(eps) or eps == 0.0:
            span = float(xu.max() - xu.min()) if xu.size > 0 else 1.0
            eps = span / max(int(xu.size), 1)
            if eps == 0.0:
                eps = 1.0
        epsilon = eps

    rbf = interpolate.RBFInterpolator(X, y, kernel=function, epsilon=epsilon, smoothing=smooth)
    # RBF extrapolates by construction; we map modes for consistency
    def eval_rbf(z):
        return rbf(z.reshape(-1, 1))

    return _evaluate_with_extrapolation(lambda z: eval_rbf(z), x, y, x_new, 'extrapolate' if True else 'extrapolate')

def resample_uniform(
    x: ArrayLike,
    y: ArrayLike,
    num_points: int,
    *,
    method: Literal['linear','pchip','cubic','akima','nearest','bspline','rbf'] = 'linear',
    extrapolation: Extrapolation = 'nan',
    deduplicate: DedupHow = 'raise',
    **method_kwargs
) -> Tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Resample (x, y) onto a uniform grid of `num_points` within [x[0], x[-1]].

    Parameters
    ----------
    method : {'linear','pchip','cubic','akima','nearest','bspline','rbf'}
        Interpolation method to use.
    extrapolation : {'extrapolate','const','nan','periodic'}
        Out-of-bounds behavior when evaluating (shouldn't matter for the interior grid).
    method_kwargs : dict
        Extra kwargs passed through to the chosen interpolator.
    """
    if num_points < 2:
        raise ValueError("num_points must be at least 2")
    x, y = _prepare_xy(x, y, require_strict=True, deduplicate=deduplicate)
    x_new = np.linspace(x[0], x[-1], int(num_points), dtype=float)

    if method == 'linear':
        y_new = linear_interpolate(x, y, x_new, extrapolation=extrapolation, deduplicate='raise')
    elif method == 'pchip':
        y_new = pchip_interpolate(x, y, x_new, extrapolation=extrapolation, deduplicate='raise')
    elif method == 'cubic':
        y_new = cubic_spline_interpolate(x, y, x_new, extrapolation=extrapolation, deduplicate='raise', **method_kwargs)
    elif method == 'akima':
        y_new = akima_interpolate(x, y, x_new, extrapolation=extrapolation, deduplicate='raise')
    elif method == 'nearest':
        y_new = nearest_neighbor_interpolate(x, y, x_new, extrapolation=extrapolation, deduplicate='raise')
    elif method == 'bspline':
        y_new = bspline_interpolate(x, y, x_new, extrapolation=extrapolation, deduplicate='raise', **method_kwargs)
    elif method == 'rbf':
        y_new = rbf_interpolate(x, y, x_new, deduplicate='raise', **method_kwargs)
    else:
        raise ValueError(f"Unknown method: {method!r}")

    return x_new, y_new
