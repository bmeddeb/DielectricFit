"""Signal processing algorithms: smoothing and interpolation.

This package hosts implementations used by the analysis pipeline.
"""

from .smoothing import moving_average, gaussian_smooth, median_smooth, savitzky_golay
from .interpolation import linear_interpolate, pchip_interpolate

__all__ = [
    "moving_average",
    "gaussian_smooth",
    "median_smooth",
    "savitzky_golay",
    "linear_interpolate",
    "pchip_interpolate",
]

