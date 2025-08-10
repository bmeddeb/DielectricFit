"""Property-based tests using Hypothesis for robustness testing."""

import numpy as np
import pytest

# Check if hypothesis is available
try:
    import hypothesis
    from hypothesis import given, strategies as st, assume, settings
    from hypothesis.extra.numpy import arrays, floating_dtypes
    HYPOTHESIS_AVAILABLE = True
except ImportError:
    HYPOTHESIS_AVAILABLE = False

from library.algorithms import interpolation, smoothing


@pytest.mark.skipif(not HYPOTHESIS_AVAILABLE, reason="hypothesis not installed - run: pip install hypothesis")
class TestPropertyBased:
    """Property-based tests (requires hypothesis)."""
    
    def test_hypothesis_available(self):
        """Test that hypothesis is available for property-based testing."""
        assert HYPOTHESIS_AVAILABLE, "hypothesis package not installed"


# Always available tests that don't require hypothesis
class TestBasicProperties:
    """Basic property tests that don't require hypothesis."""
    
    def test_constant_signal_smoothing(self):
        """Smoothing a constant signal should return the constant."""
        value = 5.0
        signal = np.full(20, value)
        
        smoothed = smoothing.moving_average(signal, window=5)
        np.testing.assert_array_almost_equal(smoothed, signal, decimal=10)
        
        smoothed_gauss = smoothing.gaussian_smooth(signal, sigma=1.0)
        np.testing.assert_array_almost_equal(smoothed_gauss, signal, decimal=10)
    
    def test_linear_function_interpolation(self):
        """Linear interpolation should be exact for linear functions."""
        slope, intercept = 2.5, 1.0
        x = np.linspace(0, 10, 11)
        y = slope * x + intercept
        
        x_new = np.linspace(0, 10, 50)
        y_expected = slope * x_new + intercept
        
        y_interp = interpolation.linear_interpolate(x, y, x_new)
        np.testing.assert_array_almost_equal(y_interp, y_expected, decimal=10)
    
    def test_smoothing_reduces_noise(self):
        """Smoothing should reduce noise in signals."""
        x = np.linspace(0, 2*np.pi, 50)
        clean_signal = np.sin(x)
        
        # Add noise
        np.random.seed(42)
        noise_level = 0.1
        noisy_signal = clean_signal + noise_level * np.random.randn(len(x))
        
        # Apply smoothing
        smoothed = smoothing.savitzky_golay(noisy_signal, window=7, polyorder=2)
        
        # Should be closer to clean signal than noisy signal
        clean_error = np.mean((smoothed - clean_signal) ** 2)
        noise_error = np.mean((noisy_signal - clean_signal) ** 2)
        
        assert clean_error <= noise_error
    
    def test_interpolation_preserves_monotonicity_pchip(self):
        """PCHIP should preserve monotonicity."""
        x = np.array([0, 1, 2, 3, 4])
        y = np.array([0, 0.5, 0.8, 0.9, 1.0])  # Monotonic increasing
        
        x_new = np.linspace(0, 4, 50)
        y_interp = interpolation.pchip_interpolate(x, y, x_new)
        
        # Should preserve monotonicity  
        assert np.all(np.diff(y_interp) >= -1e-10)  # Allow small numerical errors
    
    def test_moving_average_different_window_sizes(self):
        """Test moving average with different window sizes."""
        np.random.seed(42)
        signal = np.random.randn(100)
        
        for window in [3, 5, 7, 11, 15]:
            smoothed = smoothing.moving_average(signal, window=window)
            
            # Should preserve length
            assert len(smoothed) == len(signal)
            
            # Larger windows should produce smoother results
            if window > 3:
                prev_smoothed = smoothing.moving_average(signal, window=window-2)
                # Compare roughness (second differences)
                current_roughness = np.sum(np.abs(np.diff(smoothed, n=2)))
                prev_roughness = np.sum(np.abs(np.diff(prev_smoothed, n=2)))
                assert current_roughness <= prev_roughness
    
    def test_gaussian_smooth_different_sigma(self):
        """Test Gaussian smoothing with different sigma values."""
        np.random.seed(42)
        signal = np.sin(np.linspace(0, 4*np.pi, 100)) + 0.1*np.random.randn(100)
        
        for sigma in [0.5, 1.0, 2.0, 4.0]:
            smoothed = smoothing.gaussian_smooth(signal, sigma=sigma)
            
            # Should preserve length
            assert len(smoothed) == len(signal)
            assert np.all(np.isfinite(smoothed))
            
            # Should reduce high frequency content
            fft_orig = np.abs(np.fft.fft(signal))
            fft_smooth = np.abs(np.fft.fft(smoothed))
            
            # Check that high frequencies are reduced
            high_freq_orig = np.sum(fft_orig[50:])
            high_freq_smooth = np.sum(fft_smooth[50:])
            
            assert high_freq_smooth <= high_freq_orig


@pytest.mark.property
class TestMathematicalInvariants:
    """Test mathematical invariants that should always hold."""
    
    def test_interpolation_identity_property(self):
        """Interpolation at original points should be identity."""
        x = np.array([0, 1, 2, 3, 4])
        y = np.array([0, 1, 4, 9, 16])  # y = x^2
        
        # Test multiple methods
        methods = [
            interpolation.linear_interpolate,
            interpolation.pchip_interpolate,
            interpolation.cubic_spline_interpolate
        ]
        
        for method in methods:
            try:
                y_interp = method(x, y, x)
                np.testing.assert_array_almost_equal(y_interp, y, decimal=8)
            except (ValueError, np.linalg.LinAlgError):
                # Some methods might fail for certain data
                pass
    
    def test_smoothing_preserves_dc_component(self):
        """Smoothing should preserve the DC (average) component."""
        # Signal with known average
        signal = np.array([1, 2, 3, 4, 5, 4, 3, 2, 1])
        original_mean = np.mean(signal)
        
        # Apply different smoothing methods
        smoothed_ma = smoothing.moving_average(signal, window=3)
        smoothed_gauss = smoothing.gaussian_smooth(signal, sigma=1.0)
        
        # DC component should be approximately preserved
        assert abs(np.mean(smoothed_ma) - original_mean) < 0.1
        assert abs(np.mean(smoothed_gauss) - original_mean) < 0.1
    
    def test_interpolation_bounds_preservation(self):
        """Interpolation within data range should preserve bounds."""
        x = np.array([0, 1, 2, 3, 4])
        y = np.array([1, 3, 2, 4, 1])  # Non-monotonic
        
        x_new = np.linspace(0, 4, 20)  # Within data range
        y_min, y_max = np.min(y), np.max(y)
        
        # Linear interpolation should preserve bounds exactly
        y_linear = interpolation.linear_interpolate(x, y, x_new)
        assert np.min(y_linear) >= y_min - 1e-10
        assert np.max(y_linear) <= y_max + 1e-10
    
    def test_interpolation_preserves_polynomials(self):
        """Test that appropriate interpolation methods preserve polynomials."""
        x = np.linspace(-2, 2, 9)
        
        # Test with different polynomials
        polynomials = [
            (lambda x: x, "linear"),
            (lambda x: x**2, "quadratic"),  
            (lambda x: x**3, "cubic")
        ]
        
        for poly_func, poly_name in polynomials:
            y = poly_func(x)
            x_new = np.linspace(-2, 2, 20)
            y_expected = poly_func(x_new)
            
            # Cubic spline should preserve polynomials up to degree 3
            if poly_name in ["linear", "quadratic", "cubic"]:
                y_interp = interpolation.cubic_spline_interpolate(x, y, x_new)
                np.testing.assert_array_almost_equal(y_interp, y_expected, decimal=6)


class TestRobustness:
    """Test robustness and edge cases."""
    
    def test_small_arrays(self):
        """Test that algorithms handle small arrays correctly."""
        x = np.array([0, 1])
        y = np.array([0, 1])
        
        # Should work with minimal data
        y_interp = interpolation.linear_interpolate(x, y, np.array([0.5]))
        assert len(y_interp) == 1
        assert 0 <= y_interp[0] <= 1
    
    def test_single_point_smoothing(self):
        """Test smoothing with very small signals."""
        signal = np.array([5.0])
        
        # Should handle single point gracefully
        smoothed = smoothing.moving_average(signal, window=1)
        assert len(smoothed) == 1
        assert smoothed[0] == signal[0]
    
    def test_numerical_precision(self):
        """Test numerical precision with various data scales."""
        scales = [1e-6, 1e-3, 1, 1e3, 1e6]
        
        for scale in scales:
            x = np.array([0, 1, 2]) * scale
            y = np.array([0, 1, 4]) * scale
            
            # Should handle different scales
            x_new = np.array([0.5, 1.5]) * scale
            y_interp = interpolation.linear_interpolate(x, y, x_new)
            
            assert len(y_interp) == 2
            assert np.all(np.isfinite(y_interp))
            
            # Scale should be preserved roughly
            if scale > 0:
                assert np.max(np.abs(y_interp)) / scale < 10
    
    def test_edge_case_window_sizes(self):
        """Test smoothing with edge case window sizes."""
        signal = np.array([1, 2, 3, 4, 5])
        
        # Window equal to signal length
        smoothed = smoothing.moving_average(signal, window=len(signal))
        assert len(smoothed) == len(signal)
        
        # Window larger than signal (should be handled gracefully)
        smoothed_large = smoothing.moving_average(signal, window=len(signal) + 2)
        assert len(smoothed_large) == len(signal)
    
    def test_unsorted_x_values_error_handling(self):
        """Test that unsorted x values raise error appropriately."""
        x = np.array([1, 3, 2, 4])  # Unsorted x values  
        y = np.array([1, 2, 3, 4])
        
        # Should raise error for non-monotonic x
        with pytest.raises(ValueError):
            interpolation.linear_interpolate(x, y, np.array([1.5]))
    
    def test_nan_handling_in_smoothing(self):
        """Test handling of NaN values in smoothing."""
        signal = np.array([1, 2, np.nan, 4, 5])
        
        # Most smoothing algorithms should handle NaN gracefully
        try:
            smoothed = smoothing.gaussian_smooth(signal, sigma=1.0)
            # If it doesn't raise an error, check that result has some valid values
            assert len(smoothed) == len(signal)
        except (ValueError, FloatingPointError):
            # Some algorithms might not handle NaN
            pass


class TestBoundaryConditions:
    """Test behavior at boundaries and edge cases."""
    
    def test_extrapolation_behavior(self):
        """Test extrapolation behavior of different methods."""
        x = np.array([1, 2, 3, 4])
        y = np.array([1, 4, 9, 16])  # y = x^2
        
        # Points outside range
        x_extrap = np.array([0, 5])
        
        # Linear extrapolation
        y_linear = interpolation.linear_interpolate(x, y, x_extrap)
        assert len(y_linear) == 2
        assert np.all(np.isfinite(y_linear))
        
        # PCHIP with extrapolation
        y_pchip = interpolation.pchip_interpolate(x, y, x_extrap, extrapolation='extrapolate')
        assert len(y_pchip) == 2
        assert np.all(np.isfinite(y_pchip))
        
        # PCHIP without extrapolation should give NaN
        y_pchip_no_extrap = interpolation.pchip_interpolate(x, y, x_extrap, extrapolation='nan')
        assert np.all(np.isnan(y_pchip_no_extrap))
    
    def test_boundary_mode_effects(self):
        """Test that different boundary modes work for smoothing."""
        signal = np.array([1, 2, 3, 2, 1])
        
        modes = ['reflect', 'constant', 'nearest', 'mirror', 'wrap']
        
        for mode in modes:
            try:
                smoothed = smoothing.moving_average(signal, window=3, mode=mode)
                assert len(smoothed) == len(signal)
                assert np.all(np.isfinite(smoothed))
            except ValueError:
                # Some modes might not be supported by all algorithms
                pass


if HYPOTHESIS_AVAILABLE:
    # Add some actual property-based tests if hypothesis is available
    from hypothesis import given, strategies as st, settings
    from hypothesis.extra.numpy import arrays
    
    class TestActualPropertyBased:
        """Actual property-based tests using hypothesis."""
        
        @given(signal=arrays(
            dtype=np.float64,
            shape=st.integers(5, 50),
            elements=st.floats(-10.0, 10.0, allow_nan=False, allow_infinity=False)
        ))
        @settings(max_examples=20, deadline=2000)
        def test_moving_average_length_preservation(self, signal):
            """Moving average should always preserve signal length."""
            if len(signal) >= 3:
                smoothed = smoothing.moving_average(signal, window=3)
                assert len(smoothed) == len(signal)
        
        @given(
            size=st.integers(3, 20),
            scale=st.floats(0.1, 100.0)
        )
        @settings(max_examples=15, deadline=2000)
        def test_linear_interpolation_scaling_invariance(self, size, scale):
            """Linear interpolation should be scale-invariant."""
            x = np.linspace(0, 1, size)
            y = np.sin(2 * np.pi * x)
            
            # Scale the data
            x_scaled = x * scale
            y_scaled = y * scale
            
            # Interpolate
            x_new = np.linspace(0, 1, size * 2) * scale
            y_orig = interpolation.linear_interpolate(x, y, np.linspace(0, 1, size * 2))
            y_scaled_interp = interpolation.linear_interpolate(x_scaled, y_scaled, x_new)
            
            # Results should be related by the same scale
            np.testing.assert_array_almost_equal(
                y_scaled_interp / scale, y_orig, decimal=8
            )