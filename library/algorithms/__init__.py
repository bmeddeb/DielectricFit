"""Signal processing algorithms: smoothing, interpolation, and Kramers-Kronig validation.

This package hosts implementations used by the analysis pipeline.
"""

from .smoothing import moving_average, gaussian_smooth, median_smooth, savitzky_golay
from .interpolation import linear_interpolate, pchip_interpolate
from .kramers_kronig import (
    validate_kramers_kronig,
    kramers_kronig_from_dataframe,
    KramersKronigValidator
)

__all__ = [
    "moving_average",
    "gaussian_smooth",
    "median_smooth",
    "savitzky_golay",
    "linear_interpolate",
    "pchip_interpolate",
    "validate_kramers_kronig",
    "kramers_kronig_from_dataframe",
    "KramersKronigValidator",
]

