# Library App — Status and Roadmap

This app hosts the dielectric model registry and basic signal‑processing utilities
(smoothing/interpolation) used by the analysis pipeline.

Important: The current algorithms are NOT production‑ready. They are lightweight placeholders to keep the UI and pipeline wiring functional until we integrate scientific libraries.

- Smoothing: moving average, Gaussian, median, and a minimal Savitzky–Golay implementation.
  - Planned replacement: `scipy.signal.savgol_filter` and related robust filters.
- Interpolation: linear and a PCHIP placeholder that currently falls back to linear.
  - Planned replacement: `scipy.interpolate.PchipInterpolator` (monotone), splines.
- Fitting/optimization: presently not wired to a full optimizer from this app.
  - Planned libraries: `lmfit` (preferred) and `scipy.optimize.least_squares` with robust losses.
- Models: Debye(1) and Cole–Cole evaluators are included as examples for wiring and registry shape; validation against reference datasets is pending.

Do not rely on the numerical accuracy or performance of the placeholder implementations for production.

## Next Steps
- Add SciPy and lmfit as dependencies; swap in tested implementations.
- Expand the model registry (multi‑Debye, Djordjević–Sarkar, Cole–Davidson, HN) with unit tests.
- Provide benchmarks and verification notebooks comparing against reference solvers.

