import pytest
from src.compressors.sdt import SDTCompressor


# ── Unit tests: SDTCompressor._SDT ───────────────────────────────────────────

class TestSDTInner:
    def test_same_timestamp_returns_valid(self):
        # dx == 0 → returns True, None without processing
        sdt = SDTCompressor._SDT(error=5.0, first_point=(0, 100.0))
        valid, out = sdt.process((0, 100.0))
        assert valid is True
        assert out is None

    def test_constant_series_never_breaks_corridor(self):
        # Constant values within error → corridor never closes
        sdt = SDTCompressor._SDT(error=5.0, first_point=(0, 100.0))
        for i in range(1, 10):
            valid, _ = sdt.process((i, 100.0))
            assert valid is True

    def test_sharp_jump_breaks_corridor(self):
        # With error=0.1 and a large jump followed by a drop, corridor must break
        sdt = SDTCompressor._SDT(error=0.1, first_point=(0, 0.0))
        sdt.process((1, 10.0))
        ok, out = sdt.process((2, -10.0))
        assert ok is False
        assert isinstance(out, tuple)
        assert len(out) == 2

    def test_break_returns_last_inbound_point(self):
        # The returned point on break must be the last inbound point
        sdt = SDTCompressor._SDT(error=0.1, first_point=(0, 0.0))
        sdt.process((1, 10.0))  # last inbound = (1, 10.0)
        ok, out = sdt.process((2, -10.0))
        if not ok:
            assert out == (1, 10.0)


# ── Integration tests: SDTCompressor ─────────────────────────────────────────

class TestSDTCompressor:
    def test_compress_returns_correct_length(self, medium_series):
        c = SDTCompressor(error=5.0)
        result = c.compress(medium_series)
        assert len(result) == len(medium_series)

    def test_compression_ratio_in_range(self, medium_series):
        c = SDTCompressor(error=5.0)
        c.compress(medium_series)
        assert 0 <= c.compression_ratio <= 100

    def test_execution_time_non_negative(self, medium_series):
        c = SDTCompressor(error=5.0)
        c.compress(medium_series)
        assert c.execution_time >= 0

    def test_memory_usage_non_negative(self, medium_series):
        c = SDTCompressor(error=5.0)
        c.compress(medium_series)
        assert c.memory_usage_mb >= 0

    def test_metrics_contains_all_keys(self, medium_series, metric_keys):
        c = SDTCompressor(error=5.0)
        c.compress(medium_series)
        assert set(c.metrics.keys()) == metric_keys

    def test_larger_error_yields_higher_cr(self, medium_series):
        c_strict = SDTCompressor(error=0.1)
        c_loose = SDTCompressor(error=50.0)
        c_strict.compress(medium_series)
        c_loose.compress(medium_series)
        assert c_loose.compression_ratio >= c_strict.compression_ratio

    def test_constant_series_achieves_high_cr(self, constant_series):
        # Constant series: SDT keeps only first and last point → high CR
        c = SDTCompressor(error=0.1)
        c.compress(constant_series)
        assert c.compression_ratio > 80
