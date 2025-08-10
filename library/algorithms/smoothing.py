from __future__ import annotations

import logging
import warnings
from typing import Iterable, Literal

import numpy as np
from numpy.typing import ArrayLike, NDArray
import scipy.signal
import scipy.ndimage

logger = logging.getLogger(__name__)


def moving_average(
    y: ArrayLike, 
    window: int = 5,
    mode: Literal['reflect', 'constant', 'nearest', 'mirror', 'wrap'] = 'reflect'
) -> NDArray[np.float64]:
    """Apply moving average smoothing using uniform window.
    
    Args:
        y: Input signal values
        window: Window size (will be made odd if even)
        mode: Boundary handling mode for convolution
        
    Returns:
        Smoothed signal array
        
    Raises:
        ValueError: If window size is invalid or y is empty
    """
    y = np.asarray(y, dtype=float)
    
    if y.size == 0:
        raise ValueError("Input array is empty")
    
    window = max(1, int(window))
    if window % 2 == 0:
        window += 1
        
    if window == 1:
        return y.copy()
    
    if window > y.size:
        logger.warning(f"Window size {window} larger than signal length {y.size}, reducing window")
        window = y.size if y.size % 2 == 1 else y.size - 1
    
    # Use scipy's uniform filter for efficiency and proper boundary handling
    return scipy.ndimage.uniform_filter1d(y, size=window, mode=mode)


def gaussian_smooth(
    y: ArrayLike, 
    sigma: float = 2.0,
    truncate: float = 4.0,
    mode: Literal['reflect', 'constant', 'nearest', 'mirror', 'wrap'] = 'reflect'
) -> NDArray[np.float64]:
    """Apply Gaussian smoothing filter.
    
    Args:
        y: Input signal values
        sigma: Standard deviation of Gaussian kernel (in samples)
        truncate: Truncate filter at this many standard deviations
        mode: Boundary handling mode
        
    Returns:
        Smoothed signal array
        
    Raises:
        ValueError: If sigma is non-positive or y is empty
    """
    y = np.asarray(y, dtype=float)
    
    if y.size == 0:
        raise ValueError("Input array is empty")
    
    if sigma <= 0:
        raise ValueError(f"Sigma must be positive, got {sigma}")
    
    # Use scipy's optimized Gaussian filter
    return scipy.ndimage.gaussian_filter1d(y, sigma=sigma, truncate=truncate, mode=mode)


def median_smooth(
    y: ArrayLike, 
    window: int = 5,
    mode: Literal['reflect', 'constant', 'nearest', 'mirror', 'wrap'] = 'reflect'
) -> NDArray[np.float64]:
    """Apply median filter for robust smoothing against outliers.
    
    Args:
        y: Input signal values
        window: Window size (will be made odd if even)
        mode: Boundary handling mode
        
    Returns:
        Smoothed signal array
        
    Raises:
        ValueError: If window size is invalid or y is empty
    """
    y = np.asarray(y, dtype=float)
    
    if y.size == 0:
        raise ValueError("Input array is empty")
    
    window = max(1, int(window))
    if window % 2 == 0:
        window += 1
        
    if window == 1:
        return y.copy()
    
    if window > y.size:
        logger.warning(f"Window size {window} larger than signal length {y.size}, reducing window")
        window = y.size if y.size % 2 == 1 else y.size - 1
    
    # Use scipy's ndimage median filter which supports boundary modes
    return scipy.ndimage.median_filter(y, size=window, mode=mode)


def savitzky_golay(
    y: Iterable[float], 
    window: int = 7, 
    polyorder: int = 3,
    deriv: int = 0,
    delta: float = 1.0,
    mode: Literal['mirror', 'constant', 'nearest', 'interp', 'wrap'] = 'mirror'
) -> np.ndarray:
    """Apply Savitzky-Golay filter for smoothing while preserving features.
    
    This filter fits a polynomial to each window of data and evaluates
    the polynomial at the center point. It's particularly good at preserving
    peaks and other features while removing noise.
    
    Args:
        y: Input signal values
        window: Window length (must be odd and > polyorder)
        polyorder: Order of polynomial to fit
        deriv: Order of derivative to compute (0 = just smoothing)
        delta: Sample spacing for derivative calculation
        mode: Boundary handling mode
        
    Returns:
        Smoothed (or differentiated) signal array
        
    Raises:
        ValueError: If parameters are invalid
    """
    y = np.asarray(y, dtype=float)
    
    if y.size == 0:
        raise ValueError("Input array is empty")
    
    window = max(3, int(window))
    if window % 2 == 0:
        window += 1
        
    polyorder = max(0, int(polyorder))
    
    if polyorder >= window:
        polyorder = window - 1
        logger.warning(f"Polyorder {polyorder} >= window {window}, reducing to {polyorder}")
    
    if window > y.size:
        # Adjust window to be at most the size of the signal
        window = y.size if y.size % 2 == 1 else y.size - 1
        if polyorder >= window:
            polyorder = max(0, window - 1)
        logger.warning(f"Window size adjusted to {window} with polyorder {polyorder}")
    
    # Use scipy's Savitzky-Golay filter
    return scipy.signal.savgol_filter(
        y, window_length=window, polyorder=polyorder, 
        deriv=deriv, delta=delta, mode=mode
    )


def lowess_smooth(
    x: Iterable[float],
    y: Iterable[float], 
    frac: float = 0.3,
    it: int = 3,
    delta: float = 0.0
) -> tuple[np.ndarray, np.ndarray]:
    """Apply LOWESS (Locally Weighted Scatterplot Smoothing).
    
    This is a non-parametric regression method that combines multiple
    regression models in a k-nearest-neighbor-based meta-model.
    
    Args:
        x: Independent variable values (must be sorted)
        y: Dependent variable values
        frac: Fraction of data points to use for each local regression
        it: Number of robustifying iterations
        delta: Distance within which to use linear interpolation
        
    Returns:
        Tuple of (x_values, smoothed_y_values)
        
    Raises:
        ValueError: If inputs are invalid
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)

    if x.size != y.size:
        raise ValueError(f"x and y must have same size, got {x.size} and {y.size}")
    if x.size == 0:
        raise ValueError("Input arrays are empty")
    if not (0 < frac <= 1):
        raise ValueError(f"frac must be in (0, 1], got {frac}")
    if not np.all(np.diff(x) >= 0):
        raise ValueError("x values must be sorted in ascending order")

    try:
        # Real LOWESS (optional dependency)
        from statsmodels.nonparametric.smoothers_lowess import lowess as _lowess
        # return_sorted=False keeps original x order (already sorted per check)
        y_smooth = _lowess(y, x, frac=frac, it=it, delta=delta, return_sorted=False)
    except Exception:
        # Fallback: Savitzky–Golay approximation
        from scipy.signal import savgol_filter
        window = max(5, int(frac * x.size))
        if window % 2 == 0:
            window += 1
        window = min(window, x.size if x.size % 2 == 1 else x.size - 1)
        polyorder = min(3, window - 1)
        y_smooth = savgol_filter(y, window, polyorder)

    return x, y_smooth


def butterworth_lowpass(
    y: Iterable[float],
    cutoff_freq: float,
    sampling_freq: float,
    order: int = 5
) -> np.ndarray:
    """Apply Butterworth low-pass filter for frequency-domain smoothing.
    
    Args:
        y: Input signal values
        cutoff_freq: Cutoff frequency in Hz
        sampling_freq: Sampling frequency in Hz
        order: Filter order (higher = sharper cutoff)
        
    Returns:
        Filtered signal array
        
    Raises:
        ValueError: If parameters are invalid
    """
    y = np.asarray(y, dtype=float)
    
    if y.size == 0:
        raise ValueError("Input array is empty")
    
    if order < 1:
        raise ValueError(f"Order must be >= 1, got {order}")
    
    if cutoff_freq <= 0:
        raise ValueError(f"Cutoff frequency must be positive, got {cutoff_freq}")
    
    if sampling_freq <= 0:
        raise ValueError(f"Sampling frequency must be positive, got {sampling_freq}")
    
    nyquist = 0.5 * sampling_freq
    if cutoff_freq >= nyquist:
        raise ValueError(f"Cutoff frequency {cutoff_freq} must be < Nyquist {nyquist}")
    
    # Design Butterworth filter using SOS (second-order sections) for numerical stability
    normal_cutoff = cutoff_freq / nyquist
    sos = scipy.signal.butter(order, normal_cutoff, btype='low', output='sos')
    
    try:
        # Use sosfiltfilt for zero-phase filtering with better numerical stability
        return scipy.signal.sosfiltfilt(sos, y)
    except ValueError as e:
        # Likely too short for padding; degrade gracefully to causal filtering
        logger.warning(f"sosfiltfilt failed, falling back to sosfilt due to: {e}")
        return scipy.signal.sosfilt(sos, y)


def wiener_smooth(
    y: Iterable[float],
    noise: float | None = None,
    mysize: int | None = None
) -> np.ndarray:
    """Apply Wiener filter for optimal noise reduction.
    
    The Wiener filter minimizes the mean square error between the
    estimated and true signal.
    
    Args:
        y: Input signal values
        noise: Noise power (if None, estimated from signal)
        mysize: Size of local neighborhood for filter
        
    Returns:
        Filtered signal array
    """
    y = np.asarray(y, dtype=float)
    
    if y.size == 0:
        raise ValueError("Input array is empty")
    
    # Apply Wiener filter
    return scipy.signal.wiener(y, mysize=mysize, noise=noise)


def exponential_smooth(
    y: Iterable[float],
    alpha: float = 0.3,
    adjust: bool = True,
    ignore_na: bool = False
) -> np.ndarray:
    """Apply exponential smoothing (exponentially weighted moving average).
    
    Args:
        y: Input signal values
        alpha: Smoothing factor between 0 and 1
        adjust: Adjust weights to account for imbalance in beginning
        ignore_na: Ignore NaN values
        
    Returns:
        Smoothed signal array
        
    Raises:
        ValueError: If alpha is not in [0, 1]
    """
    y = np.asarray(y, dtype=float)
    
    if y.size == 0:
        raise ValueError("Input array is empty")
    
    if not 0 <= alpha <= 1:
        raise ValueError(f"Alpha must be in [0, 1], got {alpha}")
    
    # Handle alpha == 0 explicitly to avoid division by zero
    if alpha == 0:
        if ignore_na:
            # forward-fill the last non-NaN (NaNs leading the series remain NaN)
            result = np.empty_like(y)
            seen = False
            last = np.nan
            for i, v in enumerate(y):
                if not np.isnan(v):
                    last = v
                    seen = True
                result[i] = last if seen else np.nan
            return result
        # No decay; everything stays at the first value
        return np.full_like(y, y[0])
    
    if ignore_na:
        mask = ~np.isnan(y)
        if not mask.any():
            return np.full_like(y, np.nan)
    else:
        mask = np.ones(y.size, dtype=bool)
        if np.isnan(y).any():
            logger.warning("NaN values present in signal, results may be NaN")
    
    result = np.empty_like(y)
    
    if adjust:
        # Adjusted EWMA
        weighted_sum = 0.0
        weight_sum = 0.0
        
        for i in range(y.size):
            if mask[i]:
                weighted_sum = weighted_sum * (1 - alpha) + y[i] * alpha
                weight_sum = weight_sum * (1 - alpha) + alpha
                result[i] = weighted_sum / weight_sum
            else:
                result[i] = np.nan if i == 0 else result[i-1]
    else:
        # Simple EWMA
        result[0] = y[0] if mask[0] else np.nan
        
        for i in range(1, y.size):
            if mask[i]:
                result[i] = alpha * y[i] + (1 - alpha) * result[i-1]
            else:
                result[i] = result[i-1]
    
    return result


def spline_smooth(
    x: Iterable[float],
    y: Iterable[float],
    s: float | None = None,
    k: int = 3
) -> tuple[np.ndarray, np.ndarray]:
    """Apply smoothing spline interpolation.
    
    Args:
        x: Independent variable values (must be strictly increasing)
        y: Dependent variable values
        s: Smoothing factor (0 = interpolation, higher = more smoothing)
           If None, s = len(x)
        k: Degree of spline (1-5, default 3 for cubic)
        
    Returns:
        Tuple of (x_values, smoothed_y_values)
    """
    from scipy.interpolate import UnivariateSpline
    
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    
    if x.size != y.size:
        raise ValueError(f"x and y must have same size, got {x.size} and {y.size}")
    
    if x.size == 0:
        raise ValueError("Input arrays are empty")
    
    # Check if x is strictly increasing (no duplicates)
    if not np.all(np.diff(x) > 0):
        raise ValueError("x values must be strictly increasing (no duplicates)")
    
    # Clamp k to valid range and available data
    k = int(k)
    if k < 1 or k > 5:
        warnings.warn(f"k={k} out of [1,5], clipping to valid range", UserWarning)
        k = min(5, max(1, k))
    k = min(k, x.size - 1)
    
    # Create spline
    if s is None:
        s = x.size  # Default smoothing
    
    spline = UnivariateSpline(x, y, s=s, k=k)
    
    return x, spline(x)