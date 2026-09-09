"""
tests/test_bridge.py
=====================
src/network/bridge.py::bundle_from_single_fiber için refrakter periyot ve
Brian2 zaman ızgarası testleri.

Yüksek frekanslı uyarımda (>= 1 kHz) jitter eklenmiş spike'lar aynı dt
kutusuna düşüp Brian2'yi çökertiyordu; bu testler regresyonu önler.
"""

import numpy as np

from config.defaults import AXON_REFRACTORY_MS, DEFAULT_BRIAN_DT_MS
from src.network.bridge import bundle_from_single_fiber


def _times_by_fiber(group, n_fibers):
    times = np.asarray(group._spike_time) * 1000.0  # s -> ms
    index = np.asarray(group._neuron_index)
    return [np.sort(times[index == f]) for f in range(n_fibers)]


def test_bundle_enforces_refractory_period():
    # 10 kHz'e denk yoğun tren: 0.1 ms aralıklı 1000 spike
    spikes = list(np.arange(0.0, 100.0, 0.1))
    n_fibers = 5
    group = bundle_from_single_fiber(spikes, n_fibers=n_fibers, jitter_ms=0.4, seed=1)

    for fiber_times in _times_by_fiber(group, n_fibers):
        if fiber_times.size > 1:
            assert np.diff(fiber_times).min() >= AXON_REFRACTORY_MS - 1e-9


def test_bundle_snaps_to_brian_dt_grid():
    spikes = list(np.arange(0.0, 50.0, 0.1))
    n_fibers = 4
    group = bundle_from_single_fiber(spikes, n_fibers=n_fibers, jitter_ms=0.4, seed=2)

    for fiber_times in _times_by_fiber(group, n_fibers):
        bins = np.floor(fiber_times / DEFAULT_BRIAN_DT_MS).astype(np.int64)
        assert bins.size == np.unique(bins).size  # kutu başına en fazla bir spike


def test_bundle_low_frequency_keeps_all_spikes():
    # 20 Hz: ISI 50 ms >> refrakter periyot, hiçbir spike elenmemeli
    spikes = [0.0, 50.0, 100.0, 150.0]
    n_fibers = 3
    group = bundle_from_single_fiber(spikes, n_fibers=n_fibers, jitter_ms=0.4, seed=3)

    for fiber_times in _times_by_fiber(group, n_fibers):
        assert fiber_times.size == len(spikes)


def test_bundle_empty_input_returns_empty_group():
    group = bundle_from_single_fiber([], n_fibers=6, seed=0)
    assert group.N == 6
    assert np.asarray(group._spike_time).size == 0
