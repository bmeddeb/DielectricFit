"""Comprehensive tests for the new interpolation API features."""

import numpy as np
import pytest
from library.algorithms import interpolation


class TestExtrapolationModes:
    """Test the unified extrapolation modes across all methods."""
    
    def test_linear_extrapolation_modes(self):
        """Test all extrapolation modes for linear interpolation."""
        x = np.array([0, 1, 2, 3, 4])
        y = np.array([0, 1, 4, 9, 16])
        x_new = np.array([-1, 0.5, 2.5, 5])
        
        # Test 'extrapolate' - true linear extension
        y_ext = interpolation.linear_interpolate(x, y, x_new, extrapolation='extrapolate')
        assert len(y_ext) == 4
        # Check left extrapolation uses first segment slope
        assert y_ext[0] == y[0] + (y[1] - y[0]) * (-1 - x[0])
        
        # Test 'const' - clamp to edge values
        y_const = interpolation.linear_interpolate(x, y, x_new, extrapolation='const')
        assert y_const[0] == y[0]  # Clamped to first value
        assert y_const[-1] == y[-1]  # Clamped to last value
        
        # Test 'nan' - return NaN outside bounds
        y_nan = interpolation.linear_interpolate(x, y, x_new, extrapolation='nan')
        assert np.isnan(y_nan[0])  # Outside left
        assert np.isnan(y_nan[-1])  # Outside right
        assert np.isfinite(y_nan[1])  # Inside
        
        # Test 'periodic' - wrap around
        y_per = interpolation.linear_interpolate(x, y, x_new, extrapolation='periodic')
        assert len(y_per) == 4
        # x=-1 wraps to x=3 (period=4)
        assert np.isclose(y_per[0], np.interp(3, x, y))
    
    def test_pchip_extrapolation_modes(self):
        """Test extrapolation modes for PCHIP."""
        x = np.array([0, 1, 2, 3])
        y = np.array([0, 1, 0, 1])
        x_new = np.array([-0.5, 3.5])
        
        # Default is 'nan' for PCHIP
        y_default = interpolation.pchip_interpolate(x, y, x_new)
        assert np.all(np.isnan(y_default))
        
        # Extrapolate mode
        y_ext = interpolation.pchip_interpolate(x, y, x_new, extrapolation='extrapolate')
        assert np.all(np.isfinite(y_ext))
        
        # Const mode
        y_const = interpolation.pchip_interpolate(x, y, x_new, extrapolation='const')
        assert y_const[0] == y[0]
        assert y_const[1] == y[-1]
    
    def test_cubic_spline_periodic_bc(self):
        """Test cubic spline with periodic boundary conditions."""
        # Create periodic data
        x = np.linspace(0, 2*np.pi, 9)
        y = np.sin(x)
        y[-1] = y[0]  # Ensure periodicity
        
        x_new = np.linspace(0, 2*np.pi, 50)
        
        # Should work with periodic BC
        y_interp = interpolation.cubic_spline_interpolate(
            x, y, x_new, bc_type='periodic'
        )
        assert np.all(np.isfinite(y_interp))
        
        # Should fail if y[0] != y[-1]
        y_bad = y.copy()
        y_bad[-1] = y[0] + 1
        with pytest.raises(ValueError, match="y\\[0\\] must equal y\\[-1\\]"):
            interpolation.cubic_spline_interpolate(
                x, y_bad, x_new, bc_type='periodic'
            )


class TestDeduplication:
    """Test the deduplication options for handling duplicate x values."""
    
    def test_deduplicate_raise(self):
        """Test that duplicates raise error by default."""
        x = np.array([0, 1, 1, 2, 3])  # Duplicate at x=1
        y = np.array([0, 1, 2, 3, 4])
        x_new = np.array([0.5, 1.5])
        
        with pytest.raises(ValueError, match="contains duplicates"):
            interpolation.linear_interpolate(x, y, x_new)
    
    def test_deduplicate_first(self):
        """Test keeping first occurrence when deduplicating."""
        x = np.array([0, 1, 1, 2, 3])
        y = np.array([0, 1, 2, 3, 4])
        x_new = np.array([0.5, 1.5])
        
        y_interp = interpolation.linear_interpolate(
            x, y, x_new, deduplicate='first'
        )
        assert len(y_interp) == 2
        # At x=1, should keep y=1 (first occurrence)
        # Check interpolation uses the deduplicated data
        assert np.isfinite(y_interp[0])
        assert np.isfinite(y_interp[1])
    
    def test_deduplicate_mean(self):
        """Test averaging duplicates when deduplicating."""
        x = np.array([0, 1, 1, 2, 3])
        y = np.array([0, 1, 3, 4, 5])  # y=1 and y=3 at x=1
        x_new = np.array([1.0])
        
        y_interp = interpolation.linear_interpolate(
            x, y, x_new, deduplicate='mean'
        )
        # Should average y values at x=1: (1+3)/2 = 2
        assert np.isclose(y_interp[0], 2.0)
    
    def test_deduplicate_with_multiple_methods(self):
        """Test deduplication works with various interpolation methods."""
        x = np.array([0, 1, 1, 2])
        y = np.array([0, 1, 2, 3])
        x_new = np.array([0.5, 1.5])
        
        # Test with different methods
        for method in [interpolation.pchip_interpolate, 
                      interpolation.cubic_spline_interpolate,
                      interpolation.akima_interpolate]:
            y_interp = method(x, y, x_new, deduplicate='first')
            assert len(y_interp) == 2
            assert np.all(np.isfinite(y_interp))


class TestBSplineInterpolation:
    """Test the new bspline_interpolate function."""
    
    def test_bspline_basic(self):
        """Test basic B-spline interpolation."""
        x = np.linspace(0, 5, 10)
        y = np.sin(x)
        x_new = np.linspace(0, 5, 50)
        
        y_interp = interpolation.bspline_interpolate(x, y, x_new, k=3)
        assert len(y_interp) == 50
        assert np.all(np.isfinite(y_interp))
    
    def test_bspline_k_validation(self):
        """Test that k is validated properly."""
        x = np.array([0, 1, 2, 3, 4])
        y = np.array([0, 1, 0, 1, 0])
        x_new = np.array([0.5, 1.5])
        
        # k must be in [1, 5]
        with pytest.raises(ValueError, match="k must be in \\[1, 5\\]"):
            interpolation.bspline_interpolate(x, y, x_new, k=0)
        
        with pytest.raises(ValueError, match="k must be in \\[1, 5\\]"):
            interpolation.bspline_interpolate(x, y, x_new, k=6)
    
    def test_bspline_insufficient_points(self):
        """Test that insufficient points raise error."""
        x = np.array([0, 1])  # Only 2 points
        y = np.array([0, 1])
        x_new = np.array([0.5])
        
        # Need at least k+1 points
        with pytest.raises(ValueError, match="Need at least"):
            interpolation.bspline_interpolate(x, y, x_new, k=3)
    
    def test_bspline_periodic_bc(self):
        """Test B-spline with periodic boundary conditions."""
        x = np.linspace(0, 2*np.pi, 9)
        y = np.sin(x)
        y[-1] = y[0]  # Make periodic
        x_new = np.linspace(0, 2*np.pi, 50)
        
        y_interp = interpolation.bspline_interpolate(
            x, y, x_new, k=3, bc_type='periodic'
        )
        assert np.all(np.isfinite(y_interp))
    
    def test_make_interp_spline_alias(self):
        """Test that make_interp_spline is an alias for bspline_interpolate."""
        assert interpolation.make_interp_spline is interpolation.bspline_interpolate


class TestRBFInterpolation:
    """Test RBF interpolation improvements."""
    
    def test_rbf_auto_epsilon(self):
        """Test automatic epsilon inference for RBF."""
        x = np.array([0, 1, 2, 3, 4])
        y = np.array([0, 1, 0, 1, 0])
        x_new = np.linspace(0, 4, 20)
        
        # Should infer epsilon automatically for multiquadric
        y_interp = interpolation.rbf_interpolate(
            x, y, x_new, function='multiquadric'
        )
        assert len(y_interp) == 20
        assert np.all(np.isfinite(y_interp))
    
    def test_rbf_scale_invariant_kernels(self):
        """Test RBF kernels that don't need epsilon."""
        x = np.array([0, 1, 2, 3])
        y = np.array([0, 1, 0, 1])
        x_new = np.linspace(0, 3, 20)
        
        # These kernels don't need epsilon
        for kernel in ['linear', 'cubic', 'quintic', 'thin_plate_spline']:
            y_interp = interpolation.rbf_interpolate(
                x, y, x_new, function=kernel
            )
            assert np.all(np.isfinite(y_interp))
    
    def test_rbf_with_smoothing(self):
        """Test RBF with smoothing parameter."""
        x = np.array([0, 1, 2, 3, 4])
        y = np.array([0, 1, 0, 1, 0]) + 0.1 * np.random.randn(5)
        x_new = np.linspace(0, 4, 50)
        
        # Without smoothing
        y_exact = interpolation.rbf_interpolate(x, y, x_new, smooth=0.0)
        
        # With smoothing
        y_smooth = interpolation.rbf_interpolate(x, y, x_new, smooth=0.5)
        
        assert len(y_exact) == len(y_smooth) == 50
        # Smoothed version should have less variation
        assert np.std(np.diff(y_smooth)) <= np.std(np.diff(y_exact))


class TestResampleUniform:
    """Test uniform resampling with method_kwargs."""
    
    def test_resample_with_kwargs(self):
        """Test passing kwargs to underlying methods."""
        x = np.array([0, 1, 2, 3, 4])
        y = np.array([0, 1, 4, 9, 16])
        
        # Pass bc_type to cubic method
        x_new, y_new = interpolation.resample_uniform(
            x, y, 20, method='cubic', bc_type='natural'
        )
        assert len(x_new) == len(y_new) == 20
        
        # Pass k to bspline method
        x_new, y_new = interpolation.resample_uniform(
            x, y, 20, method='bspline', k=2
        )
        assert len(x_new) == len(y_new) == 20
    
    def test_resample_all_methods(self):
        """Test resampling with all available methods."""
        x = np.linspace(0, 5, 10)
        y = np.sin(x)
        
        methods = ['linear', 'pchip', 'cubic', 'akima', 'nearest', 'bspline', 'rbf']
        
        for method in methods:
            x_new, y_new = interpolation.resample_uniform(
                x, y, 30, method=method
            )
            assert len(x_new) == len(y_new) == 30
            assert np.all(np.diff(x_new) > 0)  # Strictly increasing
            
            # Check uniform spacing
            spacing = np.diff(x_new)
            assert np.allclose(spacing, spacing[0])


class TestEdgeCases:
    """Test edge cases with the new API."""
    
    def test_single_point_interpolation(self):
        """Test interpolation with single data point."""
        x = np.array([1.0])
        y = np.array([2.0])
        x_new = np.array([0.5, 1.0, 1.5])
        
        # Linear should handle this with const extrapolation
        y_interp = interpolation.linear_interpolate(
            x, y, x_new, extrapolation='const'
        )
        assert np.all(y_interp == 2.0)  # All constant
    
    def test_periodic_with_short_period(self):
        """Test periodic extrapolation with very short period."""
        x = np.array([0, 1])
        y = np.array([0, 1])
        x_new = np.array([-2, -1, 0, 1, 2, 3])
        
        y_per = interpolation.linear_interpolate(
            x, y, x_new, extrapolation='periodic'
        )
        
        # Period is 1, so pattern repeats
        assert y_per[2] == y_per[0]  # x=0 same as x=-2 (mod 1)
        assert y_per[3] == y_per[1]  # x=1 same as x=-1 (mod 1)
    
    def test_strictly_increasing_validation(self):
        """Test that strictly increasing check works."""
        # Sorted but not strictly increasing (has duplicate)
        x = np.array([0, 1, 1, 2])
        y = np.array([0, 1, 2, 3])
        
        # Should raise by default
        with pytest.raises(ValueError):
            interpolation.linear_interpolate(x, y, [0.5])
        
        # Should work with deduplication
        y_interp = interpolation.linear_interpolate(
            x, y, [0.5], deduplicate='first'
        )
        assert np.isfinite(y_interp[0])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])