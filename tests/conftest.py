import math
import pytest


@pytest.fixture
def serie_pequena():
    """20-point sinusoidal series with timestamps 0-19."""
    return [(i, 100 + 50 * math.sin(i * 0.3)) for i in range(20)]


@pytest.fixture
def serie_media():
    """200-point series simulating realistic consumption."""
    return [(i, 200 + 100 * math.sin(i * 2 * math.pi / 200) + 30 * math.cos(i * 0.1)) for i in range(200)]


@pytest.fixture
def serie_constante():
    """20-point constant series."""
    return [(i, 100.0) for i in range(20)]


@pytest.fixture
def metric_keys():
    return frozenset({
        "MSE", "RMSE", "NRMSE", "MAPE", "ISD", "PRD",
        "SNR", "PSNR", "SSIM",
        "EnergyError", "EnergyErrorTotal",
        "PeakRecall", "PeakAmplitudeError",
    })
