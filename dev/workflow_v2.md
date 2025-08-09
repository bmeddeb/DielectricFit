# DielectricFit — End‑to‑End Workflow (v2)
**Updated:** 2025-08-09  
**Stack:** Django backend · SQLite (dev) → PostgreSQL (future) · Optional task runner for long fits  
**Units:** Canonical internal units are **Hz**, **s**, **S/m** (UI may show GHz).

## Stage 0 — Environment & Tech Notes
- Django ORM models back all tables; JSON fields remain portable (TEXT in SQLite, JSONB in Postgres).  
- UUIDs are generated in the app for SQLite; native UUID in Postgres.  
- Generated columns (e.g., tanδ) are supported where available; otherwise computed at query time or maintained in save hooks.

## Stage 1 — Import & Validation
1. Read CSV; sniff columns: (f, Dk, Df) **or** (f, ε′, ε″).  
2. Detect frequency units (Hz/kHz/MHz/GHz) → convert to **Hz**.  
3. Dedupe and stable sort by frequency; enforce strictly increasing f for fitting.  
4. Persist dataset with: `input_schema`, `input_freq_unit`, `ingest_fingerprint (md5)`, `row_count`.  
5. Preview panel: min/max f (Hz + GHz), sample rows, and detected schema.

## Stage 2 — Preprocessing
- Outlier handling: delete, interpolate, replace; **undo/redo** stack.  
- Interpolation: linear, **PCHIP (monotone)**, cubic spline (with monotonicity guard for ε′).  
- Smoothing: Savitzky–Golay, moving average, Gaussian, median (configurable).  
- Conversions: if (Dk, Df) provided, derive ε′, ε″; if (ε′, ε″) provided, derive Dk, tanδ.  
- Persist **preprocessing_config** and its **hash**. Store preprocessed series in canonical units.

## Stage 3 — Analysis & Diagnostics
- Feature extraction: peak count and symmetry in ε″, loss peak f_peak, low/high‑f asymptotes, σ_dc cues.  
- **Kramers–Kronig** consistency check (finite‑band extrapolation strategy documented).  
- **Autosuggest scoring** = weighted blend of: KK RMSE, peak symmetry, quick coarse‑fit AIC/BIC for candidate models, σ_dc detect.  
- Persist `scoring_breakdown` and `autosuggest_top` (Top‑3 with rationale + confidence).

## Stage 4 — Model Configuration
- Select model (Debye, Cole–Cole, Cole–Davidson, HN, Multi‑pole Debye, Djordjević–Sarkar, Hybrid Debye–Lorentz).  
- Parameter UI generated from **model registry schema** with units, bounds, default **transform (log/linear)**, and constraints.  
- Supports **parameter ties** (shared ε∞, etc.) and autoscaled bounds around initial guesses.  
- Save/load **template configs** (e.g., FR‑4 presets).

## Stage 5 — Fitting
- Optimizers: least‑squares (Levenberg–Marquardt/Trust), optional global multi‑start.  
- **Robust losses**: linear, huber, soft_l1, cauchy, arctan (with `loss_scale`).  
- **Weighting**: frequency weighting (e.g., log‑spacing) and component weighting (ε′ vs ε″).  
- **Multistart**: group seeds by `multistart_group_id`, keep best by AIC (or BIC).  
- Persist convergence status, iterations, and runtime.

## Stage 6 — Validation & Comparison
- Metrics: RMSE, χ²_red, AIC/BIC, KK residuals.  
- Residual diagnostics: **Durbin–Watson**, runs test, Q–Q normality, lag‑1 autocorr.  
- Parameter CIs (bootstrap/profile) and **correlation matrix** with guidance (drop pole, fix ε∞, tighten bounds).  
- Compare fits across models/N‑poles with overlaid curves and a ranked table.

## Stage 7 — Reporting & Artifacts
- Report includes: dataset summary, preprocessing config, model equations, fitted params with CIs, stats, plots, KK check, and a **provenance block** (dataset checksum, preprocessing hash, model registry/version, software version, seed).  
- Artifacts: CSV (curves/residuals), JSON (fit result), NPZ (arrays), PNG/PDF (plots).

## Stage 8 — Persistence & Versioning
- All entities write through the ORM with created/updated timestamps.  
- Large arrays live in an **artifacts** table; small per‑point results go to `fitted_curves`.  
- Views: “best fit per multistart group” by AIC; comparison views for dashboard.

## Error Handling & Observability
- Input validation errors surface inline with actionable fixes.  
- Timeouts with graceful cancellation; partial results preserved.  
- Logging: dataset id, session id, seed, and timing for every fit; counters for retries.

## Security & Sharing
- Dataset ownership; read‑only **share links** for reports and plots (no editing).

## Roadmap Notes
- Post‑MVP: batch fitting orchestration, team sharing/permissions, scheduled pipelines.