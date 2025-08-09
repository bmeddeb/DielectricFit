
# Gemini Workflow Suggestions for DielectricFit

This document outlines a proposed workflow for the DielectricFit application, expanding on the existing analysis pipeline. The suggestions are based on the `analysis.html` mockup and general best practices for dielectric spectroscopy data analysis, with a focus on the Kramers-Kronig (KK) relations.

I was unable to locate the `workflow.md`, `workflow_v2.md`, and the Kramers-Kronig guide you mentioned. The following is based on the information I was able to gather from the existing files.

## Proposed Workflow

The proposed workflow is broken down into user stories and tasks, following a Scrum-like methodology.

### User Story 1: Data Diagnosis and Pre-processing

**As a scientist,** I want to diagnose my raw data for common issues and apply pre-processing steps to ensure it is ready for Kramers-Kronig analysis and model fitting.

#### Tasks:

*   **Data Integrity Check:**
    *   Implement a check for missing values in the dataset and provide options for handling them (e.g., interpolation, row removal).
    *   Implement a check for duplicate frequency points and provide an automated way to handle them (e.g., averaging, removal).
    *   Implement a check for negative values in the real (ε') and imaginary (ε'') parts of the permittivity, which are generally unphysical.
*   **Visual Inspection:**
    *   Provide interactive plots of ε' and ε'' vs. frequency to allow for visual inspection of the data.
    *   Implement a Cole-Cole plot (ε'' vs. ε') to help visualize the relaxation processes.
*   **Kramers-Kronig (KK) Consistency Check:**
    *   Implement a function to perform a KK transform on the measured data.
    *   Calculate and display the residuals between the original data and the KK-transformed data to quantify the consistency.
    *   Provide a clear visual representation of the KK residuals (e.g., a plot of residuals vs. frequency).
    *   Display a quantitative measure of KK consistency (e.g., a chi-squared statistic).
*   **Data Correction and Pre-processing:**
    *   **Hook Correction:** Implement a feature to correct for low-frequency "hook" artifacts, which may be caused by electrode polarization or DC conductivity. This could involve fitting and subtracting a power-law contribution.
    *   **DC Conductivity Removal:** Implement a method to subtract the contribution of DC conductivity from the imaginary part of the permittivity (ε'').
    *   **Smoothing:** Provide a selection of smoothing algorithms (e.g., Savitzky-Golay, Moving Average) with adjustable parameters to reduce noise in the data.
    *   **Baseline Correction:** Implement a baseline correction feature to remove any unwanted background signal.

### User Story 2: Model Fitting and Validation

**As a scientist,** I want to fit my pre-processed data to various dielectric models and validate the quality of the fit to ensure it accurately represents the underlying physical processes.

#### Tasks:

*   **Model Selection:**
    *   Provide a library of common dielectric models to choose from (e.g., Debye, Cole-Cole, Cole-Davidson, Havriliak-Negami).
    *   Allow for the combination of multiple models to fit complex spectra.
*   **Goodness of Fit:**
    *   Calculate and display standard goodness-of-fit metrics, such as R-squared and chi-squared.
    *   Provide a plot of the residuals (measured data - fitted model) vs. frequency to visually assess the quality of the fit.
*   **Physical Plausibility:**
    *   Implement checks to ensure that the fitted model parameters are within a physically reasonable range.
    *   Display warnings or flags for parameters that fall outside of the expected range.
*   **Cross-validation:**
    *   Implement a cross-validation technique (e.g., k-fold cross-validation) to assess the model's predictive performance and avoid overfitting.
*   **Model Comparison:**
    *   Provide a feature to compare the results of different models fitted to the same dataset.
    *   Display a comparison table with the key parameters and goodness-of-fit metrics for each model.

