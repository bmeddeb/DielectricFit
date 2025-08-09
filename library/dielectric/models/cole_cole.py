from __future__ import annotations

import numpy as np

from library.dielectric.model_registry import ModelSpec, ParameterSpec, register_model

"""
NOTE: Example evaluator
This Cole–Cole implementation is provided for registry wiring and demos.
It has not been validated for production use in this project.
"""


def cole_cole_evaluator(omega: np.ndarray, eps_inf: float, delta_eps: float, tau: float, alpha: float) -> np.ndarray:
    """Cole–Cole permittivity: ε(ω) = ε∞ + Δε / (1 + (iωτ)^{1-α})."""
    iw_tau = 1j * omega * tau
    denom = 1.0 + np.power(iw_tau, 1.0 - alpha)
    return eps_inf + (delta_eps / denom)


register_model(
    ModelSpec(
        name="Cole-Cole",
        parameters=[
            ParameterSpec("eps_inf", "", (1.0, 20.0), "linear"),
            ParameterSpec("delta_eps", "", (0.0, 20.0), "linear"),
            ParameterSpec("tau", "s", (1e-15, 1.0), "log"),
            ParameterSpec("alpha", "", (0.0, 1.0), "linear"),
        ],
        evaluator=cole_cole_evaluator,
        description="Cole–Cole dielectric model (symmetric broadening).",
    )
)
