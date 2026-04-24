import pytest
from src.compressors.rdp import RDPCompressor


# ── Unit tests: RDPCompressor._dist ──────────────────────────────────────────

class TestDist:
    def setup_method(self):
        self.c = RDPCompressor(epsilon=1.0)

    def test_point_on_line_has_zero_distance(self):
        # (1,1) lies on the line (0,0)-(2,2)
        assert self.c._dist((1, 1), (0, 0), (2, 2)) == pytest.approx(0.0, abs=1e-9)

    def test_known_perpendicular_distance(self):
        # Line y=0 from (0,0) to (2,0); point (1,5) → distance = 5
        assert self.c._dist((1, 5), (0, 0), (2, 0)) == pytest.approx(5.0)

    def test_identical_endpoints_uses_vertical_distance(self):
        # a == b: falls back to |y - y1|
        assert self.c._dist((1, 3), (2, 2), (2, 2)) == pytest.approx(abs(3 - 2))


# ── Unit tests: RDPCompressor._rdp ───────────────────────────────────────────

class TestRDP:
    def test_fewer_than_three_points_returned_as_is(self):
        c = RDPCompressor(epsilon=1.0)
        pts = [(0, 0), (1, 1)]
        assert c._rdp(pts) == pts

    def test_collinear_points_keeps_only_endpoints(self):
        # (0,0), (1,1), (2,2), (3,3) all on y=x
        c = RDPCompressor(epsilon=0.5)
        result = c._rdp([(0, 0), (1, 1), (2, 2), (3, 3)])
        assert result == [(0, 0), (3, 3)]

    def test_peak_above_epsilon_is_preserved(self):
        # (1, 100) is far from the line (0,0)-(2,0) → must be kept
        c = RDPCompressor(epsilon=0.5)
        result = c._rdp([(0, 0), (1, 100), (2, 0)])
        assert len(result) == 3

    def test_epsilon_zero_preserves_non_collinear_points(self):
        # Zigzag: no intermediate point is collinear with its neighbours
        # → with epsilon=0 all points must be preserved
        c = RDPCompressor(epsilon=0.0)
        pts = [(0, 0), (1, 1), (2, 0), (3, 1), (4, 0)]
        result = c._rdp(pts)
        assert len(result) == len(pts)

    def test_large_epsilon_keeps_only_endpoints(self):
        c = RDPCompressor(epsilon=1000.0)
        pts = [(i, float(i)) for i in range(10)]
        result = c._rdp(pts)
        assert result == [pts[0], pts[-1]]


# ── Integration tests: RDPCompressor ─────────────────────────────────────────

class TestRDPCompressor:
    def test_compress_returns_correct_length(self, medium_series):
        c = RDPCompressor(epsilon=1.0)
        result = c.compress(medium_series)
        assert len(result) == len(medium_series)

    def test_compression_ratio_in_range(self, medium_series):
        c = RDPCompressor(epsilon=1.0)
        c.compress(medium_series)
        assert 0 <= c.compression_ratio <= 100

    def test_execution_time_non_negative(self, medium_series):
        c = RDPCompressor(epsilon=1.0)
        c.compress(medium_series)
        assert c.execution_time >= 0

    def test_memory_usage_non_negative(self, medium_series):
        c = RDPCompressor(epsilon=1.0)
        c.compress(medium_series)
        assert c.memory_usage_mb >= 0

    def test_metrics_contains_all_keys(self, medium_series, metric_keys):
        c = RDPCompressor(epsilon=1.0)
        c.compress(medium_series)
        assert set(c.metrics.keys()) == metric_keys

    def test_larger_epsilon_yields_higher_cr(self, medium_series):
        c_strict = RDPCompressor(epsilon=0.01)
        c_loose = RDPCompressor(epsilon=100.0)
        c_strict.compress(medium_series)
        c_loose.compress(medium_series)
        assert c_loose.compression_ratio >= c_strict.compression_ratio

    def test_constant_series_achieves_high_cr(self, constant_series):
        # Constant series: all points collinear → only endpoints kept
        c = RDPCompressor(epsilon=0.01)
        c.compress(constant_series)
        assert c.compression_ratio > 80
