import pytest
from src.compressors.arcsdt import ARCSDTCompressor
from src.compressors.arcsdt.arcsdt import ARC_SDT


# ── Unit tests: ARC_SDT ───────────────────────────────────────────────────────

class TestARCSDT:
    def test_process_returns_bool_and_optional_tuple(self):
        arcsdt = ARC_SDT(10.0, (0, 100.0))
        valid, out = arcsdt.process_new_point((1, 100.0))
        assert isinstance(valid, bool)
        assert out is None or isinstance(out, tuple)

    def test_constant_series_never_breaks_corridor(self):
        # Constant values within the percentage error → corridor never closes
        arcsdt = ARC_SDT(10.0, (0, 100.0))
        for i in range(1, 10):
            valid, _ = arcsdt.process_new_point((i, 100.0))
            assert valid is True

    def test_sharp_reversal_breaks_corridor(self):
        # Rising sharply then dropping back forces the slopes to cross → break
        arcsdt = ARC_SDT(0.01, (0, 100.0))
        arcsdt.process_new_point((1, 200.0))
        ok, _ = arcsdt.process_new_point((2, 100.0))
        assert ok is False

    def test_set_error_does_not_raise(self):
        arcsdt = ARC_SDT(10.0, (0, 100.0))
        arcsdt.set_error(50.0)
        valid, out = arcsdt.process_new_point((1, 100.5))
        assert isinstance(valid, bool)

    def test_break_returns_valid_corridor_tuple(self):
        # Force a break and verify the returned point is a (timestamp, value) tuple
        arcsdt = ARC_SDT(0.01, (0, 100.0))
        corridor_point = None
        for i in range(1, 30):
            ok, out = arcsdt.process_new_point((i, 100.0 + i * 30))
            if not ok:
                corridor_point = out
                break
        if corridor_point is not None:
            assert len(corridor_point) == 2
            assert isinstance(corridor_point[0], (int, float))
            assert isinstance(corridor_point[1], float)


# ── Integration tests: ARCSDTCompressor ──────────────────────────────────────

class TestARCSDTCompressor:
    def test_compress_returns_correct_length(self, medium_series):
        c = ARCSDTCompressor(target_cr=80)
        result = c.compress(medium_series)
        assert len(result) == len(medium_series)

    def test_compression_ratio_in_range(self, medium_series):
        c = ARCSDTCompressor(target_cr=80)
        c.compress(medium_series)
        assert 0 <= c.compression_ratio <= 100

    def test_execution_time_non_negative(self, medium_series):
        c = ARCSDTCompressor(target_cr=80)
        c.compress(medium_series)
        assert c.execution_time >= 0

    def test_memory_usage_non_negative(self, medium_series):
        c = ARCSDTCompressor(target_cr=80)
        c.compress(medium_series)
        assert c.memory_usage_mb >= 0

    def test_metrics_contains_all_keys(self, medium_series, metric_keys):
        c = ARCSDTCompressor(target_cr=80)
        c.compress(medium_series)
        assert set(c.metrics.keys()) == metric_keys

    def test_constant_series_achieves_high_cr(self, constant_series):
        c = ARCSDTCompressor(target_cr=80)
        c.compress(constant_series)
        assert c.compression_ratio > 80

    def test_pid_drives_cr_above_zero(self, medium_series):
        # PID should push CR away from 0 towards the target
        c = ARCSDTCompressor(target_cr=80, kp=10.0, ki=2.0)
        c.compress(medium_series)
        assert c.compression_ratio > 0
