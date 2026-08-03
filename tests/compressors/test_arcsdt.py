import math

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
        # Force a break and verify the returned point is a (timestamp, value) tuple.
        # The previous version fed a perfectly straight ramp (100 + i*30), which the
        # corridor never breaks, so the guarded assertions never ran at all.
        arcsdt = ARC_SDT(0.01, (0, 100.0))
        arcsdt.process_new_point((1, 200.0))
        ok, corridor_point = arcsdt.process_new_point((2, 100.0))

        assert ok is False
        assert corridor_point is not None
        assert len(corridor_point) == 2
        assert isinstance(corridor_point[0], (int, float))
        assert isinstance(corridor_point[1], float)

    def test_break_returns_the_last_inbound_point(self):
        # The anchor emitted on a break is the last point still inside the corridor.
        arcsdt = ARC_SDT(0.01, (0, 100.0))
        arcsdt.process_new_point((1, 200.0))
        _, corridor_point = arcsdt.process_new_point((2, 100.0))
        assert corridor_point == (1, 200.0)

    def test_min_absolute_error_floors_the_corridor(self):
        # tolerancia = max(rms * tol_rel / 100, min_absolute_error). With tol_rel at
        # 0.01% the relative term is negligible, so min_absolute_error alone decides
        # whether small oscillations are absorbed. The default moved from 1 to 0.001
        # and nothing caught it: the same series goes from 0 breaks to 46.
        series = [(i, 100.0 + 0.5 * math.sin(i)) for i in range(1, 50)]

        def count_breaks(min_absolute_error):
            arcsdt = ARC_SDT(0.01, (0, 100.0), min_absolute_error=min_absolute_error)
            return sum(1 for p in series if not arcsdt.process_new_point(p)[0])

        assert count_breaks(1.0) == 0
        assert count_breaks(0.001) > 40

    def test_default_min_absolute_error_does_not_absorb_small_ripple(self):
        # Guards the default value itself, not just the parameter.
        series = [(i, 100.0 + 0.5 * math.sin(i)) for i in range(1, 50)]
        arcsdt = ARC_SDT(0.01, (0, 100.0))
        assert sum(1 for p in series if not arcsdt.process_new_point(p)[0]) > 40


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

    # ── PID control loop ─────────────────────────────────────────────────────

    @pytest.mark.parametrize("target_cr", [20, 50, 80, 90])
    def test_pid_converges_to_target(self, noisy_series, target_cr):
        # The central claim of ARC-SDT: the controller drives the achieved CR to the
        # requested one without the caller having to tune tol_rel by hand. Runs on
        # the default gains on purpose — the old test hardcoded kp=10, ki=2, which
        # stopped being the defaults in June, so retuning the controller could not
        # break it.
        c = ARCSDTCompressor(target_cr=target_cr)
        c.compress(noisy_series)
        assert abs(c.compression_ratio - target_cr) <= 3.0

    def test_pid_converges_with_explicit_default_gains(self, noisy_series):
        # Same result whether the gains are omitted or passed explicitly, which is
        # what makes the parametrized test above a real check on the defaults.
        c_implicit = ARCSDTCompressor(target_cr=80)
        c_explicit = ARCSDTCompressor(target_cr=80, kp=32.0, ki=1.0, kd=0.0)
        c_implicit.compress(noisy_series)
        c_explicit.compress(noisy_series)
        assert c_implicit.compression_ratio == pytest.approx(c_explicit.compression_ratio)

    def test_pid_does_not_overshoot_target(self, noisy_series):
        # Overshoot widens the corridor beyond what was asked and silently drops
        # demand peaks; undershoot only costs a slightly larger payload. The gains
        # are tuned to prefer undershoot, so overshoot must stay small.
        c = ARCSDTCompressor(target_cr=80)
        c.compress(noisy_series)
        assert c.compression_ratio - 80 <= 1.0

    def test_smooth_series_saturates_the_controller(self, medium_series):
        # Documents why `noisy_series` exists. On a highly compressible signal the
        # PID output hits the lower bound of output_limits and the achieved CR stops
        # following the target: asking for 20 still yields well above 80.
        c = ARCSDTCompressor(target_cr=20)
        c.compress(medium_series)
        assert c.compression_ratio > 80
