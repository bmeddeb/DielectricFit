"""Pytest configuration and fixtures for library tests."""

import numpy as np
import pytest


@pytest.fixture
def clean_sine_wave():
    """Generate a clean sine wave for testing."""
    x = np.linspace(0, 2 * np.pi, 100)
    y = np.sin(x)
    return x, y


@pytest.fixture
def noisy_sine_wave(clean_sine_wave):
    """Generate a noisy sine wave for testing smoothing algorithms."""
    x, clean_y = clean_sine_wave
    np.random.seed(42)  # Reproducible noise
    noise = 0.1 * np.random.randn(len(clean_y))
    noisy_y = clean_y + noise
    return x, noisy_y, clean_y


@pytest.fixture
def outlier_signal(noisy_sine_wave):
    """Generate a signal with outliers for robust filtering tests."""
    x, noisy_y, clean_y = noisy_sine_wave
    outlier_y = noisy_y.copy()
    outlier_y[25] = 5.0   # Positive outlier
    outlier_y[75] = -5.0  # Negative outlier
    return x, outlier_y, clean_y


@pytest.fixture
def sparse_quadratic():
    """Generate sparse quadratic data for interpolation tests."""
    x = np.array([0, 1, 2, 3, 4, 5])
    y = x ** 2  # y = x^2
    return x, y


@pytest.fixture
def dense_grid():
    """Generate dense grid for interpolation."""
    return np.linspace(0, 5, 50)


@pytest.fixture
def monotonic_data():
    """Generate monotonic data for monotonicity-preserving tests."""
    x = np.array([0, 1, 2, 3, 4])
    y = np.array([0, 0.5, 0.8, 0.9, 1.0])
    return x, y


@pytest.fixture
def log_scale_data():
    """Generate data for logarithmic interpolation tests."""
    x = np.array([1, 10, 100, 1000])
    y = np.array([1, 10, 100, 1000])  # y = x
    return x, y


@pytest.fixture
def frequency_data():
    """Generate frequency domain test data."""
    fs = 100  # Sampling frequency
    t = np.linspace(0, 1, fs, endpoint=False)
    
    # Signal with multiple frequency components
    f1, f2, f3 = 5, 15, 25  # Hz
    signal = (np.sin(2*np.pi*f1*t) + 
              0.5*np.sin(2*np.pi*f2*t) + 
              0.2*np.sin(2*np.pi*f3*t))
    
    return t, signal, fs


@pytest.fixture(params=[5, 7, 9, 11])
def window_sizes(request):
    """Parametrized window sizes for testing."""
    return request.param


@pytest.fixture(params=[1, 2, 3])
def polynomial_orders(request):
    """Parametrized polynomial orders for testing."""
    return request.param


@pytest.fixture(params=[
    'linear', 'cubic', 'pchip', 'akima'
])
def interpolation_methods(request):
    """Parametrized interpolation methods."""
    return request.param


@pytest.fixture(params=[
    'multiquadric', 'linear', 'cubic', 'quintic', 'thin_plate'
])
def rbf_kernels(request):
    """Parametrized RBF kernel functions."""
    return request.param


@pytest.fixture(params=[0.1, 0.3, 0.5, 0.7, 0.9])
def alpha_values(request):
    """Parametrized alpha values for exponential smoothing."""
    return request.param


@pytest.fixture
def dielectric_data():
    """Generate realistic dielectric spectroscopy data."""
    # Frequency range typical for dielectric measurements
    freq = np.logspace(0, 6, 100)  # 1 Hz to 1 MHz
    
    # Simple Cole-Cole model parameters
    eps_inf = 3.0    # High frequency permittivity
    delta_eps = 10.0 # Relaxation strength
    tau = 1e-4       # Relaxation time (s)
    alpha = 0.1      # Distribution parameter
    
    # Complex permittivity
    omega = 2 * np.pi * freq
    eps_complex = eps_inf + delta_eps / (1 + (1j * omega * tau) ** (1 - alpha))
    
    eps_real = eps_complex.real
    eps_imag = eps_complex.imag
    
    # Add some noise
    np.random.seed(123)
    noise_level = 0.02
    eps_real += noise_level * eps_real * np.random.randn(len(freq))
    eps_imag += noise_level * eps_imag * np.random.randn(len(freq))
    
    return freq, eps_real, eps_imag


@pytest.fixture
def small_dataset():
    """Small dataset for edge case testing."""
    x = np.array([1, 2])
    y = np.array([1, 4])
    return x, y


@pytest.fixture
def empty_dataset():
    """Empty dataset for error testing."""
    return np.array([]), np.array([])


@pytest.fixture
def unsorted_data():
    """Unsorted data for error testing."""
    x = np.array([1, 3, 2, 4])
    y = np.array([1, 9, 4, 16])
    return x, y


@pytest.fixture(autouse=True)
def reset_random_seed():
    """Reset random seed before each test for reproducibility."""
    np.random.seed(42)