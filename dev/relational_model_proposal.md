Data Model for Multiple Fittings

-- ============================================
-- USERS & AUTHENTICATION
-- ============================================

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    organization VARCHAR(255),
    role VARCHAR(50) DEFAULT 'researcher',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    preferences JSONB DEFAULT '{}',
    CONSTRAINT chk_role CHECK (role IN ('admin', 'researcher', 'viewer'))
);

-- ============================================
-- PROJECTS & ORGANIZATION
-- ============================================

CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    tags TEXT[],
    is_archived BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}',
    UNIQUE(user_id, name)
);

-- ============================================
-- DATASETS
-- ============================================

CREATE TABLE datasets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255),
    file_size_bytes INTEGER,
    material_type VARCHAR(100),
    temperature_c DECIMAL(5,2),
    measurement_date DATE,
    notes TEXT,
    status VARCHAR(50) DEFAULT 'uploaded',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}',
    CONSTRAINT chk_status CHECK (status IN ('uploaded', 'processing', 'preprocessed', 'analyzed', 'error'))
);

-- ============================================
-- RAW DATA STORAGE
-- ============================================

CREATE TABLE raw_data_points (
    id BIGSERIAL PRIMARY KEY,
    dataset_id UUID NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
    frequency_ghz DOUBLE PRECISION NOT NULL,
    dk DOUBLE PRECISION NOT NULL,
    df DOUBLE PRECISION NOT NULL,
    point_index INTEGER NOT NULL,
    is_outlier BOOLEAN DEFAULT false,
    UNIQUE(dataset_id, point_index)
);

-- Index for fast frequency-based queries
CREATE INDEX idx_raw_data_frequency ON raw_data_points(dataset_id, frequency_ghz);

-- ============================================
-- PREPROCESSED DATA
-- ============================================

CREATE TABLE preprocessing_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dataset_id UUID NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
    version INTEGER NOT NULL DEFAULT 1,
    smoothing_method VARCHAR(50),
    smoothing_params JSONB,
    outlier_method VARCHAR(50),
    outlier_params JSONB,
    baseline_correction BOOLEAN DEFAULT false,
    hook_correction_cp DOUBLE PRECISION,
    frequency_min_ghz DOUBLE PRECISION,
    frequency_max_ghz DOUBLE PRECISION,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by UUID REFERENCES users(id),
    is_active BOOLEAN DEFAULT true,
    UNIQUE(dataset_id, version),
    CONSTRAINT chk_smoothing CHECK (smoothing_method IN (NULL, 'none', 'savitzky_golay', 'moving_average')),
    CONSTRAINT chk_outlier CHECK (outlier_method IN (NULL, 'none', 'statistical', 'manual'))
);

CREATE TABLE preprocessed_data_points (
    id BIGSERIAL PRIMARY KEY,
    preprocessing_config_id UUID NOT NULL REFERENCES preprocessing_configs(id) ON DELETE CASCADE,
    frequency_ghz DOUBLE PRECISION NOT NULL,
    epsilon_real DOUBLE PRECISION NOT NULL,
    epsilon_imag DOUBLE PRECISION NOT NULL,
    tan_delta DOUBLE PRECISION GENERATED ALWAYS AS (epsilon_imag / NULLIF(epsilon_real, 0)) STORED,
    point_index INTEGER NOT NULL,
    is_excluded BOOLEAN DEFAULT false,
    UNIQUE(preprocessing_config_id, point_index)
);

CREATE INDEX idx_preprocessed_frequency ON preprocessed_data_points(preprocessing_config_id, frequency_ghz);

-- ============================================
-- ANALYSIS & DIAGNOSTICS
-- ============================================

CREATE TABLE analyses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dataset_id UUID NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
    preprocessing_config_id UUID REFERENCES preprocessing_configs(id),
    kk_valid BOOLEAN,
    kk_rmse DOUBLE PRECISION,
    kk_residuals JSONB,
    epsilon_inf_estimated DOUBLE PRECISION,
    sigma_dc_estimated DOUBLE PRECISION,
    num_peaks_detected INTEGER,
    peak_frequencies_ghz DOUBLE PRECISION[],
    peak_characteristics JSONB,
    suggested_model VARCHAR(50),
    suggested_params JSONB,
    quality_score DECIMAL(3,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    analysis_params JSONB DEFAULT '{}'
);

-- ============================================
-- MODEL DEFINITIONS
-- ============================================ 

CREATE TABLE model_types (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    category VARCHAR(50),
    equation_latex TEXT,
    parameters_schema JSONB,
    supports_multi_term BOOLEAN DEFAULT false,
    description TEXT,
    CONSTRAINT chk_category CHECK (category IN ('relaxation', 'resonance', 'hybrid', 'empirical'))
);

-- Seed model types
INSERT INTO model_types (code, name, category, equation_latex, parameters_schema, supports_multi_term, description) VALUES
('DEBYE', 'Debye (Multi-Pole)', 'relaxation',
'\hat{\varepsilon}(\omega) = \varepsilon_\infty + \sum_{k=1}^{N} {\frac{\Delta\varepsilon_k}{1 + j\omega\tau_k}} - {\frac{j\sigma_{dc}}{\omega\varepsilon_0}}',
'[\n    {\"name\": \"epsilon_inf\", \"description\": \"Permittivity at infinite frequency\", \"default_value\": 3.0, \"bounds\": [1.0, 10.0], \"unit\": null},\n    {\"name\": \"delta_epsilon\", \"description\": \"Relaxation strength of pole k\", \"default_value\": 10.0, \"bounds\": [0.1, 100.0], \"unit\": null},\n    {\"name\": \"tau\", \"description\": \"Relaxation time of pole k\", \"default_value\": 1e-6, \"bounds\": [1e-12, 1e-3], \"unit\": \"s\"},\n    {\"name\": \"sigma_dc\", \"description\": \"DC conductivity\", \"default_value\": 0, \"bounds\": [0, 1e-6], \"unit\": \"S/m\"}
]', true, 'N-pole relaxation model (N=1 for single Debye)'),

('COLE_COLE', 'Cole-Cole', 'relaxation',
'\hat{\varepsilon}(\omega) = \varepsilon_\infty + {\frac{\Delta\varepsilon}{1 + (j\omega\tau)^\alpha}} - {\frac{j\sigma_{dc}}{\omega\varepsilon_0}}',
'[\n    {\"name\": \"epsilon_inf\", \"description\": \"Permittivity at infinite frequency\", \"default_value\": 3.0, \"bounds\": [1.0, 10.0], \"unit\": null},\n    {\"name\": \"delta_epsilon\", \"description\": \"Relaxation strength\", \"default_value\": 10.0, \"bounds\": [0.1, 100.0], \"unit\": null},\n    {\"name\": \"tau\", \"description\": \"Relaxation time\", \"default_value\": 1e-6, \"bounds\": [1e-12, 1e-3], \"unit\": \"s\"},\n    {\"name\": \"alpha\", \"description\": \"Broadening parameter (0 < α ≤ 1)\", \"default_value\": 0.8, \"bounds\": [0.001, 1.0], \"unit\": null},\n    {\"name\": \"sigma_dc\", \"description\": \"DC conductivity\", \"default_value\": 0, \"bounds\": [0, 1e-6], \"unit\": \"S/m\"}
]', false, 'Symmetric broadening of the relaxation peak.'),

('COLE_DAVIDSON', 'Cole-Davidson', 'relaxation',
'\hat{\varepsilon}(\omega) = \varepsilon_\infty + {\frac{\Delta\varepsilon}{(1 + j\omega\tau)^\beta}} - {\frac{j\sigma_{dc}}{\omega\varepsilon_0}}',
'[\n    {\"name\": \"epsilon_inf\", \"description\": \"Permittivity at infinite frequency\", \"default_value\": 3.0, \"bounds\": [1.0, 10.0], \"unit\": null},\n    {\"name\": \"delta_epsilon\", \"description\": \"Relaxation strength\", \"default_value\": 10.0, \"bounds\": [0.1, 100.0], \"unit\": null},\n    {\"name\": \"tau\", \"description\": \"Relaxation time\", \"default_value\": 1e-6, \"bounds\": [1e-12, 1e-3], \"unit\": \"s\"},\n    {\"name\": \"beta\", \"description\": \"Skewness parameter (0 < β ≤ 1)\", \"default_value\": 0.5, \"bounds\": [0.001, 1.0], \"unit\": null},\n    {\"name\": \"sigma_dc\", \"description\": \"DC conductivity\", \"default_value\": 0, \"bounds\": [0, 1e-6], \"unit\": \"S/m\"}
]', false, 'Asymmetric peak with high-frequency tail.'),

('HN', 'Havriliak-Negami', 'relaxation',
'\hat{\varepsilon}(\omega) = \varepsilon_\infty + {\frac{\varepsilon_s - \varepsilon_\infty}{(1 + (j\omega\tau)^\alpha)^\beta}} - {\frac{j\sigma_{dc}}{\omega\varepsilon_0}}',
'[\n    {\"name\": \"epsilon_inf\", \"description\": \"Permittivity at infinite frequency\", \"default_value\": 3.0, \"bounds\": [1.0, 10.0], \"unit\": null},\n    {\"name\": \"epsilon_s\", \"description\": \"Static permittivity\", \"default_value\": 15.0, \"bounds\": [1.0, 200.0], \"unit\": null},\n    {\"name\": \"tau\", \"description\": \"Relaxation time\", \"default_value\": 1e-6, \"bounds\": [1e-12, 1e-3], \"unit\": \"s\"},\n    {\"name\": \"alpha\", \"description\": \"Shape parameter (related to width)\", \"default_value\": 0.8, \"bounds\": [0.001, 1.0], \"unit\": null},\n    {\"name\": \"beta\", \"description\": \"Shape parameter (related to skewness)\", \"default_value\": 0.5, \"bounds\": [0.001, 1.0], \"unit\": null},\n    {\"name\": \"sigma_dc\", \"description\": \"DC conductivity\", \"default_value\": 0, \"bounds\": [0, 1e-6], \"unit\": \"S/m\"}
]', false, 'General model for asymmetric and broad peaks.'),

('DS', 'Djordjević-Sarkar', 'empirical',
'\hat{\varepsilon}(\omega) = \varepsilon_\infty + {\frac{\Delta\varepsilon}{1 - {\frac{j\omega}{\omega_2}}}} {\frac{\ln(1 + j\omega/\omega_1)}{\ln(1 + j\omega/\omega_2)}}',
'[\n    {\"name\": \"epsilon_inf\", \"description\": \"Permittivity at infinite frequency\", \"default_value\": 2.5, \"bounds\": [1.0, 10.0], \"unit\": null},\n    {\"name\": \"delta_epsilon\", \"description\": \"Relaxation strength\", \"default_value\": 1.0, \"bounds\": [0.1, 10.0], \"unit\": null},\n    {\"name\": \"omega_1\", \"description\": \"Lower transition angular frequency\", \"default_value\": 1e3, \"bounds\": [1, 1e6], \"unit\": \"rad/s\"},\n    {\"name\": \"omega_2\", \"description\": \"Upper transition angular frequency\", \"default_value\": 1e12, \"bounds\": [1e9, 1e15], \"unit\": \"rad/s\"},\n    {\"name\": \"sigma_dc\", \"description\": \"DC conductivity\", \"default_value\": 0, \"bounds\": [0, 1e-6], \"unit\": \"S/m\"}
]', false, 'Wideband model for low-loss dielectrics like PCB substrates.');


-- ============================================
-- MODEL CONFIGURATIONS & FITTINGS
-- ============================================

CREATE TABLE model_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dataset_id UUID NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
    preprocessing_config_id UUID REFERENCES preprocessing_configs(id),
    analysis_id UUID REFERENCES analyses(id),
    model_type_id INTEGER NOT NULL REFERENCES model_types(id),
    name VARCHAR(255),
    num_terms INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by UUID REFERENCES users(id),
    notes TEXT,
    CONSTRAINT chk_num_terms CHECK (num_terms >= 1 AND num_terms <= 20)
);

CREATE TABLE model_parameters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_config_id UUID NOT NULL REFERENCES model_configs(id) ON DELETE CASCADE,
    term_index INTEGER NOT NULL DEFAULT 0,
    parameter_name VARCHAR(50) NOT NULL,
    initial_value DOUBLE PRECISION,
    lower_bound DOUBLE PRECISION,
    upper_bound DOUBLE PRECISION,
    is_fixed BOOLEAN DEFAULT false,
    UNIQUE(model_config_id, term_index, parameter_name),
    CONSTRAINT chk_bounds CHECK (lower_bound <= initial_value AND initial_value <= upper_bound)
);

-- ============================================
-- FITTING RESULTS
-- ============================================

CREATE TABLE fitting_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_config_id UUID NOT NULL REFERENCES model_configs(id) ON DELETE CASCADE,
    version INTEGER NOT NULL DEFAULT 1,
    algorithm VARCHAR(50) DEFAULT 'levenberg_marquardt',
    max_iterations INTEGER DEFAULT 1000,
    tolerance DOUBLE PRECISION DEFAULT 1e-6,
    weighting_scheme VARCHAR(50) DEFAULT 'none',
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    status VARCHAR(50) DEFAULT 'pending',
    convergence_reason VARCHAR(100),
    num_iterations INTEGER,
    computation_time_ms INTEGER,
    created_by UUID REFERENCES users(id),
    UNIQUE(model_config_id, version),
    CONSTRAINT chk_status CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled')),
    CONSTRAINT chk_algorithm CHECK (algorithm IN ('levenberg_marquardt', 'trust_region', 'differential_evolution'))
);

CREATE TABLE fitted_parameters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    fitting_session_id UUID NOT NULL REFERENCES fitting_sessions(id) ON DELETE CASCADE,
    term_index INTEGER NOT NULL DEFAULT 0,
    parameter_name VARCHAR(50) NOT NULL,
    fitted_value DOUBLE PRECISION NOT NULL,
    std_error DOUBLE PRECISION,
    confidence_lower DOUBLE PRECISION,
    confidence_upper DOUBLE PRECISION,
    UNIQUE(fitting_session_id, term_index, parameter_name)
);

CREATE TABLE fitting_statistics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    fitting_session_id UUID UNIQUE NOT NULL REFERENCES fitting_sessions(id) ON DELETE CASCADE,
    rmse DOUBLE PRECISION,
    chi_squared DOUBLE PRECISION,
    reduced_chi_squared DOUBLE PRECISION,
    r_squared DOUBLE PRECISION,
    adjusted_r_squared DOUBLE PRECISION,
    aic DOUBLE PRECISION,
    bic DOUBLE PRECISION,
    degrees_of_freedom INTEGER,
    num_data_points INTEGER,
    max_residual DOUBLE PRECISION,
    mean_residual DOUBLE PRECISION,
    kk_consistency_rmse DOUBLE PRECISION
);

CREATE TABLE fitted_curves (
    id BIGSERIAL PRIMARY KEY,
    fitting_session_id UUID NOT NULL REFERENCES fitting_sessions(id) ON DELETE CASCADE,
    frequency_ghz DOUBLE PRECISION NOT NULL,
    epsilon_real_fitted DOUBLE PRECISION NOT NULL,
    epsilon_imag_fitted DOUBLE PRECISION NOT NULL,
    epsilon_real_residual DOUBLE PRECISION,
    epsilon_imag_residual DOUBLE PRECISION,
    point_index INTEGER NOT NULL,
    UNIQUE(fitting_session_id, point_index)
);

CREATE INDEX idx_fitted_curves_frequency ON fitted_curves(fitting_session_id, frequency_ghz);

-- ============================================
-- PARAMETER CORRELATIONS
-- ============================================

CREATE TABLE parameter_correlations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    fitting_session_id UUID NOT NULL REFERENCES fitting_sessions(id) ON DELETE CASCADE,
    param1_name VARCHAR(50) NOT NULL,
    param1_term INTEGER NOT NULL,
    param2_name VARCHAR(50) NOT NULL,
    param2_term INTEGER NOT NULL,
    correlation_coefficient DOUBLE PRECISION NOT NULL,
    UNIQUE(fitting_session_id, param1_name, param1_term, param2_name, param2_term),
    CONSTRAINT chk_correlation CHECK (correlation_coefficient >= -1 AND correlation_coefficient <= 1)
);

-- ============================================
-- COMPARISONS
-- ============================================

CREATE TABLE model_comparisons (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dataset_id UUID NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
    name VARCHAR(255),
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by UUID REFERENCES users(id)
);

CREATE TABLE comparison_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    comparison_id UUID NOT NULL REFERENCES model_comparisons(id) ON DELETE CASCADE,
    fitting_session_id UUID NOT NULL REFERENCES fitting_sessions(id),
    is_best_fit BOOLEAN DEFAULT false,
    ranking INTEGER,
    UNIQUE(comparison_id, fitting_session_id)
);

-- ============================================
-- EXPORTS & REPORTS
-- ============================================

CREATE TABLE export_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    dataset_id UUID REFERENCES datasets(id),
    fitting_session_id UUID REFERENCES fitting_sessions(id),
    comparison_id UUID REFERENCES model_comparisons(id),
    export_type VARCHAR(50) NOT NULL,
    file_format VARCHAR(20) NOT NULL,
    file_name VARCHAR(255),
    file_size_bytes INTEGER,
    storage_path TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}',
    CONSTRAINT chk_export_type CHECK (export_type IN ('data', 'plot', 'report', 'session')),
    CONSTRAINT chk_format CHECK (file_format IN ('csv', 'xlsx', 'pdf', 'png', 'svg', 'json', 'hdf5'))
);

-- ============================================
-- SESSION MANAGEMENT
-- ============================================

CREATE TABLE user_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    dataset_id UUID REFERENCES datasets(id),
    current_stage VARCHAR(50),
    stage_data JSONB DEFAULT '{}',
    ui_state JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP
);

-- ============================================
-- AUDIT & HISTORY
-- ============================================

CREATE TABLE audit_log (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50),
    entity_id UUID,
    old_values JSONB,
    new_values JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_audit_user ON audit_log(user_id, created_at DESC);
CREATE INDEX idx_audit_entity ON audit_log(entity_type, entity_id, created_at DESC);

-- ============================================
-- VIEWS FOR COMMON QUERIES
-- ============================================

-- View for dataset overview with latest fitting
CREATE VIEW dataset_overview AS
SELECT 
    d.id,
    d.name,
    d.material_type,
    d.created_at,
    u.username,
    COUNT(DISTINCT mc.id) as num_models,
    COUNT(DISTINCT fs.id) as num_fittings,
    MAX(fs.completed_at) as last_fitted,
    MIN(fst.rmse) as best_rmse
FROM datasets d
LEFT JOIN users u ON d.user_id = u.id
LEFT JOIN model_configs mc ON mc.dataset_id = d.id
LEFT JOIN fitting_sessions fs ON fs.model_config_id = mc.id AND fs.status = 'completed'
LEFT JOIN fitting_statistics fst ON fst.fitting_session_id = fs.id
GROUP BY d.id, d.name, d.material_type, d.created_at, u.username;

-- View for fitting comparison
CREATE VIEW fitting_comparison AS
SELECT 
    fs.id as fitting_id,
    d.name as dataset_name,
    mt.name as model_name,
    mc.num_terms,
    fs.version,
    fs.status,
    fs.completed_at,
    fst.rmse,
    fst.chi_squared,
    fst.r_squared,
    fst.aic,
    fst.bic
FROM fitting_sessions fs
JOIN model_configs mc ON fs.model_config_id = mc.id
JOIN datasets d ON mc.dataset_id = d.id
JOIN model_types mt ON mc.model_type_id = mt.id
LEFT JOIN fitting_statistics fst ON fst.fitting_session_id = fs.id
WHERE fs.status = 'completed';

-- ============================================
-- INDEXES FOR PERFORMANCE
-- ============================================

CREATE INDEX idx_datasets_user ON datasets(user_id, created_at DESC);
CREATE INDEX idx_datasets_project ON datasets(project_id);
CREATE INDEX idx_preprocessing_dataset ON preprocessing_configs(dataset_id, version);
CREATE INDEX idx_model_configs_dataset ON model_configs(dataset_id);
CREATE INDEX idx_fitting_sessions_config ON fitting_sessions(model_config_id, version);
CREATE INDEX idx_fitting_sessions_status ON fitting_sessions(status) WHERE status IN ('running', 'pending');
CREATE INDEX idx_export_history_user ON export_history(user_id, created_at DESC);
CREATE INDEX idx_user_sessions_active ON user_sessions(user_id) WHERE is_active = true;

-- ============================================
-- TRIGGERS FOR UPDATED_AT
-- ============================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_projects_updated_at BEFORE UPDATE ON projects
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_datasets_updated_at BEFORE UPDATE ON datasets
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();