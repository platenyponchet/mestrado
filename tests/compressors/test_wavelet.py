import pytest
from src.compressors.wavelet import WaveletCompressor


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
        assert c_high.compression_ratio >= c_low.compression_ratio

    def test_different_wavelets_return_correct_length(self, medium_series):
        for wavelet in ("db4", "haar", "sym4"):
            c = WaveletCompressor(wavelet=wavelet, cr=80)
            result = c.compress(medium_series)
            assert len(result) == len(medium_series), f"failed for wavelet={wavelet}"

    def test_timestamps_preserved(self, medium_series):
        c = WaveletCompressor(cr=80)
        result = c.compress(medium_series)
        assert [t for t, _ in result] == [t for t, _ in medium_series]
