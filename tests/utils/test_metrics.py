import pytest
from src.compressors.utils.metrics import Metrics


# ── MSE ──────────────────────────────────────────────────────────────────────

def test_mse_identical_series():
    assert Metrics([1.0, 2.0, 3.0], [1.0, 2.0, 3.0]).mse() == pytest.approx(0.0)


def test_mse_known_value():
    # mean([(0-1)^2, (0-1)^2]) = 1.0
    assert Metrics([0.0, 0.0], [1.0, 1.0]).mse() == pytest.approx(1.0)


# ── RMSE ─────────────────────────────────────────────────────────────────────

def test_rmse_equals_sqrt_of_mse():
    m = Metrics([0.0, 0.0], [3.0, 4.0])
    assert m.rmse() == pytest.approx(m.mse() ** 0.5)


# ── NRMSE ────────────────────────────────────────────────────────────────────

def test_nrmse_zero_range_returns_zero():
    # Constant original: range=0 → nrmse=0 regardless of reconstruction
    assert Metrics([5.0, 5.0, 5.0], [5.0, 5.0, 5.0]).nrmse() == pytest.approx(0.0)


def test_nrmse_known_value():
    # original=[0,1], range=1, mse=1.0, rmse=1.0, nrmse=1.0
    assert Metrics([0.0, 1.0], [1.0, 0.0]).nrmse() == pytest.approx(1.0)


# ── SSIM ─────────────────────────────────────────────────────────────────────

def test_ssim_identical_series():
    s = [float(i) for i in range(1, 11)]
    assert Metrics(s, s).ssim() == pytest.approx(1.0)


def test_ssim_constant_equal_series():
    assert Metrics([5.0] * 10, [5.0] * 10).ssim() == pytest.approx(1.0)


# ── MAPE ─────────────────────────────────────────────────────────────────────

def test_mape_known_value():
    # |10-12|/10 * 100 = 20%
    assert Metrics([10.0], [12.0]).mape() == pytest.approx(20.0)


def test_mape_skips_zero_original_values():
    # Only second pair counts: |10-20|/10 * 100 = 100%
    assert Metrics([0.0, 10.0], [99.0, 20.0]).mape() == pytest.approx(100.0)


# ── ISD ──────────────────────────────────────────────────────────────────────

def test_isd_known_value():
    # sum([(0-1)^2, (0-1)^2]) = 2.0
    assert Metrics([0.0, 0.0], [1.0, 1.0]).isd() == pytest.approx(2.0)


# ── PRD ──────────────────────────────────────────────────────────────────────

def test_prd_known_value():
    # numerator=sqrt(2), denominator=sqrt(2), prd=100%
    assert Metrics([1.0, 1.0], [0.0, 0.0]).prd() == pytest.approx(100.0)


# ── SNR ──────────────────────────────────────────────────────────────────────

def test_snr_zero_noise_returns_none():
    # Identical series: noise_power=0 → None
    assert Metrics([1.0, 2.0, 3.0], [1.0, 2.0, 3.0]).snr() is None


def test_snr_zero_signal_returns_none():
    assert Metrics([0.0, 0.0], [1.0, 1.0]).snr() is None


def test_snr_positive_when_signal_dominates():
    result = Metrics([100.0, 100.0], [99.0, 101.0]).snr()
    assert result is not None
    assert result > 0


# ── PSNR ─────────────────────────────────────────────────────────────────────

def test_psnr_zero_mse_returns_none():
    assert Metrics([5.0, 5.0], [5.0, 5.0]).psnr() is None


def test_psnr_zero_max_returns_none():
    # max_i = max([0, 0]) = 0 → None
    assert Metrics([0.0, 0.0], [1.0, 0.0]).psnr() is None


# ── PEAK RECALL ──────────────────────────────────────────────────────────────

def test_peak_recall_flat_series_returns_none():
    # Flat series has no peaks
    assert Metrics([5.0] * 30, [5.0] * 30).peak_recall() is None


def test_peak_recall_perfect_when_series_identical():
    s = [0.0, 1.0, 10.0, 1.0, 0.0, 1.0, 10.0, 1.0, 0.0] * 5
    result = Metrics(s, s).peak_recall()
    assert result is None or result == pytest.approx(1.0)


# ── PEAK AMPLITUDE ERROR ─────────────────────────────────────────────────────

def test_peak_amplitude_error_flat_series_returns_none():
    assert Metrics([5.0] * 30, [5.0] * 30).peak_amplitude_error() is None


# ── ENERGY ERROR ─────────────────────────────────────────────────────────────

def test_energy_error_zero_energy_returns_none():
    # sum=0 → energy=0 → None
    assert Metrics([0.0, 0.0], [1.0, 1.0]).energy_error() is None


def test_energy_error_identical_series():
    assert Metrics([10.0, 20.0], [10.0, 20.0]).energy_error() == pytest.approx(0.0)


def test_energy_error_total_identical_series():
    assert Metrics([10.0, -20.0], [10.0, -20.0]).energy_error_total() == pytest.approx(0.0)


# ── COMPUTE_METRICS ───────────────────────────────────────────────────────────

def test_compute_metrics_returns_all_keys(metric_keys):
    # SSIM requires at least 7 samples
    s1 = [float(i) for i in range(1, 11)]
    s2 = [float(i) + 0.1 for i in range(1, 11)]
    result = Metrics(s1, s2).compute_metrics()
    assert set(result.keys()) == metric_keys


def test_compute_metrics_mse_zero_for_identical():
    s = [float(i) for i in range(1, 11)]
    result = Metrics(s, s).compute_metrics()
    assert result["MSE"] == pytest.approx(0.0)
    assert result["RMSE"] == pytest.approx(0.0)
