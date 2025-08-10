"""
Kramers-Kronig validation and causality checking for dielectric data.

This module provides tools for validating experimental dielectric data using 
Kramers-Kronig relations, which enforce causality constraints on the complex 
permittivity.
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, Literal, Tuple
from scipy.signal import hilbert, get_window, find_peaks
from scipy.interpolate import interp1d
from scipy.stats import linregress
from functools import lru_cache

# Optional Numba acceleration
try:
    from numba import njit, prange
    NUMBA_AVAILABLE = True
except ImportError:
    NUMBA_AVAILABLE = False

logger = logging.getLogger(__name__)


if NUMBA_AVAILABLE:
    @njit(parallel=True, fastmath=True)
    def _kk_trapz_numba(omega: np.ndarray, eps_imag: np.ndarray, eps_inf: float) -> np.ndarray:
        """
        Numba-accelerated trapezoidal Kramers-Kronig on non-uniform grids.
        
        Parameters
        ----------
        omega : np.ndarray
            Angular frequency array (rad/s)
        eps_imag : np.ndarray
            Imaginary part of permittivity (ε″)
        eps_inf : float
            High-frequency permittivity limit
            
        Returns
        -------
        np.ndarray
            Calculated real part (ε′) from KK relations
        """
        n = omega.size
        dk_kk = np.empty(n, dtype=np.float64)
        for i in prange(n):
            w_i = omega[i]
            integral = 0.0
            for j in range(n - 1):
                # Skip the two intervals adjacent to the singularity
                if j == i or j + 1 == i:
                    continue
                wj, wj1 = omega[j], omega[j + 1]
                # Integrand for Kramers-Kronig
                fj = (wj * eps_imag[j]) / (wj ** 2 - w_i ** 2)
                fj1 = (wj1 * eps_imag[j + 1]) / (wj1 ** 2 - w_i ** 2)
                # Standard trapezoidal rule
                integral += 0.5 * (fj + fj1) * (wj1 - wj)
            dk_kk[i] = eps_inf + (2.0 / np.pi) * integral
        return dk_kk
else:
    def _kk_trapz_numba(omega: np.ndarray, eps_imag: np.ndarray, eps_inf: float) -> np.ndarray:
        """
        Pure-Python trapezoidal integration fallback.
        """
        n = omega.size
        dk_kk = np.empty(n, dtype=float)
        for i in range(n):
            w_i = omega[i]
            integral = 0.0
            for j in range(n - 1):
                if j == i or j + 1 == i:
                    continue
                wj, wj1 = omega[j], omega[j + 1]
                fj = (wj * eps_imag[j]) / (wj ** 2 - w_i ** 2)
                fj1 = (wj1 * eps_imag[j + 1]) / (wj1 ** 2 - w_i ** 2)
                integral += 0.5 * (fj + fj1) * (wj1 - wj)
            dk_kk[i] = eps_inf + (2.0 / np.pi) * integral
        return dk_kk


def validate_kramers_kronig(
    frequency: np.ndarray,
    dk: np.ndarray,
    df: np.ndarray,
    method: Literal['auto', 'hilbert', 'trapz'] = 'auto',
    eps_inf_method: Literal['mean', 'fit'] = 'fit',
    eps_inf: Optional[float] = None,
    tail_fraction: float = 0.1,
    min_tail_points: int = 3,
    window: Optional[str] = None,
    resample_points: Optional[int] = None,
    causality_threshold: float = 0.05
) -> Dict[str, Any]:
    """
    Validate experimental dielectric data using Kramers-Kronig relations.
    
    Parameters
    ----------
    frequency : np.ndarray
        Frequency array in Hz
    dk : np.ndarray
        Real part of relative permittivity (Dk)
    df : np.ndarray
        Dissipation factor (Df or tan δ)
    method : {'auto', 'hilbert', 'trapz'}, optional
        KK transform method. 'auto' selects based on grid uniformity
    eps_inf_method : {'mean', 'fit'}, optional
        Method for estimating high-frequency permittivity
    eps_inf : float, optional
        Explicit high-frequency permittivity value
    tail_fraction : float, optional
        Fraction of data to use for eps_inf estimation
    min_tail_points : int, optional
        Minimum points for tail analysis
    window : str, optional
        Window function for Hilbert transform
    resample_points : int, optional
        Number of points for resampling
    causality_threshold : float, optional
        Threshold for causality pass/fail (default 5%)
        
    Returns
    -------
    dict
        Validation results including:
        - dk_kk: KK-predicted Dk values
        - mean_relative_error: Average relative error
        - rmse: Root mean square error
        - causality_status: 'PASS' or 'FAIL'
        - eps_inf_estimated: Estimated high-frequency permittivity
        - method_used: Actual method used
        - num_peaks: Number of peaks detected in Df
    """
    # Input validation
    if len(frequency) != len(dk) or len(frequency) != len(df):
        raise ValueError("Input arrays must have the same length")
    
    if len(frequency) < 2:
        raise ValueError("At least 2 data points are required")
    
    if not np.all(np.diff(frequency) > 0):
        raise ValueError("Frequencies must be strictly increasing")
    
    if np.any(frequency < 0):
        raise ValueError("Negative frequencies detected")
    
    if np.any(np.isnan(frequency)) or np.any(np.isnan(dk)) or np.any(np.isnan(df)):
        raise ValueError("Input contains NaN values")
    
    # Convert frequency to angular frequency
    omega = 2 * np.pi * frequency
    
    # Estimate eps_inf if not provided
    if eps_inf is None:
        eps_inf = _estimate_eps_inf(
            frequency, dk, eps_inf_method, 
            tail_fraction, min_tail_points
        )
    
    # Detect number of peaks
    num_peaks = _detect_peaks(df)
    
    # Check grid uniformity
    is_uniform = _is_grid_uniform(frequency)
    
    # Select method
    if method == 'auto':
        actual_method = 'hilbert' if is_uniform else 'trapz'
        logger.debug(f"Auto-selected '{actual_method}' method based on grid uniformity")
    else:
        actual_method = method
    
    # Perform KK transform
    if actual_method == 'hilbert':
        if not is_uniform:
            logger.debug("Non-uniform grid detected for 'hilbert' method; resampling")
            dk_kk = _kk_resample_hilbert(
                frequency, df, eps_inf, window, resample_points
            )
        else:
            dk_kk = _kk_hilbert(df, eps_inf, window)
    else:  # trapz
        dk_kk = _kk_trapz_numba(omega, df, eps_inf)
    
    # Calculate metrics
    eps = 1e-9
    rel_err = np.abs(dk_kk - dk) / (np.abs(dk) + eps)
    mean_rel = float(np.mean(rel_err))
    rmse = float(np.sqrt(np.mean((dk_kk - dk) ** 2)))
    status = "PASS" if mean_rel <= causality_threshold else "FAIL"
    
    logger.info(f"KK Validation: {status} (Mean Rel Err: {mean_rel:.2%})")
    
    return {
        'dk_kk': dk_kk,
        'mean_relative_error': mean_rel,
        'rmse': rmse,
        'causality_status': status,
        'eps_inf_estimated': eps_inf,
        'method_used': actual_method,
        'num_peaks': num_peaks,
        'is_uniform_grid': is_uniform
    }


def _estimate_eps_inf(
    frequency: np.ndarray,
    dk: np.ndarray,
    method: str,
    tail_fraction: float,
    min_tail_points: int
) -> float:
    """Estimate high-frequency permittivity from tail of Dk."""
    N = len(frequency)
    n_tail = max(min_tail_points, int(tail_fraction * N))
    
    tail_freq = frequency[-n_tail:]
    tail_dk = dk[-n_tail:]
    
    if method == 'fit':
        if len(tail_dk) < 3:
            logger.warning(
                f"Tail size {len(tail_dk)} < 3, falling back to 'mean' method"
            )
            return float(np.mean(tail_dk))
        
        # Fit Dk vs 1/f^2 (physically motivated)
        slope, intercept, *_ = linregress(1 / tail_freq ** 2, tail_dk)
        return float(intercept)
    else:  # mean
        return float(np.mean(tail_dk))


def _is_grid_uniform(frequency: np.ndarray, rtol: float = 1e-5, atol: float = 1e-8) -> bool:
    """Check if frequency grid is uniformly spaced."""
    diffs = np.diff(frequency)
    return np.allclose(diffs, diffs[0], rtol=rtol, atol=atol)


def _detect_peaks(df: np.ndarray) -> int:
    """Detect number of peaks in dissipation factor."""
    # Use 10% of maximum as minimum height threshold
    peaks, _ = find_peaks(df, height=0.1 * np.max(df))
    return len(peaks)


def _kk_hilbert(df: np.ndarray, eps_inf: float, window: Optional[str] = None) -> np.ndarray:
    """Apply Hilbert transform for uniform grids."""
    data = df.copy()
    
    if window:
        w = get_window(window, data.size)
        data = data * w
        # Add small epsilon to avoid division by zero
        return eps_inf - np.imag(hilbert(data)) / (w + 1e-12)
    
    return eps_inf - np.imag(hilbert(data))


def _kk_resample_hilbert(
    frequency: np.ndarray,
    df: np.ndarray,
    eps_inf: float,
    window: Optional[str],
    resample_points: Optional[int]
) -> np.ndarray:
    """Resample to uniform grid and apply Hilbert transform."""
    num = resample_points or min(4096, 4 * len(frequency))
    freq_uniform = np.linspace(frequency.min(), frequency.max(), num)
    
    # Interpolate Df to uniform grid
    interp_df = interp1d(frequency, df, kind='cubic', fill_value='extrapolate')
    df_uniform = interp_df(freq_uniform)
    
    # Apply Hilbert transform on uniform grid
    if window:
        w = get_window(window, num)
        df_uniform = df_uniform * w
        dk_uniform = eps_inf - np.imag(hilbert(df_uniform)) / (w + 1e-12)
    else:
        dk_uniform = eps_inf - np.imag(hilbert(df_uniform))
    
    # Interpolate back to original grid
    interp_back = interp1d(freq_uniform, dk_uniform, kind='cubic', fill_value='extrapolate')
    return interp_back(frequency)


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
    freq_column : str, optional
        Name of frequency column (assumed in GHz)
    dk_column : str, optional
        Name of Dk column
    df_column : str, optional
        Name of Df column
    **kwargs
        Additional arguments passed to validate_kramers_kronig
        
    Returns
    -------
    dict
        Validation results from validate_kramers_kronig
    """
    # Extract and validate columns
    if freq_column not in df.columns:
        raise ValueError(f"Column '{freq_column}' not found in DataFrame")
    if dk_column not in df.columns:
        raise ValueError(f"Column '{dk_column}' not found in DataFrame")
    if df_column not in df.columns:
        raise ValueError(f"Column '{df_column}' not found in DataFrame")
    
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
    Class-based interface for Kramers-Kronig validation.
    
    This provides a stateful interface compatible with the Flask implementation,
    while internally using the functional API.
    """
    
    def __init__(
        self,
        df: pd.DataFrame,
        method: Literal['auto', 'hilbert', 'trapz'] = 'auto',
        eps_inf_method: Literal['mean', 'fit'] = 'fit',
        eps_inf: Optional[float] = None,
        tail_fraction: float = 0.1,
        min_tail_points: int = 3,
        window: Optional[str] = None,
        resample_points: Optional[int] = None
    ):
        """
        Initialize validator with DataFrame.
        
        Parameters
        ----------
        df : pd.DataFrame
            DataFrame with 'Frequency (GHz)', 'Dk', 'Df' columns
        method : {'auto', 'hilbert', 'trapz'}, optional
            KK transform method
        eps_inf_method : {'mean', 'fit'}, optional
            Method for estimating high-frequency permittivity
        eps_inf : float, optional
            Explicit high-frequency permittivity
        tail_fraction : float, optional
            Fraction of data for eps_inf estimation
        min_tail_points : int, optional
            Minimum points for tail analysis
        window : str, optional
            Window function for Hilbert transform
        resample_points : int, optional
            Number of points for resampling
        """
        self.df = df
        self.method = method
        self.eps_inf_method = eps_inf_method
        self.explicit_eps_inf = eps_inf
        self.tail_fraction = tail_fraction
        self.min_tail_points = min_tail_points
        self.window = window
        self.resample_points = resample_points
        self.results = {}
        
        # Validate window parameter
        if window is not None:
            valid_windows = ['hamming', 'hann', 'blackman', 'bartlett', 'kaiser', 'tukey']
            if window not in valid_windows:
                raise ValueError(f"window must be one of {valid_windows} or None")
    
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
            causality_threshold=causality_threshold
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
        max_df_idx = np.argmax(df_values)
        
        return {
            'grid_uniform': self.results['is_uniform_grid'],
            'num_points': len(freq_ghz),
            'freq_range_ghz': (float(freq_ghz.min()), float(freq_ghz.max())),
            'eps_inf': self.results['eps_inf_estimated'],
            'method_used': self.results['method_used'],
            'max_df_freq_ghz': float(freq_ghz[max_df_idx]),
            'num_peaks': self.results['num_peaks'],
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
            f" ▸ RMSE (Dk vs. Dk_KK):   {self.results['rmse']:.4f}\n"
            f"{'=' * 50}"
        )
        return report