from __future__ import annotations

import numpy as np

from library.dielectric.model_registry import ModelSpec, ParameterSpec, register_model

"""
NOTE: Example evaluator
This Debye(1) implementation is provided for registry wiring and demos.
It has not been validated for production use in this project.
"""


def debye_evaluator(omega: np.ndarray, eps_inf: float, delta_eps: float, tau: float) -> np.ndarray:
    """Single-pole Debye permittivity: ε(ω) = ε∞ + Δε / (1 + iωτ)."""
    iwt = 1j * omega * tau
    return eps_inf + (delta_eps / (1.0 + iwt))


register_model(
    ModelSpec(
        name="Debye(1)",
        parameters=[
            ParameterSpec("eps_inf", "", (1.0, 20.0), "linear"),
            ParameterSpec("delta_eps", "", (0.0, 20.0), "linear"),
            ParameterSpec("tau", "s", (1e-15, 1.0), "log"),
        ],
        evaluator=debye_evaluator,
        description="Single-pole Debye dielectric model.",
    )
)
