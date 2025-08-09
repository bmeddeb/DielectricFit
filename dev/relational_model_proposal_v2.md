# DielectricFit — Relational Model Proposal (v2)
**Updated:** 2025-08-09  
**Stack:** Django ORM over SQLite (dev) and PostgreSQL (future)  
**Units:** Canonical storage in **Hz**, **s**, **S/m** (UI may display GHz).

## Cross‑DB Conventions
- **UUIDs** generated in app for SQLite; native UUID type in Postgres. Store as TEXT in SQLite models for portability.  
- **JSON**: Django `JSONField` maps to TEXT in SQLite and JSONB in Postgres.  
- **Generated columns** (e.g., tanδ) used where supported; otherwise computed in queries or maintained by model hooks.  
- All timestamps in UTC; store dataset unit provenance (`input_freq_unit`) and schema (`input_schema`).

---

## Entities & Key Tables

### datasets
- `id (UUID PK)`  
- `name TEXT`, `description TEXT`  
- `input_schema TEXT CHECK IN ('dk_df','eps')`  
- `input_freq_unit TEXT DEFAULT 'GHz'`  
- `ingest_fingerprint TEXT` (md5 of raw file)  
- `row_count INTEGER`  
- `status TEXT`, `created_at`, `updated_at`

### raw_data_points  (canonical: one row per original sample)
- `id (UUID PK)`, `dataset_id (FK datasets)`  
- `point_index INTEGER` (original order)  
- `frequency_hz REAL NOT NULL`  
- **Either**: `dk REAL`, `df REAL` **or** `epsilon_real REAL`, `epsilon_imag REAL` (nullable pair)  
- `tan_delta` (generated or maintained as ε″/ε′ when ε-values exist; else = df)  
- **Constraints**: `(dk,df) XOR (epsilon_real,epsilon_imag)` must be present  
- **Index**: `(dataset_id, frequency_hz)` unique

### preprocessing_configs
- `id (UUID PK)`, `dataset_id (FK)`, `config_json JSON`, `config_hash TEXT UNIQUE`, timestamps

### preprocessed_data_points
- `id (UUID PK)`, `preprocessing_config_id (FK)`  
- `frequency_hz REAL NOT NULL`  
- `epsilon_real REAL`, `epsilon_imag REAL`, `dk REAL`, `tan_delta REAL`  
- **Index**: `(preprocessing_config_id, frequency_hz)`

### analyses
- `id (UUID PK)`, `preprocessing_config_id (FK)`  
- `kk_metrics JSON`, `features JSON` (peaks, symmetry, σ_dc)  
- `scoring_breakdown JSON` (KK RMSE, peak symmetry, coarse AIC/BIC, σ_dc)  
- `autosuggest_top JSON` (Top‑3 models with score/confidence/rationale)  
- timestamps

### model_types  (model registry)
- `id (UUID PK)`, `name TEXT UNIQUE`, `equation_latex TEXT`  
- `parameters_schema JSON` — list of parameter objects with:  
  - `name`, `unit`, `default`, `min`, `max`, `step`  
  - `transform` ∈ {`linear`,`log`}  
  - `constraint` (e.g., `"tau>0"`, `"delta_eps>=0"`)  
  - `shared_across_terms` (bool)  
- `version INTEGER`, timestamps

### model_configs
- `id (UUID PK)`, `model_type_id (FK)`, `analysis_id (FK)` (nullable)  
- `name TEXT`, `notes TEXT`, timestamps

### model_parameters
- `id (UUID PK)`, `model_config_id (FK)`  
- `param_name TEXT`  
- `value REAL`, `min REAL`, `max REAL`  
- `transform TEXT CHECK IN ('linear','log')`  
- `tie_group TEXT NULL`  (shared parameters across terms)  
- `scale_hint REAL NULL`

### fitting_sessions
- `id (UUID PK)`, `model_config_id (FK)`, `preprocessing_config_id (FK)`  
- Optimizer config: `algorithm TEXT`, `max_iter INTEGER`, `tol REAL`  
- **Robust loss**: `loss_function TEXT CHECK IN ('linear','huber','soft_l1','cauchy','arctan') DEFAULT 'linear'`, `loss_scale REAL`  
- Weighting: `freq_weighting TEXT`, `component_weighting JSON`  
- **Multistart**: `multistart_group_id TEXT NULL`, `start_seed INTEGER NULL`  
- Results: `success BOOL`, `converged_reason TEXT`, `runtime_ms INTEGER`  
- Stats: `rmse REAL`, `chisq_red REAL`, `aic REAL`, `bic REAL`  
- timestamps  
- **Index**: `(multistart_group_id, aic)`

### residual_diagnostics
- `fitting_session_id (PK/FK)`  
- `dw_stat REAL`, `runs_p REAL`, `qq_normal_p REAL`, `autocorr_lag1 REAL`

### fitted_curves
- `id (UUID PK)`, `fitting_session_id (FK)`  
- `frequency_hz REAL NOT NULL`  
- `epsilon_real_fit REAL`, `epsilon_imag_fit REAL`, `dk_fit REAL`, `tan_delta_fit REAL`  
- `residual_real REAL`, `residual_imag REAL`  
- **Index**: `(fitting_session_id, frequency_hz)`

### artifacts
- `id (UUID PK)`, `fitting_session_id (FK)`  
- `kind TEXT CHECK IN ('npz','json','parquet','png','pdf','csv')`  
- `path TEXT`, `sha256 TEXT`, `bytes INTEGER`, timestamps

### shares (optional, for read‑only links)
- `id (UUID PK)`, `fitting_session_id (FK)` or `analysis_id (FK)`  
- `token TEXT UNIQUE`, `expires_at`, `can_download BOOL DEFAULT TRUE`, timestamps

---

## Views
- **best_fit_per_group**: for each `multistart_group_id`, select row with minimal AIC (tie‑break by BIC).  
- **model_comparisons**: summary by dataset/analysis showing top models & stats.

---

## Example (SQLite‑friendly) DDL Snippets

```sql
-- datasets (SQLite)
CREATE TABLE datasets (
  id TEXT PRIMARY KEY,
  name TEXT,
  description TEXT,
  input_schema TEXT NOT NULL CHECK (input_schema IN ('dk_df','eps')),
  input_freq_unit TEXT NOT NULL DEFAULT 'GHz',
  ingest_fingerprint TEXT,
  row_count INTEGER,
  status TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

```sql
-- raw_data_points
CREATE TABLE raw_data_points (
  id TEXT PRIMARY KEY,
  dataset_id TEXT NOT NULL,
  point_index INTEGER,
  frequency_hz REAL NOT NULL,
  dk REAL,
  df REAL,
  epsilon_real REAL,
  epsilon_imag REAL,
  -- tan_delta may be generated where supported; otherwise maintain via app logic
  tan_delta REAL,
  CHECK (
    (dk IS NOT NULL AND df IS NOT NULL AND epsilon_real IS NULL AND epsilon_imag IS NULL) OR
    (epsilon_real IS NOT NULL AND epsilon_imag IS NOT NULL AND dk IS NULL AND df IS NULL)
  ),
  FOREIGN KEY(dataset_id) REFERENCES datasets(id) ON DELETE CASCADE
);
CREATE UNIQUE INDEX idx_rawdata_freq ON raw_data_points(dataset_id, frequency_hz);
```

```sql
-- fitting_sessions (robust + multistart)
CREATE TABLE fitting_sessions (
  id TEXT PRIMARY KEY,
  model_config_id TEXT NOT NULL,
  preprocessing_config_id TEXT NOT NULL,
  algorithm TEXT,
  max_iter INTEGER,
  tol REAL,
  loss_function TEXT NOT NULL CHECK (loss_function IN ('linear','huber','soft_l1','cauchy','arctan')) DEFAULT 'linear',
  loss_scale REAL DEFAULT 1.0,
  freq_weighting TEXT,
  component_weighting TEXT,
  multistart_group_id TEXT,
  start_seed INTEGER,
  success INTEGER,
  converged_reason TEXT,
  runtime_ms INTEGER,
  rmse REAL, chisq_red REAL, aic REAL, bic REAL,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(model_config_id) REFERENCES model_configs(id) ON DELETE CASCADE,
  FOREIGN KEY(preprocessing_config_id) REFERENCES preprocessing_configs(id) ON DELETE CASCADE
);
CREATE INDEX idx_fit_group_aic ON fitting_sessions(multistart_group_id, aic);
```
```sql
-- residual_diagnostics
CREATE TABLE residual_diagnostics (
  fitting_session_id TEXT PRIMARY KEY,
  dw_stat REAL, runs_p REAL, qq_normal_p REAL, autocorr_lag1 REAL,
  FOREIGN KEY(fitting_session_id) REFERENCES fitting_sessions(id) ON DELETE CASCADE
);
```

---

## Django Implementation Notes
- Use Django `JSONField` for all JSON columns; on SQLite it stores TEXT transparently.  
- For **UUIDs**, prefer `models.UUIDField(default=uuid.uuid4, editable=False)`; keep TEXT in SQLite migrations.  
- Consider a small `ModelRegistry` service to validate parameter schemas (units, transforms, constraints) at runtime and to auto‑generate forms.  
- For generated columns like `tan_delta`, prefer app‑level computation for cross‑DB behavior; optionally add DB‑generated columns behind a setting for Postgres deployments.

---

## Roadmap Alignment
- v1: all tables above except `shares` (optional) and batch orchestration.  
- Future: batch fitting controller, team permissions, scheduled jobs, advanced provenance store.