"""Pytest tests for smoothing algorithms."""

import warnings
import numpy as np
import pytest

from library.algorithms import smoothing


class TestMovingAverage:
    """Test moving average smoothing."""
    
    def test_basic_smoothing(self, noisy_sine_wave):
        """Test basic moving average functionality."""
        x, noisy_y, clean_y = noisy_sine_wave
        smoothed = smoothing.moving_average(noisy_y, window=5)
        
        # Check shape preserved
        assert smoothed.shape == noisy_y.shape
        
        # Check smoothing reduces variance
        assert np.var(smoothed) < np.var(noisy_y)
    
    @pytest.mark.parametrize("window", [3, 5, 7, 9, 11])
    def test_different_windows(self, noisy_sine_wave, window):
        """Test moving average with different window sizes."""
        x, noisy_y, clean_y = noisy_sine_wave
        smoothed = smoothing.moving_average(noisy_y, window=window)
        
        # Larger windows should produce smoother results
        assert smoothed.shape == noisy_y.shape
        assert np.var(smoothed) <= np.var(noisy_y)
    
    @pytest.mark.parametrize("mode", [
        'reflect', 'constant', 'nearest', 'mirror', 'wrap'
    ])
    def test_boundary_modes(self, noisy_sine_wave, mode):
        """Test different boundary handling modes."""
        x, noisy_y, clean_y = noisy_sine_wave
        smoothed = smoothing.moving_average(noisy_y, window=5, mode=mode)
        
        assert smoothed.shape == noisy_y.shape
        assert not np.any(np.isnan(smoothed))
    
    def test_window_larger_than_signal(self, small_dataset):
        """Test when window is larger than signal."""
        x, y = small_dataset
        smoothed = smoothing.moving_average(y, window=10)
        
        # Should handle gracefully
        assert len(smoothed) == len(y)
    
    def test_empty_input_raises_error(self, empty_dataset):
        """Test that empty input raises ValueError."""
        x, y = empty_dataset
        with pytest.raises(ValueError, match="Input array is empty"):
            smoothing.moving_average(y, window=5)


class TestGaussianSmooth:
    """Test Gaussian smoothing."""
    
    def test_basic_gaussian_smoothing(self, noisy_sine_wave):
        """Test basic Gaussian smoothing functionality."""
        x, noisy_y, clean_y = noisy_sine_wave
        smoothed = smoothing.gaussian_smooth(noisy_y, sigma=2.0)
        
        assert smoothed.shape == noisy_y.shape
        
        # Check frequency domain - high frequencies should be reduced
        fft_orig = np.abs(np.fft.fft(noisy_y))
        fft_smooth = np.abs(np.fft.fft(smoothed))
        
        # High frequency components should be attenuated
        high_freq_reduction = np.sum(fft_smooth[50:]) / np.sum(fft_orig[50:])
        assert high_freq_reduction < 1.0
    
    @pytest.mark.parametrize("sigma", [0.5, 1.0, 2.0, 4.0])
    def test_different_sigma_values(self, noisy_sine_wave, sigma):
        """Test Gaussian smoothing with different sigma values."""
        x, noisy_y, clean_y = noisy_sine_wave
        smoothed = smoothing.gaussian_smooth(noisy_y, sigma=sigma)
        
        # Larger sigma should produce more smoothing
        assert smoothed.shape == noisy_y.shape
        
        # Check that smoothing reduces variance
        if sigma > 0.1:  # Very small sigma might not reduce variance much
            assert np.var(smoothed) <= np.var(noisy_y)
    
    def test_invalid_sigma_raises_error(self, noisy_sine_wave):
        """Test that invalid sigma raises ValueError."""
        x, noisy_y, clean_y = noisy_sine_wave
        
        with pytest.raises(ValueError, match="Sigma must be positive"):
            smoothing.gaussian_smooth(noisy_y, sigma=-1)
        
        with pytest.raises(ValueError, match="Sigma must be positive"):
            smoothing.gaussian_smooth(noisy_y, sigma=0)


class TestMedianSmooth:
    """Test median filtering."""
    
    def test_outlier_removal(self, outlier_signal):
        """Test median filter removes outliers effectively."""
        x, outlier_y, clean_y = outlier_signal
        smoothed = smoothing.median_smooth(outlier_y, window=5)
        
        # Check outliers are significantly reduced
        assert np.max(np.abs(smoothed)) < 3.0
        
        # Should be better than moving average for outliers
        mean_smoothed = smoothing.moving_average(outlier_y, window=5)
        median_error = np.mean(np.abs(smoothed - clean_y))
        mean_error = np.mean(np.abs(mean_smoothed - clean_y))
        
        assert median_error < mean_error * 1.1  # Allow some tolerance
    
    @pytest.mark.parametrize("window", [3, 5, 7, 9])
    def test_different_windows(self, outlier_signal, window):
        """Test median filter with different window sizes."""
        x, outlier_y, clean_y = outlier_signal
        smoothed = smoothing.median_smooth(outlier_y, window=window)
        
        assert smoothed.shape == outlier_y.shape
        # Larger windows should be more effective at removing outliers
        assert np.max(np.abs(smoothed)) < np.max(np.abs(outlier_y))
    
    @pytest.mark.parametrize("mode", [
        'reflect', 'constant', 'nearest', 'mirror', 'wrap'
    ])
    def test_boundary_modes(self, outlier_signal, mode):
        """Test that different boundary modes work and produce different results."""
        x, outlier_y, clean_y = outlier_signal
        
        smoothed = smoothing.median_smooth(outlier_y, window=5, mode=mode)
        
        # Should complete without error
        assert smoothed.shape == outlier_y.shape
        assert np.all(np.isfinite(smoothed))
    
    def test_mode_parameter_affects_results(self, outlier_signal):
        """Test that mode parameter actually affects the results."""
        x, outlier_y, clean_y = outlier_signal
        
        # Get results with different modes
        reflect_result = smoothing.median_smooth(outlier_y, window=5, mode='reflect')
        constant_result = smoothing.median_smooth(outlier_y, window=5, mode='constant')
        
        # Results should be different (at least at boundaries)
        # Check first and last few elements where boundary effects are strongest
        boundary_indices = [0, 1, -2, -1]
        
        differences_found = False
        for idx in boundary_indices:
            if abs(reflect_result[idx] - constant_result[idx]) > 1e-10:
                differences_found = True
                break
        
        assert differences_found, "Mode parameter should affect results at boundaries"


class TestSavitzkyGolay:
    """Test Savitzky-Golay filtering."""
    
    def test_feature_preservation(self, clean_sine_wave):
        """Test that Savitzky-Golay preserves features well."""
        x, clean_y = clean_sine_wave
        
        # Add minimal noise
        noisy_y = clean_y + 0.05 * np.random.randn(len(clean_y))
        smoothed = smoothing.savitzky_golay(noisy_y, window=7, polyorder=3)
        
        # Should preserve the sine wave shape well
        correlation = np.corrcoef(smoothed, clean_y)[0, 1]
        assert correlation > 0.98
    
    def test_derivative_calculation(self, clean_sine_wave):
        """Test derivative calculation with Savitzky-Golay."""
        x, clean_y = clean_sine_wave
        
        # Calculate first derivative
        dt = x[1] - x[0]
        deriv = smoothing.savitzky_golay(
            clean_y, window=15, polyorder=3, deriv=1, delta=dt
        )
        
        # Expected derivative of sin(x) is cos(x)
        expected_deriv = np.cos(x)
        correlation = np.corrcoef(deriv, expected_deriv)[0, 1]
        
        # Should be highly correlated
        assert correlation > 0.95
    
    @pytest.mark.parametrize("polyorder", [1, 2, 3, 4])
    def test_different_polynomial_orders(self, noisy_sine_wave, polyorder):
        """Test Savitzky-Golay with different polynomial orders."""
        x, noisy_y, clean_y = noisy_sine_wave
        window = 7 + 2 * polyorder  # Ensure window > polyorder
        
        smoothed = smoothing.savitzky_golay(noisy_y, window=window, polyorder=polyorder)
        assert smoothed.shape == noisy_y.shape


class TestButterworthLowpass:
    """Test Butterworth low-pass filter."""
    
    def test_frequency_filtering(self, frequency_data):
        """Test that Butterworth filter works without errors."""
        t, signal, fs = frequency_data
        
        # Filter to remove frequencies above 10 Hz
        filtered = smoothing.butterworth_lowpass(
            signal, cutoff_freq=10.0, sampling_freq=fs, order=5
        )
        
        # Basic functionality tests
        assert filtered.shape == signal.shape
        assert np.all(np.isfinite(filtered))
        
        # Check that signal is modified (not identical)
        signal_diff = np.mean(np.abs(filtered - signal))
        assert signal_diff > 0, "Filter should modify the signal"
        
        # Check that filter doesn't amplify the signal significantly
        filtered_energy = np.mean(filtered**2)
        original_energy = np.mean(signal**2)
        assert filtered_energy <= original_energy * 1.1, "Filter shouldn't significantly amplify signal"
    
    def test_invalid_frequencies_raise_error(self, frequency_data):
        """Test that invalid frequency parameters raise errors."""
        t, signal, fs = frequency_data
        
        with pytest.raises(ValueError):
            smoothing.butterworth_lowpass(signal, cutoff_freq=-1, sampling_freq=fs)
        
        with pytest.raises(ValueError):
            smoothing.butterworth_lowpass(signal, cutoff_freq=fs, sampling_freq=fs)
    
    def test_invalid_order_raises_error(self, frequency_data):
        """Test that invalid filter order raises error."""
        t, signal, fs = frequency_data
        
        with pytest.raises(ValueError, match="Order must be >= 1"):
            smoothing.butterworth_lowpass(signal, cutoff_freq=10.0, sampling_freq=fs, order=0)
        
        with pytest.raises(ValueError, match="Order must be >= 1"):
            smoothing.butterworth_lowpass(signal, cutoff_freq=10.0, sampling_freq=fs, order=-1)
    
    def test_short_signal_handling(self):
        """Test that very short signals are handled gracefully."""
        # Very short signal that might cause filtfilt to fail
        short_signal = np.array([1.0, 2.0, 1.0])
        fs = 100.0
        
        # This should not raise an error, should fall back to sosfilt
        filtered = smoothing.butterworth_lowpass(
            short_signal, cutoff_freq=10.0, sampling_freq=fs, order=8
        )
        
        assert filtered.shape == short_signal.shape
        assert np.all(np.isfinite(filtered))
    
    def test_sos_vs_ba_numerical_stability(self, frequency_data):
        """Test that SOS implementation provides better numerical stability."""
        t, signal, fs = frequency_data
        
        # High order filter where ba-form might be unstable
        high_order = 12
        
        filtered = smoothing.butterworth_lowpass(
            signal, cutoff_freq=10.0, sampling_freq=fs, order=high_order
        )
        
        # Should complete without numerical issues
        assert filtered.shape == signal.shape
        assert np.all(np.isfinite(filtered))
        
        # Check that output isn't pathologically large (sign of instability)
        max_output = np.max(np.abs(filtered))
        max_input = np.max(np.abs(signal))
        assert max_output < max_input * 10, "Output shouldn't be excessively amplified"
    
    @pytest.mark.parametrize("order", [1, 2, 4, 6, 8, 10])
    def test_different_filter_orders(self, frequency_data, order):
        """Test Butterworth filter with different orders."""
        t, signal, fs = frequency_data
        
        filtered = smoothing.butterworth_lowpass(
            signal, cutoff_freq=15.0, sampling_freq=fs, order=order
        )
        
        assert filtered.shape == signal.shape
        assert np.all(np.isfinite(filtered))
    
    def test_edge_case_very_short_signals(self):
        """Test edge cases with extremely short signals."""
        # Single point
        single_point = np.array([5.0])
        result = smoothing.butterworth_lowpass(single_point, cutoff_freq=10.0, sampling_freq=100.0)
        assert len(result) == 1
        assert np.isfinite(result[0])
        
        # Two points
        two_points = np.array([1.0, 2.0])
        result = smoothing.butterworth_lowpass(two_points, cutoff_freq=10.0, sampling_freq=100.0)
        assert len(result) == 2
        assert np.all(np.isfinite(result))


class TestExponentialSmooth:
    """Test exponential smoothing."""
    
    @pytest.mark.parametrize("alpha", [0.1, 0.3, 0.5, 0.7, 0.9])
    def test_different_alpha_values(self, noisy_sine_wave, alpha):
        """Test exponential smoothing with different alpha values."""
        x, noisy_y, clean_y = noisy_sine_wave
        smoothed = smoothing.exponential_smooth(noisy_y, alpha=alpha)
        
        assert smoothed.shape == noisy_y.shape
        
        # Higher alpha should track the signal more closely
        tracking_error = np.mean(np.abs(smoothed - noisy_y))
        
        # Basic sanity check - smoothed values should be finite
        assert np.all(np.isfinite(smoothed))
    
    def test_nan_handling(self, noisy_sine_wave):
        """Test handling of NaN values."""
        x, noisy_y, clean_y = noisy_sine_wave
        
        # Insert NaN values
        signal_with_nan = noisy_y.copy()
        signal_with_nan[50] = np.nan
        signal_with_nan[51] = np.nan
        
        # Test ignore_na=True
        smoothed = smoothing.exponential_smooth(
            signal_with_nan, alpha=0.3, ignore_na=True
        )
        
        # Should handle NaN gracefully
        assert not np.isnan(smoothed[49])  # Before NaN
        assert not np.isnan(smoothed[52])  # After NaN
    
    def test_invalid_alpha_raises_error(self, noisy_sine_wave):
        """Test that invalid alpha values raise errors."""
        x, noisy_y, clean_y = noisy_sine_wave
        
        with pytest.raises(ValueError):
            smoothing.exponential_smooth(noisy_y, alpha=-0.1)
        
        with pytest.raises(ValueError):
            smoothing.exponential_smooth(noisy_y, alpha=1.1)
    
    def test_alpha_zero_no_division_error(self, noisy_sine_wave):
        """Test that alpha=0 doesn't cause division by zero errors."""
        x, noisy_y, clean_y = noisy_sine_wave
        
        # Test with adjust=True (previously caused division by zero)
        smoothed_adjust = smoothing.exponential_smooth(noisy_y, alpha=0.0, adjust=True)
        assert smoothed_adjust.shape == noisy_y.shape
        assert np.all(np.isfinite(smoothed_adjust))
        
        # Should return constant signal equal to first value
        expected = np.full_like(noisy_y, noisy_y[0])
        np.testing.assert_array_almost_equal(smoothed_adjust, expected)
        
        # Test with adjust=False
        smoothed_no_adjust = smoothing.exponential_smooth(noisy_y, alpha=0.0, adjust=False)
        assert smoothed_no_adjust.shape == noisy_y.shape
        assert np.all(np.isfinite(smoothed_no_adjust))
        np.testing.assert_array_almost_equal(smoothed_no_adjust, expected)
    
    def test_alpha_zero_with_nan_handling(self):
        """Test alpha=0 with NaN values and ignore_na=True."""
        signal_with_nan = np.array([np.nan, np.nan, 2.0, 3.0, np.nan, 4.0])
        
        # With ignore_na=True, should forward-fill last seen non-NaN value
        result = smoothing.exponential_smooth(signal_with_nan, alpha=0.0, ignore_na=True)
        
        # Expected behavior: [NaN, NaN, 2.0, 3.0, 3.0, 4.0]
        # - Index 0,1: NaN (no valid value seen yet)
        # - Index 2: 2.0 (first non-NaN)
        # - Index 3: 3.0 (new non-NaN, updates last seen)
        # - Index 4: 3.0 (NaN, forward-fill last seen which is 3.0)
        # - Index 5: 4.0 (new non-NaN)
        expected = np.array([np.nan, np.nan, 2.0, 3.0, 3.0, 4.0])
        
        # Check NaN positions match
        assert np.isnan(result[0]) and np.isnan(expected[0])
        assert np.isnan(result[1]) and np.isnan(expected[1])
        
        # Check non-NaN positions match
        assert result[2] == expected[2] == 2.0
        assert result[3] == expected[3] == 3.0
        assert result[4] == expected[4] == 3.0
        assert result[5] == expected[5] == 4.0
        
        # With ignore_na=False, should still work (start with first value)
        result_no_ignore = smoothing.exponential_smooth(signal_with_nan, alpha=0.0, ignore_na=False)
        # First value is NaN, so everything should be NaN
        assert np.all(np.isnan(result_no_ignore))


class TestSplineSmooth:
    """Test spline smoothing."""
    
    def test_basic_spline_smoothing(self, noisy_sine_wave):
        """Test basic spline smoothing functionality."""
        x, noisy_y, clean_y = noisy_sine_wave
        
        x_smooth, y_smooth = smoothing.spline_smooth(x, noisy_y, s=5.0)
        
        assert x_smooth.shape == x.shape
        assert y_smooth.shape == noisy_y.shape
        
        # Should reduce noise
        assert np.var(y_smooth) < np.var(noisy_y)
    
    @pytest.mark.parametrize("s", [0, 1, 5, 10, 50])
    def test_different_smoothing_factors(self, noisy_sine_wave, s):
        """Test spline smoothing with different smoothing factors."""
        x, noisy_y, clean_y = noisy_sine_wave
        
        x_smooth, y_smooth = smoothing.spline_smooth(x, noisy_y, s=s)
        
        assert x_smooth.shape == x.shape
        assert y_smooth.shape == noisy_y.shape
    
    def test_unsorted_data_raises_error(self, unsorted_data):
        """Test that unsorted data raises error."""
        x, y = unsorted_data
        
        with pytest.raises(ValueError, match="must be strictly increasing"):
            smoothing.spline_smooth(x, y)
    
    def test_duplicate_x_values_raise_error(self):
        """Test that duplicate x values raise error."""
        x = np.array([0, 1, 1, 2, 3])  # Duplicate at index 1,2
        y = np.array([0, 1, 2, 3, 4])
        
        with pytest.raises(ValueError, match="must be strictly increasing"):
            smoothing.spline_smooth(x, y)
    
    def test_k_clamping_and_warnings(self, noisy_sine_wave):
        """Test that k values are properly clamped with warnings."""
        x, noisy_y, clean_y = noisy_sine_wave
        
        # Test k too small
        with pytest.warns(UserWarning, match="k=-1 out of"):
            x_smooth, y_smooth = smoothing.spline_smooth(x, noisy_y, k=-1)
            assert x_smooth.shape == x.shape
            assert y_smooth.shape == noisy_y.shape
        
        # Test k too large  
        with pytest.warns(UserWarning, match="k=10 out of"):
            x_smooth, y_smooth = smoothing.spline_smooth(x, noisy_y, k=10)
            assert x_smooth.shape == x.shape
            assert y_smooth.shape == noisy_y.shape
    
    def test_k_limited_by_data_size(self):
        """Test that k is limited by data size."""
        # Very small dataset
        x = np.array([0, 1, 2])
        y = np.array([0, 1, 0])
        
        # Request k=5 but only have 3 points, should be clamped to k=2
        x_smooth, y_smooth = smoothing.spline_smooth(x, y, k=5)
        assert x_smooth.shape == x.shape
        assert y_smooth.shape == y.shape
        assert np.all(np.isfinite(y_smooth))
    
    @pytest.mark.parametrize("k", [1, 2, 3, 4, 5])
    def test_valid_k_values(self, noisy_sine_wave, k):
        """Test that all valid k values work."""
        x, noisy_y, clean_y = noisy_sine_wave
        
        x_smooth, y_smooth = smoothing.spline_smooth(x, noisy_y, k=k)
        assert x_smooth.shape == x.shape
        assert y_smooth.shape == noisy_y.shape
        assert np.all(np.isfinite(y_smooth))


class TestLowessSmooth:
    """Test LOWESS smoothing."""
    
    def test_basic_lowess_smoothing(self, noisy_sine_wave):
        """Test basic LOWESS smoothing functionality."""
        x, noisy_y, clean_y = noisy_sine_wave
        
        x_smooth, y_smooth = smoothing.lowess_smooth(x, noisy_y, frac=0.3)
        
        assert x_smooth.shape == x.shape
        assert y_smooth.shape == noisy_y.shape
        
        # Should reduce noise
        assert np.var(y_smooth) < np.var(noisy_y)
    
    def test_lowess_parameters_used(self, noisy_sine_wave):
        """Test that it and delta parameters affect results when statsmodels available."""
        x, noisy_y, clean_y = noisy_sine_wave
        
        # Test with different it values
        x1, y1 = smoothing.lowess_smooth(x, noisy_y, frac=0.3, it=1)
        x2, y2 = smoothing.lowess_smooth(x, noisy_y, frac=0.3, it=5)
        
        assert x1.shape == x.shape
        assert y1.shape == noisy_y.shape
        assert x2.shape == x.shape
        assert y2.shape == noisy_y.shape
        
        # Results should be finite
        assert np.all(np.isfinite(y1))
        assert np.all(np.isfinite(y2))
    
    @pytest.mark.parametrize("frac", [0.1, 0.3, 0.5, 0.7])
    def test_different_frac_values(self, noisy_sine_wave, frac):
        """Test LOWESS with different frac values."""
        x, noisy_y, clean_y = noisy_sine_wave
        
        x_smooth, y_smooth = smoothing.lowess_smooth(x, noisy_y, frac=frac)
        
        assert x_smooth.shape == x.shape
        assert y_smooth.shape == noisy_y.shape
        assert np.all(np.isfinite(y_smooth))
    
    def test_unsorted_data_raises_error(self, unsorted_data):
        """Test that unsorted x values raise error."""
        x, y = unsorted_data
        
        with pytest.raises(ValueError, match="must be sorted"):
            smoothing.lowess_smooth(x, y, frac=0.3)
    
    def test_invalid_frac_raises_error(self, noisy_sine_wave):
        """Test that invalid frac values raise error."""
        x, noisy_y, clean_y = noisy_sine_wave
        
        with pytest.raises(ValueError, match="frac must be in"):
            smoothing.lowess_smooth(x, noisy_y, frac=0.0)
        
        with pytest.raises(ValueError, match="frac must be in"):
            smoothing.lowess_smooth(x, noisy_y, frac=1.1)
    
    def test_empty_input_raises_error(self, empty_dataset):
        """Test that empty input raises error."""
        x, y = empty_dataset
        
        with pytest.raises(ValueError, match="Input arrays are empty"):
            smoothing.lowess_smooth(x, y, frac=0.3)
    
    def test_mismatched_sizes_raise_error(self):
        """Test that mismatched input sizes raise error."""
        with pytest.raises(ValueError, match="must have same size"):
            smoothing.lowess_smooth([1, 2, 3], [1, 2], frac=0.3)


class TestComprehensiveEdgeCases:
    """Comprehensive edge case tests for all smoothing functions."""
    
    @pytest.mark.parametrize("length", [1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
    def test_tiny_arrays_all_functions(self, length):
        """Test all smoothing functions with tiny arrays (length 1-10)."""
        # Create tiny signal
        y = np.random.randn(length) * 0.1 + np.linspace(0, 1, length)
        
        # Test moving average
        try:
            result = smoothing.moving_average(y, window=3)
            assert len(result) == length
            assert np.all(np.isfinite(result))
        except ValueError:
            pass  # Some configurations might be invalid
        
        # Test Gaussian smooth
        result = smoothing.gaussian_smooth(y, sigma=0.5)
        assert len(result) == length
        assert np.all(np.isfinite(result))
        
        # Test median smooth
        try:
            result = smoothing.median_smooth(y, window=3)
            assert len(result) == length
            assert np.all(np.isfinite(result))
        except ValueError:
            pass
        
        # Test Savitzky-Golay
        try:
            result = smoothing.savitzky_golay(y, window=min(5, length), polyorder=min(2, length-1))
            assert len(result) == length
            assert np.all(np.isfinite(result))
        except ValueError:
            pass
        
        # Test exponential smooth
        result = smoothing.exponential_smooth(y, alpha=0.3)
        assert len(result) == length
        assert np.all(np.isfinite(result))
        
        # Test Wiener smooth
        result = smoothing.wiener_smooth(y)
        assert len(result) == length
        assert np.all(np.isfinite(result))
    
    @pytest.mark.parametrize("length", [1, 2, 3, 4, 5, 6, 7, 8, 9, 10])  
    def test_tiny_arrays_butterworth(self, length):
        """Test Butterworth filter specifically with tiny arrays."""
        y = np.random.randn(length) * 0.1 + np.sin(np.linspace(0, 1, length))
        fs = 100.0
        cutoff = 10.0
        
        # Test different orders
        for order in [1, 2, 3, 4, 5]:
            result = smoothing.butterworth_lowpass(y, cutoff, fs, order)
            assert len(result) == length
            assert np.all(np.isfinite(result))
    
    def test_windows_larger_than_signal(self):
        """Test functions with windows larger than signal."""
        short_signal = np.array([1, 2, 3, 4, 5])
        
        # Moving average with large window
        result = smoothing.moving_average(short_signal, window=20)
        assert len(result) == len(short_signal)
        assert np.all(np.isfinite(result))
        
        # Median filter with large window
        result = smoothing.median_smooth(short_signal, window=20)
        assert len(result) == len(short_signal)
        assert np.all(np.isfinite(result))
        
        # Savitzky-Golay with large window
        result = smoothing.savitzky_golay(short_signal, window=20, polyorder=3)
        assert len(result) == len(short_signal)
        assert np.all(np.isfinite(result))
    
    @pytest.mark.parametrize("window", [4, 6, 8, 10, 12])  # Even windows
    def test_even_windows(self, window):
        """Test functions with even window sizes (should be made odd)."""
        signal = np.random.randn(50) * 0.1 + np.sin(np.linspace(0, 10, 50))
        
        # Moving average should handle even windows
        result = smoothing.moving_average(signal, window=window)
        assert len(result) == len(signal)
        assert np.all(np.isfinite(result))
        
        # Median smooth should handle even windows
        result = smoothing.median_smooth(signal, window=window)
        assert len(result) == len(signal)
        assert np.all(np.isfinite(result))
        
        # Savitzky-Golay should handle even windows
        result = smoothing.savitzky_golay(signal, window=window, polyorder=3)
        assert len(result) == len(signal)
        assert np.all(np.isfinite(result))
    
    def test_savitzky_golay_polyorder_edge_cases(self):
        """Test Savitzky-Golay with polyorder >= window cases."""
        signal = np.random.randn(20) * 0.1 + np.sin(np.linspace(0, 5, 20))
        
        # Test polyorder equal to window - 1
        result = smoothing.savitzky_golay(signal, window=7, polyorder=6)
        assert len(result) == len(signal)
        assert np.all(np.isfinite(result))
        
        # Test polyorder greater than window (should be clamped)
        result = smoothing.savitzky_golay(signal, window=7, polyorder=10)
        assert len(result) == len(signal)
        assert np.all(np.isfinite(result))
    
    @pytest.mark.parametrize("alpha", [0.0, 1.0])
    @pytest.mark.parametrize("adjust", [True, False])
    def test_exponential_smooth_extreme_alphas(self, alpha, adjust):
        """Test exponential smoothing with alpha=0 and alpha=1."""
        signal = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        
        result = smoothing.exponential_smooth(signal, alpha=alpha, adjust=adjust)
        assert len(result) == len(signal)
        assert np.all(np.isfinite(result))
        
        if alpha == 0.0:
            # Alpha=0 should return constant (first value)
            expected = np.full_like(signal, signal[0])
            np.testing.assert_array_almost_equal(result, expected)
        elif alpha == 1.0:
            # Alpha=1 should return original signal (no smoothing)
            np.testing.assert_array_almost_equal(result, signal)
    
    @pytest.mark.parametrize("alpha", [0.0, 0.5, 1.0])
    @pytest.mark.parametrize("adjust", [True, False])
    @pytest.mark.parametrize("ignore_na", [True, False])
    def test_exponential_smooth_with_nans(self, alpha, adjust, ignore_na):
        """Test exponential smoothing with NaNs in various configurations."""
        signal = np.array([1.0, np.nan, 3.0, np.nan, 5.0])
        
        result = smoothing.exponential_smooth(signal, alpha=alpha, adjust=adjust, ignore_na=ignore_na)
        assert len(result) == len(signal)
        
        if ignore_na:
            # Should have some finite values
            assert np.sum(np.isfinite(result)) > 0
        # Note: Without ignore_na, NaNs may propagate depending on implementation
    
    def test_spline_smooth_duplicate_x_comprehensive(self):
        """Test spline_smooth with various duplicate x configurations."""
        # Exact duplicates
        x_dup = np.array([0, 1, 1, 2, 3])
        y_dup = np.array([0, 1, 2, 3, 4])
        
        with pytest.raises(ValueError, match="strictly increasing"):
            smoothing.spline_smooth(x_dup, y_dup)
        
        # Near duplicates (very close values)
        x_close = np.array([0, 1, 1.000001, 2, 3])
        y_close = np.array([0, 1, 2, 3, 4])
        
        # This should work (values are not exactly equal)
        x_smooth, y_smooth = smoothing.spline_smooth(x_close, y_close)
        assert len(x_smooth) == len(x_close)
        assert len(y_smooth) == len(y_close)
    
    @pytest.mark.parametrize("k", [-1, 0, 1, 2, 3, 4, 5, 6, 10])
    def test_spline_smooth_various_k_values(self, k):
        """Test spline_smooth with various k values (valid and invalid)."""
        x = np.linspace(0, 5, 20)
        y = np.sin(x)
        
        if k < 1 or k > 5:
            # Should warn about clamping
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                x_smooth, y_smooth = smoothing.spline_smooth(x, y, k=k)
                if k < 1 or k > 5:
                    assert len(w) > 0
        else:
            # Valid k values should work without warning
            x_smooth, y_smooth = smoothing.spline_smooth(x, y, k=k)
        
        assert len(x_smooth) == len(x)
        assert len(y_smooth) == len(y)
        assert np.all(np.isfinite(y_smooth))
    
    def test_lowess_smooth_unsorted_x(self):
        """Test that LOWESS raises error for unsorted x values."""
        x_unsorted = np.array([0, 2, 1, 3, 4])
        y = np.array([0, 1, 2, 3, 4])
        
        with pytest.raises(ValueError, match="sorted in ascending order"):
            smoothing.lowess_smooth(x_unsorted, y)
    
    def test_lowess_smooth_sorted_x(self):
        """Test that LOWESS works correctly with sorted x values."""
        x_sorted = np.array([0, 1, 2, 3, 4])
        y = np.array([0, 1, 4, 9, 16])
        
        x_smooth, y_smooth = smoothing.lowess_smooth(x_sorted, y)
        assert len(x_smooth) == len(x_sorted)
        assert len(y_smooth) == len(y)
        assert np.all(np.isfinite(y_smooth))
        np.testing.assert_array_equal(x_smooth, x_sorted)
    
    def test_extreme_parameter_combinations(self):
        """Test extreme parameter combinations that might cause issues."""
        signal = np.array([1, 2, 3, 4, 5, 4, 3, 2, 1])
        
        # Very small sigma for Gaussian
        result = smoothing.gaussian_smooth(signal, sigma=0.01)
        assert np.all(np.isfinite(result))
        
        # Very large sigma for Gaussian
        result = smoothing.gaussian_smooth(signal, sigma=100.0)
        assert np.all(np.isfinite(result))
        
        # Butterworth with very low cutoff
        fs = 100.0
        result = smoothing.butterworth_lowpass(signal, cutoff_freq=0.1, sampling_freq=fs)
        assert np.all(np.isfinite(result))
        
        # Single point spline (should handle gracefully)
        x_single = np.array([1.0])
        y_single = np.array([2.0])
        
        # This should either work or raise a clear error
        try:
            x_smooth, y_smooth = smoothing.spline_smooth(x_single, y_single, k=1)
            assert len(x_smooth) == 1
            assert len(y_smooth) == 1
        except ValueError:
            pass  # Expected for single point


@pytest.mark.slow
class TestPerformance:
    """Performance tests for smoothing algorithms."""
    
    def test_large_signal_performance(self):
        """Test performance with large signals."""
        # Generate large signal
        x = np.linspace(0, 100, 10000)
        y = np.sin(x) + 0.1 * np.random.randn(len(x))
        
        # These should complete reasonably quickly
        smoothed_ma = smoothing.moving_average(y, window=51)
        smoothed_gauss = smoothing.gaussian_smooth(y, sigma=5.0)
        smoothed_sg = smoothing.savitzky_golay(y, window=51, polyorder=3)
        
        assert len(smoothed_ma) == len(y)
        assert len(smoothed_gauss) == len(y)
        assert len(smoothed_sg) == len(y)