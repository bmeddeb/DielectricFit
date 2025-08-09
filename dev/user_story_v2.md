# DielectricFit — User Stories & Acceptance Criteria (v2)
**Updated:** 2025-08-09  
**Tech Stack:** Django (backend), SQLite (dev), PostgreSQL (future)  
**Canonical Units:** Frequency = **Hz** (UI may display GHz); Time = **s**; Conductivity = **S/m**

## Personas
- **Modeler (You)** — uploads dielectric spectra, selects models, tunes parameters, validates fits, exports reports.
- **Developer (Also You)** — maintains model registry, adds fitting strategies, ensures reproducibility and data integrity.

## Global Principles
- Accept **either** input schema at ingest: (f, Dk, Df) **or** (f, ε′, ε″). Internally normalize to **Hz** and store **both** Dk/Df and ε′/ε″ when determinable.
- Reproducibility: every stage persists configs, hashes, and versions (dataset fingerprint, preprocessing config hash, model registry version).
- v1 features include **robust losses** and **multistart**. Batch fitting comes later.

---

## User Stories

### 1) Import & Validate
**As a user**, I can upload CSV files with either (f, Dk, Df) or (f, ε′, ε″) and mixed units (Hz/kHz/MHz/GHz), and the system will auto-detect units, **convert to Hz**, dedupe, and stably sort by frequency.

**Acceptance**  
- **Given** a CSV in GHz with (Dk, Df)  
  **When** I upload it  
  **Then** I see a summary (row count, f_min/f_max, unit detected, dataset fingerprint) and a normalized preview in Hz.

**Notes**: Store `input_schema`, `input_freq_unit`, `ingest_fingerprint`, and `row_count` on the dataset.

---

### 2) Preprocess
**As a user**, I can remove/restore outliers, apply interpolation (linear, PCHIP, cubic) with **monotonicity guards** for ε′, and apply smoothing (Savitzky–Golay, moving average, Gaussian, median).

**Acceptance**  
- **Given** a dataset  
  **When** I choose PCHIP interpolation and median filter  
  **Then** the derived series (ε′, ε″, tanδ) update and a **preprocessing config hash** is saved for reproducibility.

---

### 3) Analyze & Autosuggest
**As a user**, I see an **autosuggested short list** of models with a score and rationale based on: KK RMSE, peak count/symmetry, quick coarse-fit AIC/BIC, and σ_dc detection.

**Acceptance**  
- **Given** preprocessed data  
  **When** I run analysis  
  **Then** I get Top-3 models with (score, confidence, rationale) and the underlying **scoring breakdown** is persisted.

---

### 4) Configure Model
**As a user**, I can choose a model and configure parameters with: bounds, **log/linear transforms**, ties (shared parameters), and **autoscaled** bounds from initial estimates. I can save and reuse **template configs** (e.g., “FR-4 low-loss”).

**Acceptance**  
- **Given** a Cole–Cole model  
  **When** I tie ε∞ across terms and set τ in log-space with Δε ≥ 0  
  **Then** validation passes and the UI prevents impossible configs.

---

### 5) Fit (Robust + Multistart)
**As a user**, I can run fits with robust loss (linear, huber, soft_l1, cauchy, arctan), frequency/component weighting, **multistart** seeds, and early stopping.

**Acceptance**  
- **Given** a model config  
  **When** I run a 10-seed multistart with soft_l1 loss  
  **Then** I see the best run by AIC, all seeds summarized, and the convergence reason recorded.

---

### 6) Validate & Compare
**As a user**, I can inspect residual diagnostics (RMSE, χ²_red, AIC/BIC, **Durbin–Watson**, runs test, Q–Q normality), parameter CIs, and correlation warnings with guidance (“try N−1 poles”, “fix ε∞”).

**Acceptance**  
- **Given** two completed fits  
  **When** I open Compare  
  **Then** I see overlaid curves (ε′, ε″, Dk, tanδ), residual plots, a stats table, and a computed winner (AIC default).

---

### 7) Report & Export
**As a user**, I can export a PDF/Markdown report with: provenance block (dataset checksum, preprocessing hash, model registry/version, software version), parameters with CIs, fit stats, charts, and equations. I can also export CSVs for fitted curves and residuals.

**Acceptance**  
- **Given** a successful fit  
  **When** I export  
  **Then** the report embeds figures and a machine-readable JSON/NPZ artifact is attached for reproducibility.

---

### 8) Save/Restore Sessions
**As a user**, I can stop at any stage and **resume** later with identical UI state, config, and hashes.

---

### 9) Headless Mode (API/CLI)
**As a developer**, I can run the entire pipeline programmatically and get all artifacts (plots, CSVs, JSON) for CI workflows.

---

### 10) Share (Read-Only)
**As a user**, I can share a **read-only** report link with embedded charts to collaborators.

---

### Future (Post‑MVP)
- **Batch fitting** across datasets with comparison tables.
- Permissions & collaboration.
- Scheduling and notifications.

---

## Non‑Functional Requirements
- Deterministic results (given same inputs & seeds).  
- Auditability (all changes logged and versioned).  
- Cross‑DB support: SQLite (dev) and PostgreSQL (prod).  
- Compute limits & timeouts; graceful cancellation.