import pytest
from src.compressors.dct import DCTCompressor


# ── Integration tests: DCTCompressor ─────────────────────────────────────────

class TestDCTCompressor:
    def test_compress_returns_correct_length(self, medium_series):
        c = DCTCompressor(cr=80)
        result = c.compress(medium_series)
        assert len(result) == len(medium_series)

    def test_compression_ratio_in_range(self, medium_series):
        c = DCTCompressor(cr=80)
        c.compress(medium_series)
        assert 0 <= c.compression_ratio <= 100

    def test_execution_time_non_negative(self, medium_series):
        c = DCTCompressor(cr=80)
        c.compress(medium_series)
        assert c.execution_time >= 0

    def test_memory_usage_non_negative(self, medium_series):
        c = DCTCompressor(cr=80)
        c.compress(medium_series)
        assert c.memory_usage_mb >= 0

    def test_metrics_contains_all_keys(self, medium_series, metric_keys):
        c = DCTCompressor(cr=80)
        c.compress(medium_series)
        assert set(c.metrics.keys()) == metric_keys

    def test_higher_cr_compresses_more(self, medium_series):
        c_low = DCTCompressor(cr=20)
        c_high = DCTCompressor(cr=90)
        c_low.compress(medium_series)
        c_high.compress(medium_series)
        # Strict: with ">=" the assertion would also hold for a compressor that
        # ignored `cr` entirely and returned the same ratio for both.
        assert c_high.compression_ratio > c_low.compression_ratio

    def test_cr_zero_reconstructs_accurately(self, medium_series):
        # CR=0 spends the whole budget on coefficients (K = N - 2 here, the two
        # missing slots paying for the 12 bytes of fixed overhead), so the
        # reconstruction is accurate to float32 precision.
        c = DCTCompressor(cr=0)
        result = c.compress(medium_series)
        original_vals = [v for _, v in medium_series]
        reconstructed_vals = [v for _, v in result]
        mse = sum((a - b) ** 2 for a, b in zip(original_vals, reconstructed_vals)) / len(original_vals)
        assert mse < 1e-6

    # ── Byte cost model ──────────────────────────────────────────────────────

    @pytest.mark.parametrize("cr", [0, 20, 50, 80, 90, 99])
    def test_compression_ratio_matches_byte_model(self, medium_series, expected_transform_cr, cr):
        # Pins the model itself: raw point = 8 bytes, overhead = 12 bytes,
        # coefficient = 8 bytes. Without this, changing the model shifts every
        # reported ratio in the benchmark and no test reacts.
        c = DCTCompressor(cr=cr)
        c.compress(medium_series)
        n = len(medium_series)
        assert c.compression_ratio == pytest.approx(expected_transform_cr(n, cr, n))

    @pytest.mark.parametrize("cr", [20, 50, 80, 90])
    def test_achieved_cr_tracks_requested_cr(self, medium_series, cr):
        # The achieved ratio may only differ from the request by the rounding of a
        # single coefficient slot.
        c = DCTCompressor(cr=cr)
        c.compress(medium_series)
        assert abs(c.compression_ratio - cr) <= 1.0

    def test_keeps_largest_coefficients_not_leading_ones(self, high_frequency_series):
        # Regression guard for hard thresholding. This signal puts its energy on
        # DCT basis k=150, so keeping the *first* K coefficients would discard it
        # (RMSE ~35 against a 50-amplitude signal, i.e. total loss), while keeping
        # the K largest in magnitude recovers it almost exactly.
        c = DCTCompressor(cr=95)
        result = c.compress(high_frequency_series)
        rmse = (sum((a - b) ** 2 for (_, a), (_, b) in zip(high_frequency_series, result))
                / len(high_frequency_series)) ** 0.5
        assert rmse < 0.1

    def test_timestamps_preserved(self, medium_series):
        c = DCTCompressor(cr=80)
        result = c.compress(medium_series)
        assert [t for t, _ in result] == [t for t, _ in medium_series]
