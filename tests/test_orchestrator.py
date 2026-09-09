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


# ---------------------------------------------------------------------------
# Parametre zinciri regresyon testleri (BUG-001)
#
# main.py --fiber-diam/--n-nodes/--elec-dist/--pulse-width bayrakları bir
# zamanlar parse edilip run_level1()'e hiç iletilmiyordu; simülasyon sessizce
# kendi varsayılanlarıyla çalışıyordu. Aşağıdaki testler run_level1 ve
# run_full_network'ü sahte fonksiyonlarla değiştirerek (NEURON/Brian2
# çalıştırmadan) zincirin bozulmadığını doğrular.
# ---------------------------------------------------------------------------

class _FakeMonitor:
    """SpikeMonitor yerine geçen, yalnızca num_spikes sunan sahte nesne."""

    def __init__(self, num_spikes: int) -> None:
        self.num_spikes = num_spikes


@pytest.fixture
def captured_level1(monkeypatch):
    """
    run_level1 ve run_full_network'ü sahte sürümlerle değiştirir.

    Döndürür
    --------
    dict
        run_level1'e iletilen anahtar kelime argümanları (çağrıdan sonra dolar).
    """
    from src.pipeline import orchestrator

    captured: dict = {}

    def fake_run_level1(**kwargs):
        captured.update(kwargs)
        return [1.0, 2.0, 3.0]  # boş olmayan spike listesi — pipeline devam etsin

    def fake_run_full_network(spike_times_ms, duration_ms, n_fibers=20):
        return {
            "NTS": _FakeMonitor(30), "NAc": _FakeMonitor(100),
            "Insula": _FakeMonitor(100), "CA3": _FakeMonitor(100),
        }

    monkeypatch.setattr(orchestrator, "run_level1", fake_run_level1)
    monkeypatch.setattr(orchestrator, "run_full_network", fake_run_full_network)
    return captured


def test_run_one_frequency_forwards_stim_params(captured_level1):
    from src.pipeline.orchestrator import run_one_frequency

    run_one_frequency(
        20.0, amp=5.0, n_fibers=10, verbose=False,
        fiber_diam=12.8, n_nodes=21, elec_pos=(800.0, 0.0, 3000.0),
        pulse_width_ms=0.2,
    )

    assert captured_level1["amp"] == 5.0
    assert captured_level1["fiber_diam"] == 12.8
    assert captured_level1["n_nodes"] == 21
    assert captured_level1["elec_pos"] == (800.0, 0.0, 3000.0)
    assert captured_level1["pulse_width_ms"] == 0.2


def test_run_frequency_sweep_forwards_stim_params(captured_level1):
    from src.pipeline.orchestrator import run_frequency_sweep

    run_frequency_sweep(
        [50.0], amp=1.5, n_fibers=10, verbose=False,
        fiber_diam=5.7, n_nodes=9, elec_pos=(250.0, 0.0, 1000.0),
        pulse_width_ms=0.05,
    )

    assert captured_level1["amp"] == 1.5
    assert captured_level1["fiber_diam"] == 5.7
    assert captured_level1["n_nodes"] == 9
    assert captured_level1["elec_pos"] == (250.0, 0.0, 1000.0)
    assert captured_level1["pulse_width_ms"] == 0.05


def test_run_one_frequency_defaults_come_from_config(captured_level1):
    from config.defaults import (
        DEFAULT_FIBER_DIAM, DEFAULT_N_NODES, DEFAULT_ELEC_DIST,
        DEFAULT_ELEC_Z, DEFAULT_PULSE_WIDTH,
    )
    from src.pipeline.orchestrator import run_one_frequency

    run_one_frequency(20.0, verbose=False)

    assert captured_level1["fiber_diam"] == DEFAULT_FIBER_DIAM
    assert captured_level1["n_nodes"] == DEFAULT_N_NODES
    assert captured_level1["elec_pos"] == (DEFAULT_ELEC_DIST, 0.0, DEFAULT_ELEC_Z)
    assert captured_level1["pulse_width_ms"] == DEFAULT_PULSE_WIDTH


# ---------------------------------------------------------------------------
# Hz/nöron normalizasyonu regresyon testi (BUG-002)
#
# n_neurons sözlüğü bir zamanlar elle kopyalanmış sabitlerden geliyordu;
# config'teki bir popülasyon büyüklüğü değişirse oranlar sessizce yanlış
# hesaplanıyordu. Bu test, config değiştiğinde hesabın da değiştiğini doğrular.
# ---------------------------------------------------------------------------

def test_rates_use_config_population_sizes(captured_level1, monkeypatch):
    from src.pipeline import orchestrator
    from src.pipeline.orchestrator import run_one_frequency

    # NTS popülasyonunu 30 -> 60'a çıkar; aynı spike sayısı yarı hıza karşılık gelmeli
    monkeypatch.setitem(orchestrator.NTS_PARAMS, "n_neurons", 60)

    result = run_one_frequency(20.0, verbose=False)

    # duration_ms = 400 ms (8 döngü / 20 Hz), sahte monitör 30 spike veriyor
    # 30 spike / 60 nöron / 0.4 s = 1.25 Hz/nöron
    assert result["NTS"] == pytest.approx(30 / 60 / 0.4)
