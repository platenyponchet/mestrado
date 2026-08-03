import math
import random

import pytest


@pytest.fixture
def small_series():
    """20-point sinusoidal series with timestamps 0-19."""
    return [(i, 100 + 50 * math.sin(i * 0.3)) for i in range(20)]


@pytest.fixture
def medium_series():
    """200-point series simulating realistic consumption."""
    return [(i, 200 + 100 * math.sin(i * 2 * math.pi / 200) + 30 * math.cos(i * 0.1)) for i in range(200)]


@pytest.fixture
def constant_series():
    """20-point constant series."""
    return [(i, 100.0) for i in range(20)]


@pytest.fixture
def noisy_series():
    """2000-point noisy series, seeded for reproducibility.

    The ARC-SDT controller cannot be exercised on `medium_series`: that signal is
    smooth enough that even the lowest tol_rel allowed by `output_limits` already
    yields ~91% CR, so the PID output saturates and the measured CR stops tracking
    the target. Gaussian noise makes the corridor break often enough that tol_rel
    lands inside its usable range and the loop actually closes.
    """
    rng = random.Random(42)
    return [(i, 200 + 100 * math.sin(i * 2 * math.pi / 500) + rng.gauss(0, 25)) for i in range(2000)]


@pytest.fixture
def high_frequency_series():
    """200-point series whose energy sits on a high-frequency DCT basis function.

    Built directly from basis k=150 so that the dominant coefficient is a high one.
    A compressor that keeps the *first* K coefficients destroys this signal; one that
    keeps the K *largest in magnitude* reconstructs it almost exactly.
    """
    n = 200
    return [(i, 100 + 50 * math.cos(math.pi * (2 * i + 1) * 150 / (2 * n))) for i in range(n)]


@pytest.fixture
def expected_transform_cr():
    """Byte cost model shared by DCTCompressor and WaveletCompressor.

    Mirrors the model documented in both compressors so that any change to it breaks
    a test instead of silently shifting every reported compression ratio:

      - a raw point costs 8 bytes: 4 (value) + 4 (timestamp)
      - fixed overhead is 12 bytes: xmin, xmax and the window's initial timestamp
      - each kept coefficient costs 8 bytes: 4 (value) + 4 (original index), because
        the kept positions are scattered rather than a leading run
    """
    def _expected(n_points, cr, n_coeffs):
        original = n_points * 8
        target = original * round(1 - cr / 100, 10)
        overhead = 3 * 4
        k = max(1, int((target - overhead) / 8))
        k = min(k, n_coeffs)
        return 100 * (1 - (k * 8 + overhead) / original)

    return _expected


@pytest.fixture
def metric_keys():
    return frozenset({
        "MSE", "RMSE", "NRMSE", "MAPE", "ISD", "PRD",
        "SNR", "PSNR", "SSIM",
        "EnergyError", "EnergyErrorTotal",
        "PeakRecall", "PeakAmplitudeError",
    })
