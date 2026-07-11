"""
tests/test_orchestrator.py
============================
src/pipeline/orchestrator.py::cycles_to_duration_ms için sınır değer testleri.

Not: cycles_to_duration_ms() kendisi saf aritmetiktir, ama bu modül
orchestrator.py'yi import eder ve orchestrator.py modül seviyesinde
level1/level23'ü (dolayısıyla NEURON + Brian2) import eder. Bu yüzden bu
test dosyası da NEURON/Brian2 kurulu olmasını gerektirir.
"""

import pytest

from src.pipeline.orchestrator import cycles_to_duration_ms


def test_cycles_to_duration_ms_low_freq_capped_at_max():
    # 1 Hz, 8 döngü = 8000 ms -> max_ms=1000 ile sınırlandı
    assert cycles_to_duration_ms(1, n_cycles=8, min_ms=200, max_ms=1000) == 1000.0


def test_cycles_to_duration_ms_high_freq_floored_at_min():
    # 50 Hz, 8 döngü = 160 ms -> min_ms=200 ile yukarı çekildi
    assert cycles_to_duration_ms(50, n_cycles=8, min_ms=200, max_ms=1000) == 200.0


def test_cycles_to_duration_ms_mid_range_uses_formula():
    # 10 Hz, 8 döngü = 800 ms -> [200, 1000] aralığında, olduğu gibi kullanılır
    assert cycles_to_duration_ms(10, n_cycles=8, min_ms=200, max_ms=1000) == 800.0


def test_cycles_to_duration_ms_default_args_match_config():
    from config.defaults import DEFAULT_N_CYCLES, DEFAULT_MIN_MS, DEFAULT_MAX_MS
    assert cycles_to_duration_ms(1) == pytest.approx(
        min(DEFAULT_MAX_MS, max(DEFAULT_MIN_MS, DEFAULT_N_CYCLES * 1000.0 / 1))
    )
