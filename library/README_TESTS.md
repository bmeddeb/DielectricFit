# DielectricFit Library

Production-ready smoothing and interpolation algorithms for dielectric spectroscopy and materials science applications.

## Overview

This library provides robust, scientifically-validated algorithms for:
- **Smoothing**: Noise reduction and signal conditioning 
- **Interpolation**: Data resampling and gap filling
- **Signal Processing**: Frequency-domain filtering and analysis

All algorithms use scipy's optimized implementations with comprehensive error handling and validation.

## Features

### Smoothing Algorithms
- **Moving Average**: Fast uniform window smoothing
- **Gaussian Filter**: Optimal low-pass smoothing
- **Median Filter**: Robust outlier-resistant smoothing
- **Savitzky-Golay**: Feature-preserving polynomial smoothing
- **Butterworth Filter**: Frequency-domain filtering
- **Wiener Filter**: Optimal noise reduction
- **Exponential Smoothing**: Exponentially weighted moving average
- **Spline Smoothing**: B-spline based smoothing

### Interpolation Methods
- **Linear**: Fast 1D linear interpolation
- **PCHIP**: Monotonicity-preserving cubic interpolation
- **Cubic Spline**: Smooth cubic spline with boundary conditions
- **Akima**: Oscillation-reduced cubic interpolation
- **RBF**: Radial basis function for scattered data
- **Logarithmic**: Interpolation in log space
- **Uniform Resampling**: Convert to uniform spacing

## Installation

```bash
# Core dependencies (required)
pip install numpy scipy matplotlib

# Testing dependencies (optional)
pip install pytest pytest-django pytest-cov hypothesis

# Development dependencies (optional)  
pip install black isort mypy flake8
```

## Usage

### Basic Smoothing
```python
from library.algorithms import smoothing
import numpy as np

# Generate noisy signal
x = np.linspace(0, 2*np.pi, 100)
noisy_signal = np.sin(x) + 0.1*np.random.randn(100)

# Apply smoothing
smoothed = smoothing.savitzky_golay(noisy_signal, window=7, polyorder=3)
gaussian_smoothed = smoothing.gaussian_smooth(noisy_signal, sigma=2.0)
```

### Basic Interpolation
```python
from library.algorithms import interpolation

# Sparse data points
x = np.array([0, 1, 2, 3, 4])
y = x**2  # quadratic function

# Interpolate to dense grid
x_new = np.linspace(0, 4, 50)
y_interp = interpolation.pchip_interpolate(x, y, x_new)

# Uniform resampling
x_uniform, y_uniform = interpolation.resample_uniform(x, y, num_points=100)
```

### Advanced Usage
```python
# Frequency-domain filtering
filtered = smoothing.butterworth_lowpass(
    signal, cutoff_freq=10.0, sampling_freq=1000.0, order=5
)

# Robust smoothing with outliers
robust_smooth = smoothing.median_smooth(outlier_signal, window=5)

# Monotonic interpolation
monotonic_interp = interpolation.pchip_interpolate(x, y, x_new)
```

## Testing

### Django Tests (Existing)
```bash
python manage.py test library
```

### Pytest (New)
```bash
# Run all tests
pytest library/tests/

# Run with coverage
pytest library/tests/ --cov=library --cov-report=html

# Run specific test categories
pytest library/tests/ -m "unit"          # Unit tests only
pytest library/tests/ -m "integration"   # Integration tests only  
pytest library/tests/ -m "property"      # Property-based tests only

# Run tests in parallel (faster)
pytest library/tests/ -n auto

# Run with hypothesis property-based testing (requires: pip install hypothesis)
pytest library/tests/test_property_based.py
```

### Using Makefile
```bash
make test              # Run all pytest tests
make test-coverage     # Run with coverage report
make test-fast         # Run in parallel
make test-django       # Run Django tests
make test-all          # Run both Django and pytest
```

## Test Structure

### 📁 Test Organization
```
library/tests/
├── __init__.py
├── test_smoothing.py      # Smoothing algorithm tests
├── test_interpolation.py  # Interpolation algorithm tests
└── test_property_based.py # Property-based robustness tests
```

### 🧪 Test Categories

**Unit Tests** (`-m unit`)
- Individual algorithm functionality
- Parameter validation
- Error handling

**Integration Tests** (`-m integration`)  
- Algorithm combinations
- End-to-end workflows
- Consistency between methods

**Property Tests** (`-m property`)
- Mathematical invariants
- Robustness across input ranges
- Edge cases and boundary conditions

**Performance Tests** (`-m slow`)
- Large dataset handling
- Algorithm efficiency
- Memory usage

### 🎯 Test Features

- **Parametrized Tests**: Multiple parameter combinations
- **Fixtures**: Realistic scientific data (sine waves, dielectric spectra)
- **Property-based Testing**: Hypothesis for robustness (optional)
- **Performance Benchmarking**: pytest-benchmark integration
- **Coverage Reporting**: HTML and terminal coverage reports

## Configuration

### Pytest Configuration (`pytest.ini`)
```ini
[tool:pytest]
DJANGO_SETTINGS_MODULE = config.settings
testpaths = library/tests
markers =
    slow: marks tests as slow
    integration: integration tests  
    unit: unit tests
    property: property-based tests
```

### Test Fixtures (`library/conftest.py`)
Provides scientific test data:
- Clean and noisy sine waves
- Dielectric spectroscopy data
- Sparse and dense grids
- Edge cases and boundary conditions

## API Reference

### Smoothing Module (`library.algorithms.smoothing`)

| Function | Description | Key Parameters |
|----------|-------------|----------------|
| `moving_average()` | Uniform window smoothing | `window`, `mode` |
| `gaussian_smooth()` | Gaussian kernel smoothing | `sigma`, `truncate` |
| `median_smooth()` | Robust median filtering | `window`, `mode` |
| `savitzky_golay()` | Polynomial smoothing | `window`, `polyorder`, `deriv` |
| `butterworth_lowpass()` | Frequency filtering | `cutoff_freq`, `sampling_freq` |
| `exponential_smooth()` | EWMA smoothing | `alpha`, `adjust` |
| `spline_smooth()` | B-spline smoothing | `s`, `k` |

### Interpolation Module (`library.algorithms.interpolation`)

| Function | Description | Key Parameters |
|----------|-------------|----------------|
| `linear_interpolate()` | Linear interpolation | `left`, `right` |
| `pchip_interpolate()` | Monotonic cubic | `extrapolate` |
| `cubic_spline_interpolate()` | Cubic spline | `bc_type`, `extrapolate` |
| `akima_interpolate()` | Akima cubic | `extrapolate` |
| `rbf_interpolate()` | Radial basis function | `function`, `epsilon` |
| `logarithmic_interpolate()` | Log-space interpolation | `base` |
| `resample_uniform()` | Uniform resampling | `num_points`, `method` |

## Type Safety

This package includes full type annotations and a `py.typed` marker file for static type checking:

```bash
mypy library/  # Type checking with mypy
```

## Performance

All algorithms are optimized for scientific computing:
- Uses scipy's compiled implementations
- Efficient memory usage
- Vectorized operations
- Parallel testing support

## Scientific Validation

Algorithms have been validated for:
- Numerical accuracy and stability
- Boundary condition handling  
- Mathematical invariant preservation
- Robustness across parameter ranges

## Contributing

1. Add tests for new algorithms
2. Maintain type annotations
3. Follow scientific computing best practices
4. Run full test suite: `make test-all`

## License

Part of the DielectricFit project for dielectric spectroscopy analysis.