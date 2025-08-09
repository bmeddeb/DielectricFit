Input/Output Overview:
INPUT: CSV (Frequency[GHz], Dk, Df)
OUTPUT: PDF Report, Fitted CSV, Plot Images, Analysis Session

Detailed Workflow StagesStage 1:
Data Import & Validation:
Actions:
  - Upload CSV file
  - Parse and validate format
  - Auto-detect data quality issues
  - Preview data table and initial plots

Validations:
  - Check CSV format (3 columns: Freq, Dk, Df)
  - Verify frequency units (GHz)
  - Check for missing/invalid values
  - Ensure monotonic frequency increase
  - Flag outliers

Output:
  - Dataset ID
  - Initial visualization
  - Data quality report
  - Proceed/Fix decision

Save Point: Raw data stored

Stage 2: Data Preparation:
Actions:
  - Convert Dk/Df to ε'/ε''
  - Apply smoothing (optional)
  - Remove outliers (manual/auto)
  - Baseline correction
  - Frequency range selection
  - Unit conversions if needed

Calculations:
  - ε' = Dk
  - ε'' = Dk * Df
  - tan(δ) = Df

Options:
  - Smoothing: [None, Savitzky-Golay, Moving Average]
  - Outlier removal: [Manual selection, Statistical (3σ), None]
  - Interpolation: [Linear, Cubic, None]

Output:
  - Cleaned dataset
  - Preprocessing parameters
  - Before/After comparison plots

Save Point: Preprocessed data + parameters

Stage 3: Analysis & Diagnostics:
Actions:
  - Kramers-Kronig consistency check
  - Peak detection and characterization
  - Calculate data statistics
  - Auto-suggest best model

KK Analysis:
  - Run KK transform
  - Calculate residuals
  - Identify causality violations
  - Extract ε∞ and σdc estimates

Peak Analysis:
  - Number of peaks
  - Peak symmetry
  - Peak width (FWHM)
  - Frequency of max loss

Auto-Suggestion Logic:
  IF constant tan(δ) → Djordjević-Sarkar
  IF single narrow peak → Debye (N=1)
  IF multiple peaks → Multi-Pole Debye (N=peaks)
  IF broad symmetric → Cole-Cole
  IF asymmetric → Cole-Davidson or HN

Output:
  - KK validation report
  - Suggested model(s)
  - Initial parameter estimates
  - Diagnostic plots

Save Point: Analysis results + suggestions

Stage 4: Model Configuration:
Actions:
  - Select model (manual or accept suggestion)
  - Set number of terms/poles
  - Define initial parameters
  - Set parameter bounds
  - Configure fitting options

Model Selection:
  - Primary model choice
  - Number of poles (for multi-term models)
  - Comparison mode (multiple models)

Parameter Configuration:
  For each model term:
    - Initial value (auto or manual)
    - Lower bound
    - Upper bound
    - Fixed/Free flag

Fitting Options:
  - Algorithm: [Levenberg-Marquardt, Trust-Region, Differential Evolution]
  - Max iterations: [100-10000]
  - Tolerance: [1e-6 to 1e-12]
  - Weighting: [None, 1/y, 1/y²]

Output:
  - Model configuration object
  - Initial parameter set
  - Bounds matrix

Save Point: Model configuration

Stage 5: Fitting Process:
Actions:
  - Run optimization
  - Real-time progress monitoring
  - Interactive parameter adjustment
  - Convergence checking

Real-time Features:
  - Live fit visualization
  - Residual monitoring
  - Parameter evolution
  - Convergence metrics

Interactive Controls:
  - Pause/Resume fitting
  - Manual parameter tweaks
  - Add/Remove terms
  - Change bounds on-the-fly

Convergence Criteria:
  - RMSE < threshold
  - χ² < threshold
  - Parameter change < tolerance
  - Max iterations reached

Output:
  - Optimized parameters
  - Fit statistics (RMSE, χ², R², AIC, BIC)
  - Convergence history
  - Residuals

Save Point: Fitting results (versioned)

Stage 6: Validation & Comparison:
Actions:
  - Validate fit quality
  - KK consistency of fitted model
  - Compare multiple fits
  - Statistical analysis

Validation Checks:
  - Residual randomness (runs test)
  - Parameter correlation matrix
  - Confidence intervals
  - Physical reasonableness

Comparison Features:
  - Overlay multiple fits
  - Side-by-side statistics
  - Model selection criteria (AIC/BIC)
  - Best fit recommendation

Output:
  - Validation report
  - Comparison matrix
  - Best model selection

Save Point: Validation results

Stage 7: Export & Reporting
Export Options:
  1. PDF Report:
     - Cover page with metadata
     - Data summary
     - All plots (original, fitted, residuals)
     - Parameter table with uncertainties
     - Fit statistics
     - KK validation results
     - Model equations

  2. CSV Exports:
     - Original data
     - Preprocessed data
     - Fitted curves
     - Residuals
     - Parameters with bounds

  3. Plot Images:
     - Bode plots (ε' and ε'')
     - Cole-Cole plot
     - 3D waterfall (if multiple datasets)
     - Residual plots
     - KK validation plots
     - Parameter correlation matrix

  4. Session File:
     - Complete analysis state
     - All configurations
     - Multiple fit versions
     - Re-loadable format (JSON/HDF5)

Formats:
  - Plots: PNG, SVG, PDF
  - Data: CSV, Excel, MAT
  - Report: PDF, HTML
  - Session: JSON, HDF5


Data Model for Multiple Fittings:
  class Dataset:
      id: str
      name: str
      raw_data: DataFrame
      preprocessed_data: DataFrame
      preprocessing_params: dict
      analysis_results: dict
      fittings: List[Fitting]
      created_at: datetime
      modified_at: datetime

  class Fitting:
      id: str
      dataset_id: str
      version: int
      model_type: str
      model_config: dict
      initial_params: dict
      bounds: dict
      fitted_params: dict
      fit_statistics: dict
      validation_results: dict
      created_at: datetime
      notes: str

  class Comparison:
      dataset_id: str
      fitting_ids: List[str]
      comparison_metrics: dict
      best_model_id: str
      comparison_plots: dict

Progress Saving Strategy:
Save Points:
  - After each stage completion
  - Every 5 minutes (auto-save)
  - Before major operations
  - On user request

Saved Data:
  - Current stage
  - All stage outputs
  - UI state (selected tabs, zoom levels)
  - Temporary calculations

Resume Capability:
  - Load session by ID
  - Restore to exact state
  - Show progress indicator
  - Option to restart from any stage

  # Data Management
  POST   /api/datasets/upload
  GET    /api/datasets/{id}
  PUT    /api/datasets/{id}/preprocess
  POST   /api/datasets/{id}/analyze

  # Fitting Management
  POST   /api/datasets/{id}/fittings
  GET    /api/datasets/{id}/fittings
  GET    /api/fittings/{id}
  PUT    /api/fittings/{id}/configure
  POST   /api/fittings/{id}/fit
  POST   /api/fittings/{id}/validate
  POST   /api/fittings/{id}/duplicate

  # Comparison
  POST   /api/datasets/{id}/compare
  GET    /api/comparisons/{id}

  # Export
  POST   /api/fittings/{id}/export/pdf
  POST   /api/fittings/{id}/export/csv
  POST   /api/fittings/{id}/export/plots
  GET    /api/datasets/{id}/export/session

  # Session Management
  POST   /api/sessions/save
  GET    /api/sessions/{id}
  POST   /api/sessions/{id}/restore
