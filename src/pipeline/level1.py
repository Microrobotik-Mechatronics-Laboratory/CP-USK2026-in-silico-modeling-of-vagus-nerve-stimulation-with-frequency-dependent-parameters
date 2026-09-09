"""
src/pipeline/level1.py
=======================
Level 1 pipeline — NEURON simülatörü ile MRG akson uyarımı.

Tek bir MRG aksonunu verilen frekans ve genlikte uyarır; distal düğümdeki
spike zamanlarını döndürür. Bu spike zamanları Level 2-3 (Brian2) girdisidir.

Kaynak: nerve_frequency_study_colab.ipynb — Cell 24
"""

from config.defaults import (
    DEFAULT_DT,
    DEFAULT_PULSE_WIDTH,
    DEFAULT_N_NODES,
    DEFAULT_FIBER_DIAM,
    DEFAULT_ELEC_DIST,
    DEFAULT_ELEC_Z,
    DEFAULT_V_INIT_MV,
)
from src.models.mrg_axon import MRGAxon
from src.stim.extracellular_field import biphasic_waveform, run_stimulation_loop


def run_level1(
    freq_hz: float = 20, amp: float = 1.0, duration_ms: float = 200, dt: float = DEFAULT_DT,
    fiber_diam: float = DEFAULT_FIBER_DIAM, n_nodes: int = DEFAULT_N_NODES,
    elec_pos: tuple[float, float, float] = (DEFAULT_ELEC_DIST, 0.0, DEFAULT_ELEC_Z),
    pulse_width_ms: float = DEFAULT_PULSE_WIDTH,
    waveform: str = "rectangular",
) -> list[float]:
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
        Elektrot konumu (µm). Varsayılan: config/defaults.py'deki
        (DEFAULT_ELEC_DIST, 0, DEFAULT_ELEC_Z) — aksonun ortasına yakın (z=3000 µm).
    pulse_width_ms : float, optional
        Her uyarım fazının süresi (ms). Varsayılan: DEFAULT_PULSE_WIDTH = 0.1 ms.
    waveform : str, optional
        "rectangular" (bifazik, yük dengeli), "dc" (monofazik) veya
        "sinusoidal" (KHFAC). Varsayılan "rectangular".

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
        pulse_width_ms=pulse_width_ms,
        waveform=waveform,
    )

    run_stimulation_loop(sections, coords, elec_pos, i_vec, dt, v_init=DEFAULT_V_INIT_MV)

    return list(spikes)
