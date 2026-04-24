import time
import pytest
from src.compressors.utils.monitor import medir_pico_memoria


def test_returns_three_tuple():
    result, t, mem = medir_pico_memoria(lambda: 42)
    assert result == 42
    assert isinstance(t, float)
    assert isinstance(mem, float)


def test_execution_time_non_negative():
    _, t, _ = medir_pico_memoria(lambda: None)
    assert t >= 0


def test_memory_mb_non_negative():
    _, _, mem = medir_pico_memoria(lambda: None)
    assert mem >= 0


def test_passes_positional_args():
    def add(a, b):
        return a + b

    result, _, _ = medir_pico_memoria(add, 3, 7)
    assert result == 10


def test_passes_keyword_args():
    def join(parts, sep=""):
        return sep.join(parts)

    result, _, _ = medir_pico_memoria(join, ["x", "y"], sep="-")
    assert result == "x-y"


def test_measures_elapsed_time():
    def slow():
        time.sleep(0.05)
        return True

    result, t, _ = medir_pico_memoria(slow)
    assert result is True
    assert t >= 0.04
