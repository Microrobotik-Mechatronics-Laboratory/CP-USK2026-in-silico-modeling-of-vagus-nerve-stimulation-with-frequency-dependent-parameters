"""
src/pipeline/level1.py
=======================
Level 1 pipeline — NEURON simülatörü ile MRG akson uyarımı.

Tek bir MRG aksonunu verilen frekans ve genlikte uyarır; distal düğümdeki
spike zamanlarını döndürür. Bu spike zamanları Level 2-3 (Brian2) girdisidir.

Kaynak: nerve_frequency_study_colab.ipynb — Cell 24
"""

from neuron import h

from config.defaults import (
    DEFAULT_DT,
    DEFAULT_PULSE_WIDTH,
    DEFAULT_N_NODES,
    DEFAULT_FIBER_DIAM,
)
from src.models.mrg_axon import MRGAxon
from src.stim.extracellular_field import biphasic_waveform, apply_extracellular_field


def run_level1(freq_hz=20, amp=1.0, duration_ms=200, dt=DEFAULT_DT,
               fiber_diam=DEFAULT_FIBER_DIAM, n_nodes=DEFAULT_N_NODES,
               elec_pos=(500.0, 0.0, 3000.0)):
    """
    Level 1: NEURON MRG aksonunu uyarır ve distal spike zamanlarını döndürür.

    Pipeline'ın ilk aşaması. NEURON simülatörü, periferik sinirin biyofiziksel
    davranışını (iyon kanalları, kablo denklemi) çözer.

    Parametreler
    ------------
    freq_hz : float, optional
        Uyarım frekansı (Hz). Varsayılan 20 Hz.
    amp : float, optional
        Uyarım genliği (µA). Varsayılan 1.0 µA.
    duration_ms : float, optional
        Simülasyon süresi (ms). Varsayılan 200 ms.
    dt : float, optional
        Zaman adımı (ms). Varsayılan 0.005 ms = 5 µs.
    fiber_diam : float, optional
        MRG fiber çapı (µm). Varsayılan 8.7 µm (Aβ fiber).
    n_nodes : float, optional
        MRG düğüm sayısı. Varsayılan 15 (hız/doğruluk dengesi).
        Not: Klasik MRG 21 düğüm kullanır; 15 daha hızlıdır.
    elec_pos : tuple(float, float, float), optional
        Elektrot konumu (µm). Varsayılan: aksonun ortasına yakın (z=3000 µm).

    Döndürür
    --------
    list of float
        Distal düğümdeki spike zamanları (ms).
        Boş liste: uyarım eşiğin altında (spike yok).

    Notlar
    ------
    h.finitialize(-65): V=-65 mV, tüm iyon kanalı durumları sıfırlanır.
    h.fadvance(): Tek dt adımı; iyon kanalları + kablo denklemi + membran potansiyeli.
    Elektrot z=3000 µm: aksonun ortasına yakın — en etkili uyarım noktası.
    """
    fiber = MRGAxon(diameter_um=fiber_diam, n_nodes=n_nodes)
    coords = fiber.section_coords()
    sections = fiber.all_sections()
    spikes = fiber.record_last_node_spikes()

    t_vec, i_vec = biphasic_waveform(
        freq_hz, amp, duration_ms, dt,
        pulse_width_ms=DEFAULT_PULSE_WIDTH,
        waveform="rectangular",
    )

    h.dt = dt
    h.finitialize(-65)  # Dinlenme potansiyeli: V=-65 mV, kanallar kapalı

    for i_t in i_vec:
        apply_extracellular_field(sections, coords, elec_pos, i_t)
        h.fadvance()  # Bir zaman adımı ilerle (Crank-Nicolson integrasyon)

    return list(spikes)
