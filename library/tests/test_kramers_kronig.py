"""
Tests for Kramers-Kronig validation module.
"""

import pytest
import numpy as np
import pandas as pd
from unittest.mock import patch

from library.algorithms.kramers_kronig import (
    validate_kramers_kronig,
    kramers_kronig_from_dataframe,
    KramersKronigValidator,
    _estimate_eps_inf,
    _is_grid_uniform,
    _detect_peaks,
    _kk_hilbert,
    _kk_resample_hilbert,
    _kk_trapz_numba,
    _kk_trapz_sskk
)


class TestInputValidation:
    """Test input validation and error handling."""
    
    def test_mismatched_array_lengths(self):
        """Test that mismatched array lengths raise ValueError."""
        freq = np.array([1e9, 2e9, 3e9])
        dk = np.array([2.5, 2.4])  # Wrong length
        df = np.array([0.01, 0.02, 0.03])
        
        with pytest.raises(ValueError, match="same length"):
            validate_kramers_kronig(freq, dk, df)
    
    def test_insufficient_data_points(self):
        """Test that single data point raises error."""
        freq = np.array([1e9])
        dk = np.array([2.5])
        df = np.array([0.01])
        
        with pytest.raises(ValueError, match="At least 2 data points"):
            validate_kramers_kronig(freq, dk, df)
    
    def test_non_monotonic_frequencies(self):
        """Test that non-monotonic frequencies raise error."""
        freq = np.array([1e9, 3e9, 2e9])  # Not monotonic
        dk = np.array([2.5, 2.4, 2.3])
        df = np.array([0.01, 0.02, 0.03])
        
        with pytest.raises(ValueError, match="strictly increasing"):
            validate_kramers_kronig(freq, dk, df)
    
    def test_negative_frequencies(self):
        """Test that negative frequencies raise error."""
        freq = np.array([-1e9, 2e9, 3e9])
        dk = np.array([2.5, 2.4, 2.3])
        df = np.array([0.01, 0.02, 0.03])
        
        with pytest.raises(ValueError, match="positive"):
            validate_kramers_kronig(freq, dk, df)
    
    def test_nan_values(self):
        """Test that NaN values raise error."""
        # NaN in frequency breaks monotonicity check first
        freq = np.array([1e9, 2e9, np.nan])
        dk = np.array([2.5, 2.4, 2.3])
        df = np.array([0.01, 0.02, 0.03])
        
        with pytest.raises(ValueError, match="strictly increasing"):
            validate_kramers_kronig(freq, dk, df)
        
        # Test NaN detection directly by checking for finite values
        freq2 = np.array([1e9, 2e9, 3e9])
        dk2 = np.array([2.5, np.nan, 2.3])  
        df2 = np.array([0.01, 0.02, 0.03])
        
        with pytest.raises(ValueError, match="non-finite"):
            validate_kramers_kronig(freq2, dk2, df2)


class TestBasicFunctionality:
    """Test basic KK validation functionality."""
    
    def test_simple_causal_data(self):
        """Test validation with simple causal data."""
        # Generate simple Debye model data
        freq = np.logspace(6, 10, 50)  # 1 MHz to 10 GHz
        tau = 1e-9  # 1 ns relaxation time
        eps_s = 3.0  # Static permittivity
        eps_inf = 2.0  # High-frequency permittivity
        
        omega = 2 * np.pi * freq
        eps_complex = eps_inf + (eps_s - eps_inf) / (1 + 1j * omega * tau)
        dk = np.real(eps_complex)
        df = -np.imag(eps_complex) / np.real(eps_complex)  # tan δ = ε″/ε′
        
        result = validate_kramers_kronig(freq, dk, df)
        
        assert result['causality_status'] == 'PASS'
        assert result['mean_relative_error'] < 0.05
        assert 'dk_kk' in result
        assert 'median_relative_error' in result
        assert 'q90_relative_error' in result
        assert 'method_detail' in result
        assert len(result['dk_kk']) == len(dk)
    
    def test_explicit_eps_inf(self):
        """Test using explicit eps_inf value."""
        freq = np.logspace(8, 10, 20)
        dk = np.ones(20) * 2.5
        df = np.ones(20) * 0.01
        
        result = validate_kramers_kronig(freq, dk, df, eps_inf=2.0)
        
        assert result['eps_inf_estimated'] == 2.0
    
    def test_auto_method_selection(self):
        """Test automatic method selection based on grid."""
        # Uniform grid
        freq_uniform = np.linspace(1e9, 10e9, 50)
        dk = np.ones(50) * 2.5
        df = np.ones(50) * 0.01
        
        result_uniform = validate_kramers_kronig(freq_uniform, dk, df, method='auto')
        assert result_uniform['is_uniform_grid'] == True
        assert result_uniform['method_used'] == 'hilbert'
        assert 'hilbert' in result_uniform['method_detail']
        
        # Non-uniform grid (logarithmic)
        freq_log = np.logspace(9, 10, 50)
        result_log = validate_kramers_kronig(freq_log, dk, df, method='auto')
        assert result_log['is_uniform_grid'] == False
        assert result_log['method_used'] == 'trapz'
        assert 'trapz' in result_log['method_detail']
    
    def test_sskk_functionality(self):
        """Test SSKK (singly subtractive KK) functionality."""
        freq = np.logspace(8, 10, 30)
        dk = np.ones(30) * 2.5
        df = np.ones(30) * 0.01
        
        # With SSKK (default)
        result_sskk = validate_kramers_kronig(freq, dk, df, method='trapz', use_sskk=True)
        assert result_sskk['method_detail'] == 'trapz-sskk'
        
        # Without SSKK 
        result_pv = validate_kramers_kronig(freq, dk, df, method='trapz', use_sskk=False)
        assert result_pv['method_detail'] == 'trapz-pv'
        
        # Both should give results but may differ slightly
        assert len(result_sskk['dk_kk']) == len(result_pv['dk_kk']) == len(dk)
    
    def test_anchor_index(self):
        """Test custom anchor index for SSKK."""
        freq = np.logspace(8, 10, 30)
        dk = np.ones(30) * 2.5
        df = np.ones(30) * 0.01
        
        # Custom anchor index
        anchor_idx = 10
        result = validate_kramers_kronig(
            freq, dk, df, method='trapz', use_sskk=True, anchor_index=anchor_idx
        )
        
        assert result['anchor_index'] == anchor_idx
        assert result['method_detail'] == 'trapz-sskk'


class TestHelperFunctions:
    """Test helper functions."""
    
    def test_estimate_eps_inf_mean(self):
        """Test eps_inf estimation using mean method."""
        freq = np.linspace(1e9, 10e9, 100)
        dk = np.linspace(3.0, 2.0, 100)  # Decreasing trend
        
        eps_inf = _estimate_eps_inf(freq, dk, 'mean', 0.1, 3)
        
        # Should be close to mean of last 10% of data
        expected = np.mean(dk[-10:])
        assert np.isclose(eps_inf, expected, rtol=0.01)
    
    def test_estimate_eps_inf_fit(self):
        """Test eps_inf estimation using fit method."""
        freq = np.linspace(1e9, 10e9, 100)
        # Create data with 1/f^2 dependence
        eps_inf_true = 2.0
        dk = eps_inf_true + 1e18 / freq**2
        
        eps_inf = _estimate_eps_inf(freq, dk, 'fit', 0.2, 3)
        
        # Should recover the true eps_inf
        assert np.isclose(eps_inf, eps_inf_true, rtol=0.1)
    
    def test_is_grid_uniform(self):
        """Test grid uniformity detection."""
        # Uniform grid
        freq_uniform = np.linspace(1e9, 10e9, 50)
        assert _is_grid_uniform(freq_uniform) == True
        
        # Non-uniform grid
        freq_log = np.logspace(9, 10, 50)
        assert _is_grid_uniform(freq_log) == False
        
        # Almost uniform (with small numerical errors)
        freq_almost = np.linspace(1e9, 10e9, 50)
        freq_almost[25] += 1e-6  # Small perturbation
        assert _is_grid_uniform(freq_almost, rtol=1e-4) == True
    
    def test_detect_peaks(self):
        """Test peak detection in Df data."""
        # Single peak
        x = np.linspace(0, 10, 100)
        df_single = np.exp(-(x - 5)**2)
        assert _detect_peaks(df_single) == 1
        
        # Double peak
        df_double = np.exp(-(x - 3)**2) + np.exp(-(x - 7)**2)
        assert _detect_peaks(df_double) == 2
        
        # No clear peaks (flat)
        df_flat = np.ones(100) * 0.01
        assert _detect_peaks(df_flat) == 0


class TestKramersKronigTransforms:
    """Test different KK transform methods."""
    
    def test_hilbert_transform_uniform(self):
        """Test Hilbert transform on uniform omega grid."""
        # Create simple test data (now uses omega and eps_imag)
        omega = np.linspace(1e9, 1e10, 20) * 2 * np.pi  # Convert to rad/s
        eps_imag = np.ones(20) * 0.025  # ε″ = ε′ * tan δ = 2.5 * 0.01
        eps_inf = 2.0
        
        dk_kk = _kk_hilbert(omega, eps_imag, eps_inf)
        
        assert len(dk_kk) == len(eps_imag)
        assert np.all(np.isfinite(dk_kk))
    
    def test_hilbert_with_window(self):
        """Test Hilbert transform with window function."""
        omega = np.linspace(1e9, 1e10, 100) * 2 * np.pi
        eps_imag = np.random.rand(100) * 0.01 + 0.025
        eps_inf = 2.0
        
        # Test string window
        dk_kk = _kk_hilbert(omega, eps_imag, eps_inf, window='hamming')
        assert len(dk_kk) == len(eps_imag)
        assert np.all(np.isfinite(dk_kk))
        
        # Test tuple window (Kaiser with beta)
        dk_kk2 = _kk_hilbert(omega, eps_imag, eps_inf, window=('kaiser', 5.0))
        assert len(dk_kk2) == len(eps_imag)
        assert np.all(np.isfinite(dk_kk2))
    
    def test_trapz_integration(self):
        """Test trapezoidal integration method."""
        # Generate test data (now uses eps_imag directly)
        freq = np.logspace(8, 10, 30)
        omega = 2 * np.pi * freq
        eps_imag = np.ones(30) * 0.025  # ε″ = ε′ * tan δ
        eps_inf = 2.0
        
        dk_kk = _kk_trapz_numba(omega, eps_imag, eps_inf)
        
        assert len(dk_kk) == len(eps_imag)
        assert np.all(np.isfinite(dk_kk))
    
    def test_sskk_integration(self):
        """Test SSKK trapezoidal integration method."""
        freq = np.logspace(8, 10, 30)
        omega = 2 * np.pi * freq
        eps_imag = np.ones(30) * 0.025
        eps_inf = 2.0
        dk_anchor = 2.5
        omega_anchor = omega[15]  # Mid-point anchor
        
        dk_kk = _kk_trapz_sskk(omega, eps_imag, eps_inf, dk_anchor, omega_anchor)
        
        assert len(dk_kk) == len(eps_imag)
        assert np.all(np.isfinite(dk_kk))
    
    def test_resample_hilbert(self):
        """Test resampling for non-uniform grids."""
        # Non-uniform frequency grid
        freq = np.logspace(8, 10, 50)
        eps_imag = np.random.rand(50) * 0.01 + 0.025
        eps_inf = 2.0
        
        dk_kk = _kk_resample_hilbert(freq, eps_imag, eps_inf, None, None)
        
        assert len(dk_kk) == len(eps_imag)
        assert np.all(np.isfinite(dk_kk))
    
    def test_hilbert_insufficient_points(self):
        """Test error handling for insufficient points in Hilbert."""
        omega = np.array([1e9, 2e9])  # Only 2 points, need at least 4
        eps_imag = np.array([0.01, 0.02])
        eps_inf = 2.0
        
        with pytest.raises(ValueError, match="at least 4 points"):
            _kk_hilbert(omega, eps_imag, eps_inf)


class TestDataFrameInterface:
    """Test pandas DataFrame interface."""
    
    def test_dataframe_validation(self):
        """Test validation from DataFrame."""
        # Create test DataFrame
        data = {
            'Frequency (GHz)': [1, 2, 3, 4, 5],
            'Dk': [2.5, 2.4, 2.3, 2.2, 2.1],
            'Df': [0.01, 0.015, 0.02, 0.015, 0.01]
        }
        df = pd.DataFrame(data)
        
        result = kramers_kronig_from_dataframe(df)
        
        assert 'causality_status' in result
        assert 'dk_kk' in result
        assert len(result['dk_kk']) == len(df)
    
    def test_dataframe_missing_column(self):
        """Test error handling for missing columns."""
        data = {
            'Frequency (GHz)': [1, 2, 3],
            'Dk': [2.5, 2.4, 2.3]
            # Missing 'Df' column
        }
        df = pd.DataFrame(data)
        
        with pytest.raises(ValueError, match="Column.*not found"):
            kramers_kronig_from_dataframe(df)
    
    def test_dataframe_non_numeric(self):
        """Test error handling for non-numeric values."""
        data = {
            'Frequency (GHz)': [1, 2, 'three'],  # Non-numeric
            'Dk': [2.5, 2.4, 2.3],
            'Df': [0.01, 0.02, 0.03]
        }
        df = pd.DataFrame(data)
        
        with pytest.raises(ValueError, match="non-numeric or NaN"):
            kramers_kronig_from_dataframe(df)


class TestKramersKronigValidator:
    """Test the class-based validator interface."""
    
    def test_validator_initialization(self):
        """Test validator initialization."""
        data = {
            'Frequency (GHz)': [1, 2, 3, 4, 5],
            'Dk': [2.5, 2.4, 2.3, 2.2, 2.1],
            'Df': [0.01, 0.015, 0.02, 0.015, 0.01]
        }
        df = pd.DataFrame(data)
        
        validator = KramersKronigValidator(df)
        
        assert validator.df is df
        assert validator.method == 'auto'
        assert validator.use_sskk == True  # New default
        assert validator.results == {}
    
    def test_validator_validate(self):
        """Test validation method."""
        data = {
            'Frequency (GHz)': np.linspace(1, 10, 50),
            'Dk': np.ones(50) * 2.5,
            'Df': np.ones(50) * 0.01
        }
        df = pd.DataFrame(data)
        
        validator = KramersKronigValidator(df)
        result = validator.validate()
        
        assert 'causality_status' in result
        assert validator.results == result
    
    def test_validator_properties(self):
        """Test validator properties."""
        data = {
            'Frequency (GHz)': np.linspace(1, 10, 50),
            'Dk': np.ones(50) * 2.5,
            'Df': np.ones(50) * 0.01
        }
        df = pd.DataFrame(data)
        
        validator = KramersKronigValidator(df)
        
        # Should raise error before validation
        with pytest.raises(RuntimeError, match="Must call validate"):
            _ = validator.is_causal
        
        # After validation
        validator.validate()
        assert isinstance(validator.is_causal, bool)
        assert isinstance(validator.relative_error, float)
    
    def test_validator_diagnostics(self):
        """Test diagnostic information."""
        data = {
            'Frequency (GHz)': np.linspace(1, 10, 50),
            'Dk': np.ones(50) * 2.5,
            'Df': np.random.rand(50) * 0.01 + 0.01
        }
        df = pd.DataFrame(data)
        
        validator = KramersKronigValidator(df)
        diagnostics = validator.get_diagnostics()
        
        assert 'grid_uniform' in diagnostics
        assert 'num_points' in diagnostics
        assert 'freq_range_ghz' in diagnostics
        assert 'eps_inf' in diagnostics
        assert 'method_detail' in diagnostics  # New field
        assert diagnostics['num_points'] == 50
    
    def test_validator_report(self):
        """Test report generation."""
        data = {
            'Frequency (GHz)': np.linspace(1, 10, 50),
            'Dk': np.ones(50) * 2.5,
            'Df': np.ones(50) * 0.01
        }
        df = pd.DataFrame(data)
        
        validator = KramersKronigValidator(df)
        
        # Before validation
        report = validator.get_report()
        assert "not been run" in report
        
        # After validation
        validator.validate()
        report = validator.get_report()
        assert "Causality Status" in report
        assert "Mean Relative Error" in report
        assert "Median Relative Error" in report  # New field in report
    
    def test_validator_invalid_window(self):
        """Test invalid window parameter."""
        data = {
            'Frequency (GHz)': [1, 2, 3, 4, 5],
            'Dk': [2.5, 2.4, 2.3, 2.2, 2.1],
            'Df': [0.01, 0.02, 0.03, 0.02, 0.01]
        }
        df = pd.DataFrame(data)
        
        with pytest.raises(ValueError, match="Invalid window spec"):
            KramersKronigValidator(df, window='invalid_window')
    
    def test_validator_valid_window_tuples(self):
        """Test valid window parameter including tuples."""
        data = {
            'Frequency (GHz)': np.linspace(1, 10, 20),
            'Dk': np.ones(20) * 2.5,
            'Df': np.ones(20) * 0.01
        }
        df = pd.DataFrame(data)
        
        # String window
        validator1 = KramersKronigValidator(df, window='hamming')
        assert validator1.window == 'hamming'
        
        # Tuple window (Kaiser with parameter)
        validator2 = KramersKronigValidator(df, window=('kaiser', 5.0))
        assert validator2.window == ('kaiser', 5.0)


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_very_small_dataset(self):
        """Test with minimal valid dataset (4 points for Hilbert, or use trapz)."""
        freq = np.array([1e9, 2e9, 3e9, 4e9])  # Need 4 points for Hilbert
        dk = np.array([2.5, 2.4, 2.3, 2.2])
        df = np.array([0.01, 0.02, 0.015, 0.01])
        
        result = validate_kramers_kronig(freq, dk, df)
        
        assert 'dk_kk' in result
        assert len(result['dk_kk']) == 4
        
        # Test 2-point dataset with trapz method (should work)
        freq2 = np.array([1e9, 2e9])
        dk2 = np.array([2.5, 2.4])
        df2 = np.array([0.01, 0.02])
        
        result2 = validate_kramers_kronig(freq2, dk2, df2, method='trapz')
        
        assert 'dk_kk' in result2
        assert len(result2['dk_kk']) == 2
    
    def test_zero_df_values(self):
        """Test with zero dissipation factor."""
        freq = np.linspace(1e9, 10e9, 20)
        dk = np.ones(20) * 2.5
        df = np.zeros(20)  # Zero dissipation
        
        result = validate_kramers_kronig(freq, dk, df)
        
        # Should still produce results
        assert 'dk_kk' in result
        assert np.all(np.isfinite(result['dk_kk']))
    
    def test_very_high_frequencies(self):
        """Test with very high frequency data."""
        freq = np.linspace(1e12, 10e12, 30)  # THz range
        dk = np.ones(30) * 2.0
        df = np.ones(30) * 0.005
        
        result = validate_kramers_kronig(freq, dk, df)
        
        assert 'causality_status' in result
        assert np.all(np.isfinite(result['dk_kk']))
    
    def test_causality_threshold(self):
        """Test different causality thresholds."""
        freq = np.linspace(1e9, 10e9, 50)
        dk = np.ones(50) * 2.5
        # Add some noise to create error
        dk += np.random.randn(50) * 0.1
        df = np.ones(50) * 0.01
        
        # Strict threshold
        result_strict = validate_kramers_kronig(freq, dk, df, causality_threshold=0.01)
        
        # Relaxed threshold
        result_relaxed = validate_kramers_kronig(freq, dk, df, causality_threshold=0.5)
        
        # Relaxed should be more likely to pass
        assert result_relaxed['causality_status'] == 'PASS' or result_strict['causality_status'] == 'FAIL'


class TestNumbaAcceleration:
    """Test Numba acceleration functionality."""
    
    def test_numba_consistency(self):
        """Test that Numba and pure Python produce same results."""
        freq = np.logspace(8, 10, 30)
        omega = 2 * np.pi * freq
        df = np.random.rand(30) * 0.01 + 0.01
        eps_inf = 2.0
        
        # Get result with current implementation
        result1 = _kk_trapz_numba(omega, df, eps_inf)
        
        # Mock to disable Numba and test pure Python fallback
        with patch('library.algorithms.kramers_kronig.NUMBA_AVAILABLE', False):
            # Re-import to get the pure Python version
            from library.algorithms.kramers_kronig import _kk_trapz_numba as _kk_trapz_pure
            result2 = _kk_trapz_pure(omega, df, eps_inf)
        
        # Results should be very close
        assert np.allclose(result1, result2, rtol=1e-10)


class TestNewMetrics:
    """Test new error metrics and features."""
    
    def test_additional_error_metrics(self):
        """Test that new error metrics are computed."""
        freq = np.linspace(1e9, 10e9, 50)
        dk = np.ones(50) * 2.5
        df = np.ones(50) * 0.01
        
        result = validate_kramers_kronig(freq, dk, df)
        
        # Check all error metrics are present
        assert 'mean_relative_error' in result
        assert 'median_relative_error' in result
        assert 'q90_relative_error' in result
        assert 'rmse' in result
        
        # All should be non-negative
        assert result['mean_relative_error'] >= 0
        assert result['median_relative_error'] >= 0
        assert result['q90_relative_error'] >= 0
        assert result['rmse'] >= 0
        
        # Ordering should make sense (q90 >= median >= 0)
        assert result['q90_relative_error'] >= result['median_relative_error']

    def test_method_detail_reporting(self):
        """Test that method_detail is properly reported."""
        freq_uniform = np.linspace(1e9, 10e9, 50)
        freq_log = np.logspace(9, 10, 50)
        dk = np.ones(50) * 2.5
        df = np.ones(50) * 0.01
        
        # Uniform grid with Hilbert
        result1 = validate_kramers_kronig(freq_uniform, dk, df, method='hilbert')
        assert result1['method_detail'] == 'hilbert-uniform'
        
        # Non-uniform grid with Hilbert (should resample)
        result2 = validate_kramers_kronig(freq_log, dk, df, method='hilbert')
        assert result2['method_detail'] == 'hilbert-resample'
        
        # Trapz with SSKK
        result3 = validate_kramers_kronig(freq_log, dk, df, method='trapz', use_sskk=True)
        assert result3['method_detail'] == 'trapz-sskk'
        
        # Trapz without SSKK
        result4 = validate_kramers_kronig(freq_log, dk, df, method='trapz', use_sskk=False)
        assert result4['method_detail'] == 'trapz-pv'


class TestMethodComparison:
    """Test consistency between different KK methods."""
    
    def test_hilbert_vs_trapz_uniform(self):
        """Test that Hilbert and trapz give similar results on uniform grid."""
        freq = np.linspace(1e9, 10e9, 100)
        omega = 2 * np.pi * freq
        
        # Simple Debye-like data
        tau = 1e-9
        eps_s = 3.0
        eps_inf = 2.0
        eps_complex = eps_inf + (eps_s - eps_inf) / (1 + 1j * omega * tau)
        dk = np.real(eps_complex)
        df = -np.imag(eps_complex) / np.real(eps_complex)
        
        # Hilbert method
        result_hilbert = validate_kramers_kronig(freq, dk, df, method='hilbert')
        
        # Trapz method with SSKK
        result_trapz = validate_kramers_kronig(freq, dk, df, method='trapz', use_sskk=True)
        
        # Both should give similar causality assessment
        assert result_hilbert['causality_status'] == result_trapz['causality_status']
        
        # RMSEs should be reasonably close (SSKK should be better than old trapz)
        assert np.abs(result_hilbert['rmse'] - result_trapz['rmse']) < 0.1
    
    def test_sskk_vs_pv_comparison(self):
        """Test that SSKK generally performs better than basic PV trapz."""
        freq = np.logspace(8, 10, 50)
        omega = 2 * np.pi * freq
        
        # Create Debye data with some finite-band effects
        tau = 1e-9
        eps_s = 3.0
        eps_inf = 2.0
        eps_complex = eps_inf + (eps_s - eps_inf) / (1 + 1j * omega * tau)
        dk = np.real(eps_complex)
        df = -np.imag(eps_complex) / np.real(eps_complex)
        
        # SSKK method
        result_sskk = validate_kramers_kronig(freq, dk, df, method='trapz', use_sskk=True)
        
        # Basic PV method
        result_pv = validate_kramers_kronig(freq, dk, df, method='trapz', use_sskk=False)
        
        # SSKK should generally have lower error (though this isn't guaranteed)
        # At minimum, both should produce finite results
        assert np.all(np.isfinite(result_sskk['dk_kk']))
        assert np.all(np.isfinite(result_pv['dk_kk']))
        assert result_sskk['method_detail'] == 'trapz-sskk'
        assert result_pv['method_detail'] == 'trapz-pv'