"""
Kramers-Kronig validation and causality checking for dielectric data.

This module provides tools for validating experimental dielectric data using
Kramers–Kronig (KK) relations, which enforce causality constraints on the
complex permittivity ε(ω) = ε′(ω) - i ε″(ω).

Key improvements over the basic version:
- KK uses ε″(ω) (imag permittivity), not tanδ directly. We compute ε″ = ε′·tanδ.
- Hilbert method: odd extension of ε″ and optional taper + zero-padding; no window "undo".
- Non-uniform grids: resample to uniform ω for Hilbert, or use trapezoid with optional SSKK.
- Better PV handling in trapezoid: avoid dropping whole panels at the singular sample.
- Optional richer diagnostics in outputs.
"""

from __future__ import annotations

import logging
from typing import Dict, Any, Optional, Literal, Tuple

import numpy as np
import pandas as pd
from scipy.signal import hilbert, get_window, find_peaks
from scipy.interpolate import interp1d
from scipy.stats import linregress

# Optional Numba acceleration
try:
    from numba import njit, prange
    NUMBA_AVAILABLE = True
except Exception:  # pragma: no cover
    NUMBA_AVAILABLE = False

logger = logging.getLogger(__name__)

# --------------------
# Core KK primitives
# --------------------

if NUMBA_AVAILABLE:
    @njit(parallel=True, fastmath=True)
    def _kk_trapz_numba(omega: np.ndarray, eps_imag: np.ndarray, eps_inf: float) -> np.ndarray:
        """
        Trapezoidal KK on non-uniform grids (principal value) with per-endpoint guards.

        Parameters
        ----------
        omega : np.ndarray
            Angular frequency array (rad/s), strictly increasing
        eps_imag : np.ndarray
            Imaginary part of permittivity ε″(ω)
        eps_inf : float
            High-frequency permittivity limit

        Returns
        -------
        np.ndarray
            ε′(ω) reconstructed via KK
        """
        n = omega.size
        dk_kk = np.empty(n, dtype=np.float64)
        for i in prange(n):
            wi = omega[i]
            integral = 0.0
            for j in range(n - 1):
                wj, wj1 = omega[j], omega[j + 1]
                denom_j  = (wj * wj)  - (wi * wi)
                denom_j1 = (wj1 * wj1) - (wi * wi)
                # Per-endpoint PV guard: if denominator is zero at a sample, drop that endpoint only
                fj  = (wj  * eps_imag[j]     / denom_j)  if denom_j  != 0.0 else 0.0
                fj1 = (wj1 * eps_imag[j + 1] / denom_j1) if denom_j1 != 0.0 else 0.0
                integral += 0.5 * (fj + fj1) * (wj1 - wj)
            dk_kk[i] = eps_inf + (2.0 / np.pi) * integral
        return dk_kk
else:
    def _kk_trapz_numba(omega: np.ndarray, eps_imag: np.ndarray, eps_inf: float) -> np.ndarray:
        """
        Pure-Python trapezoidal KK (principal value) with per-endpoint guards.
        """
        n = omega.size
        dk_kk = np.empty(n, dtype=float)
        for i in range(n):
            wi = omega[i]
            integral = 0.0
            for j in range(n - 1):
                wj, wj1 = omega[j], omega[j + 1]
                denom_j  = (wj * wj)  - (wi * wi)
                denom_j1 = (wj1 * wj1) - (wi * wi)
                fj  = (wj  * eps_imag[j]     / denom_j)  if denom_j  != 0.0 else 0.0
                fj1 = (wj1 * eps_imag[j + 1] / denom_j1) if denom_j1 != 0.0 else 0.0
                integral += 0.5 * (fj + fj1) * (wj1 - wj)
            dk_kk[i] = eps_inf + (2.0 / np.pi) * integral
        return dk_kk

def _kk_trapz_sskk(omega: np.ndarray,
                   eps_imag: np.ndarray,
                   eps_inf: float,
                   dk_anchor: float,
                   omega_anchor: float) -> np.ndarray:
    """
    Singly subtractive KK via trapezoidal rule on non-uniform grids.

    This reduces finite-band truncation error. We still apply a principal-value
    style endpoint guard at the target sample.

    ε′(ω) = ε′(ω0) + (2(ω²-ω0²)/π) ∫₀^∞ [ Ω ε″(Ω) / ((Ω²-ω²)(Ω²-ω0²)) ] dΩ
    """
    w = omega
    y = eps_imag
    n = w.size
    out = np.empty(n, dtype=float)

    for i in range(n):
        wi2 = w[i] * w[i]
        w02 = omega_anchor * omega_anchor
        num_factor = 2.0 * (wi2 - w02) / np.pi
        integral = 0.0
        for j in range(n - 1):
            wj, wj1 = w[j], w[j + 1]
            # Endpoint-guarded integrand values
            denom_j  = (wj * wj - wi2) * (wj * wj - w02)
            denom_j1 = (wj1 * wj1 - wi2) * (wj1 * wj1 - w02)
            fj  = (wj  * y[j]     / denom_j)  if denom_j  != 0.0 else 0.0
            fj1 = (wj1 * y[j + 1] / denom_j1) if denom_j1 != 0.0 else 0.0
            integral += 0.5 * (fj + fj1) * (wj1 - wj)
        out[i] = dk_anchor + num_factor * integral

    return out

# --------------------
# Utility helpers
# --------------------

def _is_grid_uniform(frequency: np.ndarray, rtol: float = 1e-5, atol: float = 1e-8) -> bool:
    """Check if frequency grid is uniformly spaced (linear)."""
    diffs = np.diff(frequency)
    return np.allclose(diffs, diffs[0], rtol=rtol, atol=atol)

def _detect_peaks(df_values: np.ndarray) -> int:
    """Detect number of peaks in dissipation factor (simple positive height criterion)."""
    # Ensure non-negative threshold
    thr = float(max(0.0, 0.1 * float(np.max(df_values))))
    peaks, _ = find_peaks(df_values, height=thr)
    return int(peaks.size)

# --------------------
# Hilbert-based KK
# --------------------

def _kk_hilbert(omega: np.ndarray,
                eps_imag: np.ndarray,
                eps_inf: float,
                window: Optional[object] = None,
                pad_factor: int = 2) -> np.ndarray:
    """
    KK via FFT Hilbert on a uniform ω grid.
    Builds an odd extension of ε″ and uses scipy.signal.hilbert on the extended series.

    Parameters
    ----------
    omega : np.ndarray
        Uniform angular frequency samples (rad/s)
    eps_imag : np.ndarray
        ε″(ω) at those samples
    eps_inf : float
        ε∞
    window : Any accepted by scipy.signal.get_window, optional
        Taper to reduce wrap-around. We DO NOT divide by the window after transform.
    pad_factor : int
        Zero-padding factor for the extended signal to reduce circular artifacts.
    """
    n = omega.size
    if n < 4:
        raise ValueError("Need at least 4 points for Hilbert-based KK")

    x = np.asarray(eps_imag, dtype=float).copy()
    if window is not None:
        try:
            w = get_window(window, n)
            x *= w
        except Exception as e:
            raise ValueError(f"Invalid window spec {window!r}: {e}")

    # Odd extension across 0: [-x[::-1], 0, x]
    x_neg = -x[::-1]
    x_ext = np.concatenate([x_neg, [0.0], x])

    # Optional zero-padding at the end
    if pad_factor and pad_factor > 1:
        pad_len = (pad_factor - 1) * x_ext.size
        x_ext = np.pad(x_ext, (0, pad_len), mode='constant')

    # Hilbert transform
    h_ext = np.imag(hilbert(x_ext))

    # Extract the positive-ω part (skip the central zero)
    h_pos = h_ext[:(2 * n + 1)][n + 1:]  # shape (n,)
    return eps_inf + h_pos

def _kk_resample_hilbert(
    frequency: np.ndarray,
    eps_imag: np.ndarray,
    eps_inf: float,
    window: Optional[object],
    resample_points: Optional[int],
    pad_factor: int = 2
) -> np.ndarray:
    """
    Resample ε″(ω) to a uniform ω grid, apply Hilbert-based KK, and map back.

    Notes
    -----
    - This resamples in ω (linear), which is the correct variable for the KK Hilbert identity.
    """
    omega = 2.0 * np.pi * frequency
    num = int(resample_points or min(8192, 4 * len(frequency)))
    omu = np.linspace(float(omega.min()), float(omega.max()), num, dtype=float)

    # Interpolate ε″ onto uniform ω grid
    interp_eps = interp1d(omega, eps_imag, kind='cubic', fill_value='extrapolate', assume_sorted=True)
    eps_imag_u = interp_eps(omu)

    # KK on uniform grid
    dk_u = _kk_hilbert(omu, eps_imag_u, eps_inf, window=window, pad_factor=pad_factor)

    # Map back to original ω grid
    back = interp1d(omu, dk_u, kind='cubic', fill_value='extrapolate', assume_sorted=True)
    return back(omega)

# --------------------
# Public API
# --------------------

def validate_kramers_kronig(
    frequency: np.ndarray,
    dk: np.ndarray,
    df: np.ndarray,
    method: Literal['auto', 'hilbert', 'trapz'] = 'auto',
    eps_inf_method: Literal['mean', 'fit'] = 'fit',
    eps_inf: Optional[float] = None,
    tail_fraction: float = 0.1,
    min_tail_points: int = 3,
    window: Optional[object] = None,
    resample_points: Optional[int] = None,
    causality_threshold: float = 0.05,
    use_sskk: bool = True,
    anchor_index: Optional[int] = None
) -> Dict[str, Any]:
    """
    Validate experimental dielectric data using Kramers–Kronig relations.

    Parameters
    ----------
    frequency : np.ndarray
        Frequency array in Hz (strictly increasing, positive)
    dk : np.ndarray
        Real part of relative permittivity (ε′)
    df : np.ndarray
        Dissipation factor tanδ = ε″/ε′
    method : {'auto', 'hilbert', 'trapz'}
        'auto' selects Hilbert on uniform linear grids, else trapezoid (SSKK by default)
    eps_inf_method : {'mean', 'fit'}
        How to estimate ε∞ if not provided
    eps_inf : float, optional
        Explicit high-frequency permittivity value
    tail_fraction : float
        Fraction of highest-frequency data used for ε∞ estimation
    min_tail_points : int
        Minimum points for tail analysis
    window : Any accepted by scipy.signal.get_window, optional
        Taper applied before Hilbert; ignored for trapezoid
    resample_points : int, optional
        Points for ω-uniform resampling when using Hilbert on a non-uniform grid
    causality_threshold : float
        Threshold for pass/fail on mean relative error
    use_sskk : bool
        Use singly subtractive KK for trapezoid (recommended)
    anchor_index : int, optional
        Index of anchor frequency for SSKK; default is the median index

    Returns
    -------
    dict
        Results dict with keys:
        - dk_kk: KK-predicted ε′
        - mean_relative_error, median_relative_error, q90_relative_error
        - rmse
        - causality_status: 'PASS' or 'FAIL'
        - eps_inf_estimated
        - method_used: 'hilbert' or 'trapz'
        - method_detail: 'hilbert-uniform'|'hilbert-resample'|'trapz-sskk'|'trapz-pv'
        - num_peaks
        - is_uniform_grid: whether the frequency grid is uniform (linear)
        - anchor_index (when SSKK is used)
    """
    # Input validation
    frequency = np.asarray(frequency, dtype=float).reshape(-1)
    dk = np.asarray(dk, dtype=float).reshape(-1)
    df = np.asarray(df, dtype=float).reshape(-1)

    if frequency.size != dk.size or frequency.size != df.size:
        raise ValueError("Input arrays must have the same length")
    if frequency.size < 2:
        raise ValueError("At least 2 data points are required")
    if not np.all(np.diff(frequency) > 0):
        raise ValueError("Frequencies must be strictly increasing")
    if np.any(frequency <= 0):
        raise ValueError("Frequencies must be positive")
    if np.any(~np.isfinite(frequency)) or np.any(~np.isfinite(dk)) or np.any(~np.isfinite(df)):
        raise ValueError("Inputs contain non-finite values")

    # Convert to angular frequency and compute ε″ = ε′ * tanδ
    omega = 2.0 * np.pi * frequency
    eps_imag = dk * df

    # Estimate ε∞ if not provided
    if eps_inf is None:
        eps_inf = _estimate_eps_inf(frequency, dk, eps_inf_method, tail_fraction, min_tail_points)

    # Diagnostics
    num_peaks = _detect_peaks(df)
    is_uniform = _is_grid_uniform(frequency)

    # Select method
    if method == 'auto':
        actual_method = 'hilbert' if is_uniform else 'trapz'
        logger.debug(f"Auto-selected '{actual_method}' method based on linear grid uniformity")
    else:
        actual_method = method

    # Perform KK transform
    if actual_method == 'hilbert':
        if not is_uniform:
            logger.debug("Non-uniform grid detected for 'hilbert'; resampling to uniform ω")
            dk_kk = _kk_resample_hilbert(frequency, eps_imag, eps_inf, window, resample_points)
            method_detail = 'hilbert-resample'
        else:
            dk_kk = _kk_hilbert(omega, eps_imag, eps_inf, window)
            method_detail = 'hilbert-uniform'
    else:  # trapz
        if use_sskk:
            idx0 = int(anchor_index) if anchor_index is not None else (frequency.size // 2)
            dk_anchor = float(dk[idx0])
            omega_anchor = float(omega[idx0])
            dk_kk = _kk_trapz_sskk(omega, eps_imag, eps_inf, dk_anchor, omega_anchor)
            method_detail = 'trapz-sskk'
        else:
            dk_kk = _kk_trapz_numba(omega, eps_imag, eps_inf)
            method_detail = 'trapz-pv'

    # Metrics
    scale = float(np.median(np.abs(dk)))
    eps_scale = max(1e-12, 1e-6 * scale)
    rel_err = np.abs(dk_kk - dk) / (np.abs(dk) + eps_scale)
    mean_rel = float(np.mean(rel_err))
    median_rel = float(np.median(rel_err))
    q90_rel = float(np.quantile(rel_err, 0.90))
    rmse = float(np.sqrt(np.mean((dk_kk - dk) ** 2)))
    status = "PASS" if mean_rel <= causality_threshold else "FAIL"

    logger.info(f"KK Validation: {status} (Mean Rel Err: {mean_rel:.2%}, method={method_detail})")

    return {
        'dk_kk': dk_kk,
        'mean_relative_error': mean_rel,
        'median_relative_error': median_rel,
        'q90_relative_error': q90_rel,
        'rmse': rmse,
        'causality_status': status,
        'eps_inf_estimated': float(eps_inf),
        'method_used': actual_method,
        'method_detail': method_detail,
        'num_peaks': num_peaks,
        'is_uniform_grid': bool(is_uniform),
        'anchor_index': int(anchor_index) if anchor_index is not None else None,
    }

def _estimate_eps_inf(
    frequency: np.ndarray,
    dk: np.ndarray,
    method: str,
    tail_fraction: float,
    min_tail_points: int
) -> float:
    """Estimate high-frequency permittivity from the high-frequency tail of ε′."""
    N = len(frequency)
    n_tail = max(int(min_tail_points), int(tail_fraction * N))
    n_tail = min(n_tail, N)  # clamp

    tail_freq = frequency[-n_tail:]
    tail_dk = dk[-n_tail:]

    if method == 'fit':
        if tail_dk.size < 3:
            logger.warning(f"Tail size {tail_dk.size} < 3, falling back to 'mean' method")
            return float(np.mean(tail_dk))
        # Fit ε′ vs 1/f² (motivated by Debye/Lorentz high-frequency tail)
        x = 1.0 / (tail_freq * tail_freq)
        slope, intercept, *_ = linregress(x, tail_dk)
        return float(intercept)
    else:  # 'mean'
        return float(np.mean(tail_dk))

def kramers_kronig_from_dataframe(
    df: pd.DataFrame,
    freq_column: str = 'Frequency (GHz)',
    dk_column: str = 'Dk',
    df_column: str = 'Df',
    **kwargs
) -> Dict[str, Any]:
    """
    Convenience function to validate data from a pandas DataFrame.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame containing frequency and dielectric data
    freq_column : str
        Name of frequency column (assumed in GHz)
    dk_column : str
        Name of ε′ column
    df_column : str
        Name of tanδ column
    **kwargs
        Passed to validate_kramers_kronig

    Returns
    -------
    dict
        Validation results from validate_kramers_kronig
    """
    # Extract and validate columns
    for col in (freq_column, dk_column, df_column):
        if col not in df.columns:
            raise ValueError(f"Column '{col}' not found in DataFrame")

    # Convert to numpy arrays
    freq_ghz = pd.to_numeric(df[freq_column], errors='coerce').to_numpy()
    dk = pd.to_numeric(df[dk_column], errors='coerce').to_numpy()
    df_values = pd.to_numeric(df[df_column], errors='coerce').to_numpy()

    # Check for NaNs
    if np.any(np.isnan(freq_ghz)) or np.any(np.isnan(dk)) or np.any(np.isnan(df_values)):
        raise ValueError("DataFrame contains non-numeric or NaN values")

    # Convert frequency to Hz
    freq_hz = freq_ghz * 1e9
    return validate_kramers_kronig(freq_hz, dk, df_values, **kwargs)

class KramersKronigValidator:
    """
    Class-based interface for Kramers–Kronig validation.

    Provides a stateful interface (e.g., for Flask), delegating to the functional API.
    """

    def __init__(
        self,
        df: pd.DataFrame,
        method: Literal['auto', 'hilbert', 'trapz'] = 'auto',
        eps_inf_method: Literal['mean', 'fit'] = 'fit',
        eps_inf: Optional[float] = None,
        tail_fraction: float = 0.1,
        min_tail_points: int = 3,
        window: Optional[object] = None,
        resample_points: Optional[int] = None,
        use_sskk: bool = True,
        anchor_index: Optional[int] = None,
    ):
        """
        Initialize validator with DataFrame.

        Parameters
        ----------
        df : pd.DataFrame
            DataFrame with 'Frequency (GHz)', 'Dk', 'Df' columns
        method : {'auto', 'hilbert', 'trapz'}
            KK transform method
        eps_inf_method : {'mean', 'fit'}
            Method for estimating high-frequency permittivity
        eps_inf : float, optional
            Explicit high-frequency permittivity
        tail_fraction : float
            Fraction of data for eps_inf estimation
        min_tail_points : int
            Minimum points for tail analysis
        window : Any accepted by scipy.signal.get_window, optional
            Window function for Hilbert transform
        resample_points : int, optional
            Number of points for ω-uniform resampling (Hilbert on non-uniform grid)
        use_sskk : bool
            Whether to use singly subtractive KK for trapezoid
        anchor_index : int, optional
            Anchor index for SSKK (default: median index)
        """
        self.df = df
        self.method = method
        self.eps_inf_method = eps_inf_method
        self.explicit_eps_inf = eps_inf
        self.tail_fraction = tail_fraction
        self.min_tail_points = min_tail_points
        self.window = window
        self.resample_points = resample_points
        self.use_sskk = use_sskk
        self.anchor_index = anchor_index
        self.results: Dict[str, Any] = {}

        # Validate window parameter if provided
        if window is not None:
            try:
                _ = get_window(window, 16)
            except Exception as e:
                raise ValueError(f"Invalid window spec {window!r}: {e}")

    def validate(self, causality_threshold: float = 0.05) -> Dict[str, Any]:
        """
        Perform validation and return results.

        Parameters
        ----------
        causality_threshold : float, optional
            Threshold for causality pass/fail

        Returns
        -------
        dict
            Validation results
        """
        self.results = kramers_kronig_from_dataframe(
            self.df,
            method=self.method,
            eps_inf_method=self.eps_inf_method,
            eps_inf=self.explicit_eps_inf,
            tail_fraction=self.tail_fraction,
            min_tail_points=self.min_tail_points,
            window=self.window,
            resample_points=self.resample_points,
            causality_threshold=causality_threshold,
            use_sskk=self.use_sskk,
            anchor_index=self.anchor_index,
        )
        return self.results

    @property
    def is_causal(self) -> bool:
        """Check if data passes causality test."""
        if not self.results:
            raise RuntimeError("Must call validate() first")
        return self.results['causality_status'] == 'PASS'

    @property
    def relative_error(self) -> float:
        """Get mean relative error."""
        if not self.results:
            raise RuntimeError("Must call validate() first")
        return self.results['mean_relative_error']

    def get_diagnostics(self) -> Dict[str, Any]:
        """Get detailed diagnostic information."""
        if not self.results:
            self.validate()

        # Extract frequency info
        freq_ghz = pd.to_numeric(self.df['Frequency (GHz)'], errors='coerce').to_numpy()
        df_values = pd.to_numeric(self.df['Df'], errors='coerce').to_numpy()

        # Find frequency of maximum Df
        max_df_idx = int(np.argmax(df_values))

        return {
            'grid_uniform': self.results['is_uniform_grid'],
            'num_points': int(len(freq_ghz)),
            'freq_range_ghz': (float(freq_ghz.min()), float(freq_ghz.max())),
            'eps_inf': float(self.results['eps_inf_estimated']),
            'method_used': self.results['method_used'],
            'method_detail': self.results.get('method_detail', ''),
            'max_df_freq_ghz': float(freq_ghz[max_df_idx]),
            'num_peaks': int(self.results['num_peaks']),
            **self.results
        }

    def get_report(self) -> str:
        """Get formatted validation report."""
        if not self.results:
            return "Validation has not been run. Call .validate() first."

        report = (
            f"\n{' Kramers-Kronig Causality Report ':=^50}\n"
            f" ▸ Causality Status:      {self.results['causality_status']}\n"
            f" ▸ Mean Relative Error:   {self.results['mean_relative_error']:.2%}\n"
            f" ▸ Median Relative Error: {self.results.get('median_relative_error', float('nan')):.2%}\n"
            f" ▸ RMSE (Dk vs. Dk_KK):   {self.results['rmse']:.4f}\n"
            f"{'=' * 50}"
        )
        return report
