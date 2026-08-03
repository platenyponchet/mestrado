import numpy as np
import pytest
import pywt

from src.compressors.wavelet import WaveletCompressor


def _n_coeffs(n_points, wavelet, level):
    """Length of the flattened coefficient array, which exceeds n_points because
    wavedec pads at the boundaries. It is the cap applied to K."""
    coeffs = pywt.wavedec(np.zeros(n_points), wavelet, level=level)
    return len(pywt.coeffs_to_array(coeffs)[0])


# ── Integration tests: WaveletCompressor ─────────────────────────────────────

class TestWaveletCompressor:
    def test_compress_returns_correct_length(self, medium_series):
        c = WaveletCompressor(wavelet="db4", level=4, cr=80)
        result = c.compress(medium_series)
        assert len(result) == len(medium_series)

    def test_compression_ratio_in_range(self, medium_series):
        c = WaveletCompressor(cr=80)
        c.compress(medium_series)
        assert 0 <= c.compression_ratio <= 100

    def test_execution_time_non_negative(self, medium_series):
        c = WaveletCompressor(cr=80)
        c.compress(medium_series)
        assert c.execution_time >= 0

    def test_memory_usage_non_negative(self, medium_series):
        c = WaveletCompressor(cr=80)
        c.compress(medium_series)
        assert c.memory_usage_mb >= 0

    def test_metrics_contains_all_keys(self, medium_series, metric_keys):
        c = WaveletCompressor(cr=80)
        c.compress(medium_series)
        assert set(c.metrics.keys()) == metric_keys

    def test_higher_cr_compresses_more(self, medium_series):
        c_low = WaveletCompressor(cr=20)
        c_high = WaveletCompressor(cr=90)
        c_low.compress(medium_series)
        c_high.compress(medium_series)
        # Strict: ">=" would also pass for a compressor that ignored `cr`.
        assert c_high.compression_ratio > c_low.compression_ratio

    def test_different_wavelets_return_correct_length(self, medium_series):
        for wavelet in ("db4", "haar", "sym4"):
            c = WaveletCompressor(wavelet=wavelet, cr=80)
            result = c.compress(medium_series)
            assert len(result) == len(medium_series), f"failed for wavelet={wavelet}"

    def test_timestamps_preserved(self, medium_series):
        c = WaveletCompressor(cr=80)
        result = c.compress(medium_series)
        assert [t for t, _ in result] == [t for t, _ in medium_series]

    # ── Byte cost model ──────────────────────────────────────────────────────

    @pytest.mark.parametrize("cr", [0, 20, 50, 80, 90, 99])
    def test_compression_ratio_matches_byte_model(self, medium_series, expected_transform_cr, cr):
        # Pins the model: raw point = 8 bytes, overhead = 12 bytes (xmin, xmax,
        # initial timestamp), coefficient = 8 bytes. The overhead used to grow with
        # `level`; it no longer does, and that change passed unnoticed.
        c = WaveletCompressor(cr=cr)
        c.compress(medium_series)
        n = len(medium_series)
        expected = expected_transform_cr(n, cr, _n_coeffs(n, "db4", 4))
        assert c.compression_ratio == pytest.approx(expected)

    @pytest.mark.parametrize("cr", [20, 50, 80, 90])
    def test_achieved_cr_tracks_requested_cr(self, medium_series, cr):
        c = WaveletCompressor(cr=cr)
        c.compress(medium_series)
        assert abs(c.compression_ratio - cr) <= 1.0

    def test_level_does_not_change_byte_budget(self, medium_series):
        # The slice structure is derivable from (wavelet, level, N) and is not
        # transmitted, so the level must not move the byte budget.
        ratios = []
        for level in (1, 2, 3, 4):
            c = WaveletCompressor(level=level, cr=80)
            c.compress(medium_series)
            ratios.append(c.compression_ratio)
        assert ratios == [pytest.approx(ratios[0])] * len(ratios)

    def test_level_changes_reconstruction_quality(self, medium_series):
        # Same byte budget, very different fidelity: a single decomposition level
        # cannot concentrate the energy of a smooth signal into few coefficients.
        c_shallow = WaveletCompressor(level=1, cr=80)
        c_deep = WaveletCompressor(level=3, cr=80)
        c_shallow.compress(medium_series)
        c_deep.compress(medium_series)
        assert c_deep.metrics["RMSE"] < c_shallow.metrics["RMSE"]

    def test_experiment_configuration_is_covered(self, medium_series, expected_transform_cr):
        # experiment.py runs level=3, not the class default of 4.
        c = WaveletCompressor(cr=80, wavelet="db4", level=3)
        result = c.compress(medium_series)
        n = len(medium_series)
        assert len(result) == n
        assert c.compression_ratio == pytest.approx(expected_transform_cr(n, 80, _n_coeffs(n, "db4", 3)))
