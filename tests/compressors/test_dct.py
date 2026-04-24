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
        assert c_high.compression_ratio >= c_low.compression_ratio

    def test_cr_zero_reconstructs_accurately(self, medium_series):
        # CR=0 keeps all coefficients → reconstruction very close to original
        c = DCTCompressor(cr=0)
        result = c.compress(medium_series)
        original_vals = [v for _, v in medium_series]
        reconstructed_vals = [v for _, v in result]
        mse = sum((a - b) ** 2 for a, b in zip(original_vals, reconstructed_vals)) / len(original_vals)
        assert mse < 1.0

    def test_timestamps_preserved(self, medium_series):
        c = DCTCompressor(cr=80)
        result = c.compress(medium_series)
        assert [t for t, _ in result] == [t for t, _ in medium_series]
