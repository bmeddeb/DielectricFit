from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Tuple


"""
Model registry scaffolding

This registry and the bundled evaluators are examples/placeholders to shape the
API. They are NOT yet validated against reference datasets. For production,
ensure evaluators, units, and parameter transforms are verified and covered by
tests, and consider using lmfit/scipy for parameter handling and fitting.
"""

@dataclass(frozen=True)
class ParameterSpec:
    name: str
    units: str
    bounds: Tuple[float, float]
    transform: str  # 'linear' | 'log'
    fixed: bool = False


@dataclass(frozen=True)
class ModelSpec:
    name: str
    parameters: List[ParameterSpec]
    evaluator: Callable[..., complex]
    description: str


REGISTRY: Dict[str, ModelSpec] = {}


def register_model(spec: ModelSpec) -> None:
    REGISTRY[spec.name] = spec


def get_model(name: str) -> ModelSpec:
    return REGISTRY[name]
