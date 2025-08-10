from __future__ import annotations

import numpy as np
from django.test import TestCase

from library.algorithms import interpolation, smoothing


class SmoothingTestCase(TestCase):
    """Test cases for smoothing algorithms."""
    
    def setUp(self):
        """Set up test data."""
        # Create noisy sine wave
        self.x = np.linspace(0, 2 * np.pi, 100)
        self.clean_signal = np.sin(self.x)
        np.random.seed(42)
        self.noise = 0.1 * np.random.randn(100)
        self.noisy_signal = self.clean_signal + self.noise
        
        # Create signal with outliers
        self.outlier_signal = self.noisy_signal.copy()
        self.outlier_signal[25] = 5.0
        self.outlier_signal[75] = -5.0
    
    def test_moving_average(self):
        """Test moving average smoothing."""
        smoothed = smoothing.moving_average(self.noisy_signal, window=5)
        
        # Check shape preserved
        self.assertEqual(smoothed.shape, self.noisy_signal.shape)
        
        # Check smoothing reduces variance
        self.assertLess(np.var(smoothed), np.var(self.noisy_signal))
        
        # Test edge cases - empty array should raise error
        with self.assertRaises(ValueError):
            smoothing.moving_average([], window=5)
        
        # Test window larger than signal
        small_signal = [1, 2, 3]
        smoothed = smoothing.moving_average(small_signal, window=10)
        self.assertEqual(len(smoothed), 3)
    
    def test_gaussian_smooth(self):
        """Test Gaussian smoothing."""
        smoothed = smoothing.gaussian_smooth(self.noisy_signal, sigma=2.0)
        
        # Check shape preserved
        self.assertEqual(smoothed.shape, self.noisy_signal.shape)
        
        # Check smoothing reduces high frequency noise
        fft_orig = np.abs(np.fft.fft(self.noisy_signal))
        fft_smooth = np.abs(np.fft.fft(smoothed))
        # High frequency components should be reduced
        self.assertLess(
            np.sum(fft_smooth[50:]),
            np.sum(fft_orig[50:])
        )
        
        # Test error cases
        with self.assertRaises(ValueError):
            smoothing.gaussian_smooth(self.noisy_signal, sigma=-1)
        
        with self.assertRaises(ValueError):
            smoothing.gaussian_smooth([], sigma=2.0)
    
    def test_median_smooth(self):
        """Test median filter (robust to outliers)."""
        smoothed = smoothing.median_smooth(self.outlier_signal, window=5)
        
        # Check shape preserved
        self.assertEqual(smoothed.shape, self.outlier_signal.shape)
        
        # Check outliers are removed
        self.assertLess(np.max(np.abs(smoothed)), 3.0)
        
        # Median filter should handle outliers better than mean
        mean_smoothed = smoothing.moving_average(self.outlier_signal, window=5)
        self.assertLess(
            np.max(np.abs(smoothed - self.clean_signal)),
            np.max(np.abs(mean_smoothed - self.clean_signal))
        )
    
    def test_savitzky_golay(self):
        """Test Savitzky-Golay filter."""
        smoothed = smoothing.savitzky_golay(self.noisy_signal, window=7, polyorder=3)
        
        # Check shape preserved
        self.assertEqual(smoothed.shape, self.noisy_signal.shape)
        
        # Test derivative calculation
        deriv = smoothing.savitzky_golay(
            self.clean_signal, window=15, polyorder=3, deriv=1,
            delta=self.x[1] - self.x[0]  # Use actual spacing
        )
        expected_deriv = np.cos(self.x)
        
        # Derivative should approximate cosine (relaxed threshold)
        correlation = np.corrcoef(deriv, expected_deriv)[0, 1]
        self.assertGreater(correlation, 0.95)
    
    def test_butterworth_lowpass(self):
        """Test Butterworth low-pass filter."""
        # Create signal with high frequency component
        high_freq = 0.1 * np.sin(20 * self.x)
        mixed_signal = self.clean_signal + high_freq
        
        # Apply low-pass filter
        smoothed = smoothing.butterworth_lowpass(
            mixed_signal, 
            cutoff_freq=2.0,
            sampling_freq=100 / (2 * np.pi),
            order=5
        )
        
        # Check shape preserved
        self.assertEqual(smoothed.shape, mixed_signal.shape)
        
        # Check high frequency removed
        correlation = np.corrcoef(smoothed, self.clean_signal)[0, 1]
        self.assertGreater(correlation, 0.99)
        
        # Test error cases
        with self.assertRaises(ValueError):
            smoothing.butterworth_lowpass(
                mixed_signal,
                cutoff_freq=100,  # Above Nyquist
                sampling_freq=100,
                order=5
            )
    
    def test_exponential_smooth(self):
        """Test exponential smoothing."""
        smoothed = smoothing.exponential_smooth(self.noisy_signal, alpha=0.3)
        
        # Check shape preserved
        self.assertEqual(smoothed.shape, self.noisy_signal.shape)
        
        # Test with NaN values
        signal_with_nan = self.noisy_signal.copy()
        signal_with_nan[50] = np.nan
        
        smoothed = smoothing.exponential_smooth(
            signal_with_nan, alpha=0.3, ignore_na=True
        )
        
        # Non-NaN values should be smoothed
        self.assertFalse(np.isnan(smoothed[49]))
        self.assertFalse(np.isnan(smoothed[51]))
        
        # Test error cases
        with self.assertRaises(ValueError):
            smoothing.exponential_smooth(self.noisy_signal, alpha=1.5)
    
    def test_spline_smooth(self):
        """Test spline smoothing."""
        x_smooth, y_smooth = smoothing.spline_smooth(
            self.x, self.noisy_signal, s=5.0
        )
        
        # Check shape preserved
        self.assertEqual(x_smooth.shape, self.x.shape)
        self.assertEqual(y_smooth.shape, self.noisy_signal.shape)
        
        # Check smoothing reduces variance
        self.assertLess(np.var(y_smooth), np.var(self.noisy_signal))


class InterpolationTestCase(TestCase):
    """Test cases for interpolation algorithms."""
    
    def setUp(self):
        """Set up test data."""
        # Create sparse data points
        self.x = np.array([0, 1, 2, 3, 4, 5])
        self.y = np.array([0, 1, 4, 9, 16, 25])  # y = x^2
        
        # Dense grid for interpolation
        self.x_new = np.linspace(0, 5, 50)
        
        # Create monotonic data
        self.x_mono = np.array([0, 1, 2, 3, 4])
        self.y_mono = np.array([0, 0.5, 0.8, 0.9, 1.0])
        
        # Create data for log interpolation
        self.x_log = np.array([1, 10, 100, 1000])
        self.y_log = np.array([1, 10, 100, 1000])
    
    def test_linear_interpolate(self):
        """Test linear interpolation."""
        y_interp = interpolation.linear_interpolate(self.x, self.y, self.x_new)
        
        # Check shape
        self.assertEqual(y_interp.shape, self.x_new.shape)
        
        # Check interpolation at known points (use exact x values)
        y_at_known = interpolation.linear_interpolate(self.x, self.y, self.x)
        np.testing.assert_array_almost_equal(y_at_known, self.y, decimal=10)
        
        # Test extrapolation
        x_extrap = np.array([-1, 6])
        y_extrap = interpolation.linear_interpolate(
            self.x, self.y, x_extrap, left=-1, right=36
        )
        self.assertEqual(y_extrap[0], -1)
        self.assertEqual(y_extrap[1], 36)
    
    def test_pchip_interpolate(self):
        """Test PCHIP interpolation (monotonicity preserving)."""
        y_interp = interpolation.pchip_interpolate(
            self.x_mono, self.y_mono, self.x_new[:40]  # Within range
        )
        
        # Check monotonicity preserved
        self.assertTrue(np.all(np.diff(y_interp) >= 0))
        
        # Test without extrapolation
        y_no_extrap = interpolation.pchip_interpolate(
            self.x, self.y, np.array([-1, 6]), extrapolate=False
        )
        self.assertTrue(np.isnan(y_no_extrap[0]))
        self.assertTrue(np.isnan(y_no_extrap[1]))
    
    def test_cubic_spline_interpolate(self):
        """Test cubic spline interpolation."""
        y_interp = interpolation.cubic_spline_interpolate(self.x, self.y, self.x_new)
        
        # Check shape
        self.assertEqual(y_interp.shape, self.x_new.shape)
        
        # Check smoothness (second derivative exists)
        dy = np.diff(y_interp)
        ddy = np.diff(dy)
        # Second derivative should be continuous (small jumps)
        self.assertLess(np.max(np.abs(np.diff(ddy))), 1.0)
        
        # Test natural boundary conditions
        y_natural = interpolation.cubic_spline_interpolate(
            self.x, self.y, self.x_new, bc_type='natural'
        )
        self.assertEqual(y_natural.shape, self.x_new.shape)
    
    def test_akima_interpolate(self):
        """Test Akima interpolation."""
        y_interp = interpolation.akima_interpolate(self.x, self.y, self.x_new)
        
        # Check shape
        self.assertEqual(y_interp.shape, self.x_new.shape)
        
        # Akima should produce less oscillation than cubic spline
        y_cubic = interpolation.cubic_spline_interpolate(self.x, self.y, self.x_new)
        
        # Compare overshoots
        self.assertLess(
            np.max(y_interp) - np.max(self.y),
            np.max(y_cubic) - np.max(self.y) + 1  # Akima typically overshoots less
        )
    
    def test_rbf_interpolate(self):
        """Test RBF interpolation."""
        y_interp = interpolation.rbf_interpolate(
            self.x, self.y, self.x_new, function='multiquadric', epsilon=1.0
        )
        
        # Check shape
        self.assertEqual(y_interp.shape, self.x_new.shape)
        
        # Test with smoothing
        y_smooth = interpolation.rbf_interpolate(
            self.x, self.y, self.x_new, function='multiquadric', epsilon=1.0, smooth=1.0
        )
        
        # Smoothed version should have less variance
        self.assertLess(np.var(np.diff(y_smooth)), np.var(np.diff(y_interp)))
    
    def test_logarithmic_interpolate(self):
        """Test logarithmic interpolation."""
        x_new_log = np.logspace(0, 3, 50)
        y_interp = interpolation.logarithmic_interpolate(
            self.x_log, self.y_log, x_new_log
        )
        
        # Check shape
        self.assertEqual(y_interp.shape, x_new_log.shape)
        
        # For y=x data, logarithmic interpolation should be exact
        np.testing.assert_array_almost_equal(y_interp, x_new_log, decimal=5)
        
        # Test error cases
        with self.assertRaises(ValueError):
            interpolation.logarithmic_interpolate(
                np.array([0, 1, 2]),  # Contains 0
                np.array([1, 2, 3]),
                np.array([0.5, 1.5])
            )
    
    def test_resample_uniform(self):
        """Test uniform resampling."""
        x_uniform, y_uniform = interpolation.resample_uniform(
            self.x, self.y, num_points=20, method='pchip'
        )
        
        # Check uniform spacing
        spacing = np.diff(x_uniform)
        np.testing.assert_array_almost_equal(
            spacing, spacing[0] * np.ones_like(spacing)
        )
        
        # Check shape
        self.assertEqual(len(x_uniform), 20)
        self.assertEqual(len(y_uniform), 20)
        
        # Test different methods
        for method in ['linear', 'cubic', 'pchip', 'akima']:
            x_u, y_u = interpolation.resample_uniform(
                self.x, self.y, num_points=20, method=method
            )
            self.assertEqual(len(x_u), 20)
    
    def test_error_handling(self):
        """Test error handling in interpolation functions."""
        # Test mismatched sizes
        with self.assertRaises(ValueError):
            interpolation.linear_interpolate(
                [1, 2, 3], [1, 2], [1.5]
            )
        
        # Test empty arrays
        with self.assertRaises(ValueError):
            interpolation.linear_interpolate([], [], [1])
        
        # Test unsorted x
        with self.assertRaises(ValueError):
            interpolation.linear_interpolate(
                [1, 3, 2], [1, 2, 3], [1.5]
            )
        
        # Test insufficient points
        with self.assertRaises(ValueError):
            interpolation.pchip_interpolate([1], [1], [1.5])