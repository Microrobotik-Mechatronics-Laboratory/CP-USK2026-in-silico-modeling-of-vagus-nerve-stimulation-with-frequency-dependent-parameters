"""
src/network/bridge.py
======================
NEURON → Brian2 köprüsü ve fiber demet üreteci.

NEURON ve Brian2 ayrı simülatörlerdir ve ortak bellek paylaşmazlar.
Bu modül, NEURON'dan çıkan spike zamanlarını Brian2'nin anlayacağı
formata dönüştürür ("offline coupling" / "one-way coupling").

İçerik:
    - neuron_spikes_to_brian_group  : Tek fiber → SpikeGeneratorGroup
    - merge_fiber_populations        : Çoklu fiber → tek SpikeGeneratorGroup
    - bundle_from_single_fiber       : Tek fiberin spike zamanlarından demet oluşturur

Kaynak: nerve_frequency_study_colab.ipynb — Cell 20, Cell 26 (kısmen)
"""

from typing import Iterable, Sequence

import numpy as np
from brian2 import SpikeGeneratorGroup, ms


def neuron_spikes_to_brian_group(
    spike_times_ms: Iterable[float], n_fibers: int = 1, fiber_index: int = 0,
) -> SpikeGeneratorGroup:
    """
    Tek bir fiberin spike zamanlarını Brian2 SpikeGeneratorGroup'a dönüştürür.

    Parametreler
    ------------
    spike_times_ms : iterable of float
        Spike zamanları (ms cinsinden). NEURON'un h.Vector() çıktısından alınır.
    n_fibers : int, optional
        Toplam fiber sayısı (grup büyüklüğü). Varsayılan 1.
    fiber_index : int, optional
        Bu fiberin grup içindeki indeksi. Varsayılan 0.

    Döndürür
    --------
    brian2.SpikeGeneratorGroup
        Brian2 simülasyonuna dahil edilebilir sahte nöron grubu.

    Notlar
    ------
    SpikeGeneratorGroup gerçek denklem çözmez — yalnızca verilen zamanlarda
    spike üretir. Bu, NEURON çıktısının Brian2'ye aktarılmasının standart yoludur.
    """
    times = np.array(list(spike_times_ms)) * ms
    indices = np.full(len(times), fiber_index, dtype=int)
    return SpikeGeneratorGroup(n_fibers, indices, times)


def _build_spike_generator(
    n_fibers: int, all_times_ms: Sequence[float], all_indices: Sequence[int],
) -> SpikeGeneratorGroup:
    """
    Zaman sırasına göre sıralanmış SpikeGeneratorGroup oluşturur.

    Brian2 SpikeGeneratorGroup zaman sırasına göre sıralanmış girdi bekler;
    bu yardımcı fonksiyon argsort ile sıralamayı merkezi hale getirir.

    Parametreler
    ------------
    n_fibers : int
        Grup büyüklüğü (nöron sayısı).
    all_times_ms : list veya np.ndarray of float
        Sırasız spike zamanları (ms).
    all_indices : list veya np.ndarray of int
        all_times_ms ile aynı uzunlukta, her spike'ın hangi fibere ait
        olduğunu belirten indeksler.

    Döndürür
    --------
    brian2.SpikeGeneratorGroup
    """
    order = np.argsort(all_times_ms)
    times = np.array(all_times_ms)[order] * ms
    indices = np.array(all_indices)[order]
    return SpikeGeneratorGroup(n_fibers, indices, times)


def merge_fiber_populations(
    fiber_spike_lists: Sequence[Iterable[float]],
) -> SpikeGeneratorGroup:
    """
    Birden fazla fiberin spike zamanlarını tek bir SpikeGeneratorGroup'ta birleştirir.

    Parametreler
    ------------
    fiber_spike_lists : list of iterable
        Her eleman bir fiberin spike zamanları listesi (ms cinsinden).

    Döndürür
    --------
    brian2.SpikeGeneratorGroup
        Tüm fiberleri içeren birleşik SpikeGeneratorGroup.

    Örnek
    -----
    >>> group = merge_fiber_populations([spikes_fiber0, spikes_fiber1, spikes_fiber2])
    """
    n_fibers = len(fiber_spike_lists)
    all_times = []
    all_indices = []

    for fib_idx, spike_times_ms in enumerate(fiber_spike_lists):
        for t in spike_times_ms:
            all_times.append(t)
            all_indices.append(fib_idx)

    return _build_spike_generator(n_fibers, all_times, all_indices)


def bundle_from_single_fiber(
    spike_times_ms: Sequence[float], n_fibers: int = 20,
    jitter_ms: float = 0.4, seed: int = 0,
) -> SpikeGeneratorGroup:
    """
    Tek aksonun spike zamanlarından fiber demeti oluşturur.

    Gerçekçilik için her fibere Gauss gürültüsü (jitter) eklenir.
    Bu, gerçek sinir gövdesindeki farklı ileti hızlarını, eşikleri ve
    miyelin kalınlıklarını modellemektedir.

    Parametreler
    ------------
    spike_times_ms : iterable of float
        Referans aksonun spike zamanları (ms).
    n_fibers : int, optional
        Demet büyüklüğü. Varsayılan 20.
        Not: Gerçek vagus siniri ~80,000 lif içerir; 20 hesaplama maliyetini düşürür.
    jitter_ms : float, optional
        Her fiber için Gauss gürültüsünün standart sapması (ms). Varsayılan 0.4 ms.
        En kısa frekansın inter-spike aralığından küçük tutulmalıdır.
    seed : int, optional
        Tekrarlanabilirlik için rastgele tohum. Varsayılan 0.

    Döndürür
    --------
    brian2.SpikeGeneratorGroup
        n_fibers nöronlu SpikeGeneratorGroup; her fiber biraz farklı zamanlarda ateşler.

    Notlar
    ------
    Tek fiber → deterministik: Tüm postsinaptik nöronlar aynı anda uyarılır.
    Demet → stokastik: Popülasyon yanıtı gradüel olur — frekans duyarlılığı görünür.
    Kaynak: nerve_frequency_study_colab.ipynb — Cell 26
    """
    rng = np.random.default_rng(seed)
    all_times, all_idx = [], []
    for fib in range(n_fibers):
        jittered = np.array(spike_times_ms) + rng.normal(0, jitter_ms, size=len(spike_times_ms))
        jittered = np.clip(jittered, 0, None)
        all_times.extend(jittered.tolist())
        all_idx.extend([fib] * len(spike_times_ms))
    return _build_spike_generator(n_fibers, all_times, all_idx)
