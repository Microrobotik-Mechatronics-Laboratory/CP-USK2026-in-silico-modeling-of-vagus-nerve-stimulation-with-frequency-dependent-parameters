"""
src/pipeline/orchestrator.py
==============================
Tek frekans ve çoklu frekans tarama orkestratörü.

Level 1 (NEURON) → Level 2-3 (Brian2) pipeline'ını tek bir fonksiyon çağrısıyla
koordine eder. main.py'nin çağırdığı ana giriş noktasıdır.

Kaynak: nerve_frequency_study_colab.ipynb — Cell 28, Cell 30
"""

from config.defaults import (
    DEFAULT_AMP,
    DEFAULT_N_FIBERS,
    DEFAULT_N_CYCLES,
    DEFAULT_MIN_MS,
    DEFAULT_MAX_MS,
    DEFAULT_FIBER_DIAM,
    DEFAULT_N_NODES,
    DEFAULT_ELEC_DIST,
    DEFAULT_ELEC_Z,
    DEFAULT_PULSE_WIDTH,
    NTS_PARAMS,
    NAC_PATHWAY_PARAMS,
    INSULA_PATHWAY_PARAMS,
    CA3_PATHWAY_PARAMS,
    DEFAULT_N_REPEATS,
    DEFAULT_SEED,
)
from typing import Any, Optional

import numpy as np
from brian2 import seed as brian_seed

from src.pipeline.level1 import run_level1
from src.pipeline.level23 import run_full_network


def cycles_to_duration_ms(
    freq_hz: float, n_cycles: int = DEFAULT_N_CYCLES,
    min_ms: float = DEFAULT_MIN_MS, max_ms: float = DEFAULT_MAX_MS,
) -> float:
    """
    Frekansa göre adaptif simülasyon süresi hesaplar.

    Sorun: 1 Hz'de 200 ms = yalnızca 0.2 döngü (anlamsız).
           500 Hz'de 1000 ms = 500 döngü (gereksiz yavaş).
    Çözüm: Her zaman en az n_cycles döngü, ama min_ms–max_ms aralığında.

    Parametreler
    ------------
    freq_hz : float
        Stimülasyon frekansı (Hz).
    n_cycles : int, optional
        Minimum döngü sayısı. Varsayılan 8.
    min_ms : float, optional
        Minimum simülasyon süresi (ms). Varsayılan 200 ms.
    max_ms : float, optional
        Maksimum simülasyon süresi (ms). Varsayılan 1000 ms.

    Döndürür
    --------
    float
        Simülasyon süresi (ms).

    Örnek
    -----
    >>> cycles_to_duration_ms(1)   # 8 döngü = 8000 ms → max_ms=1000 ile sınırlandı
    1000.0
    >>> cycles_to_duration_ms(50)  # 8 döngü = 160 ms → min_ms=200 ile yukarı çekildi
    200.0
    >>> cycles_to_duration_ms(10)  # 8 döngü = 800 ms → olduğu gibi
    800.0
    """
    return float(min(max_ms, max(min_ms, n_cycles * 1000.0 / freq_hz)))


def run_one_frequency(
    freq_hz: float, amp: float = DEFAULT_AMP, n_fibers: int = DEFAULT_N_FIBERS,
    verbose: bool = True, fiber_diam: float = DEFAULT_FIBER_DIAM,
    n_nodes: int = DEFAULT_N_NODES,
    elec_pos: tuple[float, float, float] = (DEFAULT_ELEC_DIST, 0.0, DEFAULT_ELEC_Z),
    pulse_width_ms: float = DEFAULT_PULSE_WIDTH,
    waveform: str = "rectangular",
    analysis_window_ms: Optional[float] = None,
    n_repeats: int = DEFAULT_N_REPEATS, seed: int = DEFAULT_SEED,
) -> dict[str, Any]:
    """
    Tek frekans için tam Level 1 → Level 2-3 pipeline çalıştırır.

    Parametreler
    ------------
    freq_hz : float
        Stimülasyon frekansı (Hz).
    amp : float, optional
        Uyarım genliği (µA). Varsayılan 3.0 µA.
    n_fibers : int, optional
        Fiber demet büyüklüğü. Varsayılan 20.
    verbose : bool, optional
        True ise ilerleme mesajı yazdırır. Varsayılan True.
    fiber_diam : float, optional
        MRG fiber çapı (µm). Varsayılan DEFAULT_FIBER_DIAM = 8.7 µm.
    n_nodes : int, optional
        MRG Ranvier düğümü sayısı. Varsayılan DEFAULT_N_NODES = 15.
    elec_pos : tuple(float, float, float), optional
        Elektrot konumu (µm). Varsayılan (DEFAULT_ELEC_DIST, 0, DEFAULT_ELEC_Z).
    pulse_width_ms : float, optional
        Her uyarım fazının süresi (ms). Varsayılan DEFAULT_PULSE_WIDTH = 0.1 ms.
    waveform : str, optional
        "rectangular" (bifazik kare dalga), "dc" (monofazik) veya
        "sinusoidal". Varsayılan "rectangular".
    analysis_window_ms : float, optional
        Tüm frekanslarda kullanılacak sabit simülasyon/analiz penceresi (ms).
        None ise cycles_to_duration_ms() ile frekansa göre uyarlanır.
        Frekanslar arası karşılaştırma yapılacaksa sabit pencere kullanın:
        Hz/nöron = spike / nöron / süre olduğundan, süre frekansla değişirse
        oran da mekanik olarak değişir ve gerçek bir frekans etkisiymiş gibi
        görünür.
    n_repeats : int, optional
        Level 2-3 tekrar sayısı. Varsayılan DEFAULT_N_REPEATS = 5.
    seed : int, optional
        Taban rastgele tohum. Tekrar r için `seed + r` kullanılır.

    Döndürür
    --------
    dict
        Anahtarlar:
            "freq_hz"          : float — stimülasyon frekansı
            "duration_ms"      : float — kullanılan simülasyon süresi
            "n_axon_spikes"    : int   — Level 1'de oluşan axon spike sayısı
            "n_pulses"         : int   — uygulanan uyarım pulsu sayısı
            "follow_ratio"     : float — akson spike / puls (1:1 takip oranı)
            "<bölge>"          : float — ortalama ateşleme hızı (Hz/nöron)
            "<bölge>_sd"       : float — tekrarlar arası standart sapma
            "<bölge>_n_spikes" : float — ortalama toplam spike sayısı
        Bölgeler: NTS, NAc, Insula, CA3.

    Notlar
    ------
    Eğer axon spike oluşmadıysa (amp çok düşük), tüm bölgeler 0.0 Hz döner.
    Level 1 deterministiktir; akson bir kez simüle edilip spike treni tüm
    tekrarlarda yeniden kullanılır, bu yüzden tekrar maliyeti düşüktür.
    Kaynak: nerve_frequency_study_colab.ipynb — Cell 28
    """
    duration_ms = (cycles_to_duration_ms(freq_hz) if analysis_window_ms is None
                   else analysis_window_ms)
    spikes = run_level1(
        freq_hz=freq_hz, amp=amp, duration_ms=duration_ms,
        fiber_diam=fiber_diam, n_nodes=n_nodes, elec_pos=elec_pos,
        pulse_width_ms=pulse_width_ms, waveform=waveform,
    )
    n_pulses = int(np.ceil(duration_ms * freq_hz / 1000.0))

    if verbose:
        print(f"  {freq_hz} Hz → axon spikes: {len(spikes)}", end="  ")

    regions = ("NTS", "NAc", "Insula", "CA3")
    if len(spikes) == 0:
        if verbose:
            print("(eşik altı — tüm bölgeler 0 Hz)")
        record: dict[str, Any] = {
            "freq_hz": freq_hz,
            "duration_ms": duration_ms,
            "n_axon_spikes": 0,
            "n_pulses": n_pulses,
            "follow_ratio": 0.0,
        }
        for region in regions:
            record[region] = 0.0
            record[f"{region}_sd"] = 0.0
            record[f"{region}_n_spikes"] = 0.0
        return record

    n_neurons = {
        "NTS": NTS_PARAMS["n_neurons"],
        "NAc": NAC_PATHWAY_PARAMS["n_neurons"],
        "Insula": INSULA_PATHWAY_PARAMS["n_neurons"],
        "CA3": CA3_PATHWAY_PARAMS["n_neurons"],
    }

    # Level 1 (NEURON) deterministiktir; yalnızca Level 2-3 (Brian2 bağlantı
    # örneklemesi ve fiber jitter'ı) stokastiktir. Bu yüzden akson simülasyonu
    # bir kez çalıştırılıp spike treni tekrarlar arasında yeniden kullanılır.
    per_repeat: dict[str, list[float]] = {region: [] for region in regions}
    counts: dict[str, list[float]] = {region: [] for region in regions}
    for repeat in range(n_repeats):
        brian_seed(seed + repeat)
        np.random.seed(seed + repeat)
        mons = run_full_network(spikes, duration_ms=duration_ms, n_fibers=n_fibers)
        for region, mon in mons.items():
            counts[region].append(float(mon.num_spikes))
            per_repeat[region].append(
                mon.num_spikes / n_neurons[region] / (duration_ms / 1000.0)
            )

    rates: dict[str, Any] = {}
    for region in regions:
        rates[region] = float(np.mean(per_repeat[region]))
        rates[f"{region}_sd"] = float(np.std(per_repeat[region]))
        rates[f"{region}_n_spikes"] = float(np.mean(counts[region]))

    if verbose:
        print(f"NTS={rates['NTS']:.2f} NAc={rates['NAc']:.2f} "
              f"Insula={rates['Insula']:.2f} CA3={rates['CA3']:.2f} Hz/nöron")

    rates["freq_hz"] = freq_hz
    rates["duration_ms"] = duration_ms
    rates["n_axon_spikes"] = len(spikes)
    rates["n_pulses"] = n_pulses
    rates["follow_ratio"] = len(spikes) / n_pulses if n_pulses else 0.0
    return rates


def run_frequency_sweep(
    frequencies: list[float], amp: float = DEFAULT_AMP, n_fibers: int = DEFAULT_N_FIBERS,
    verbose: bool = True, fiber_diam: float = DEFAULT_FIBER_DIAM,
    n_nodes: int = DEFAULT_N_NODES,
    elec_pos: tuple[float, float, float] = (DEFAULT_ELEC_DIST, 0.0, DEFAULT_ELEC_Z),
    pulse_width_ms: float = DEFAULT_PULSE_WIDTH,
    waveform: str = "rectangular",
    analysis_window_ms: Optional[float] = None,
    n_repeats: int = DEFAULT_N_REPEATS, seed: int = DEFAULT_SEED,
) -> list[dict[str, Any]]:
    """
    Verilen frekans listesi için tam sweep çalıştırır.

    Parametreler
    ------------
    frequencies : list of float
        Taranacak frekanslar (Hz).
    amp : float, optional
        Uyarım genliği (µA). Varsayılan 3.0 µA.
    n_fibers : int, optional
        Fiber demet büyüklüğü. Varsayılan 20.
    verbose : bool, optional
        True ise her frekans için ilerleme mesajı yazdırır.
    fiber_diam : float, optional
        MRG fiber çapı (µm). Varsayılan DEFAULT_FIBER_DIAM = 8.7 µm.
    n_nodes : int, optional
        MRG Ranvier düğümü sayısı. Varsayılan DEFAULT_N_NODES = 15.
    elec_pos : tuple(float, float, float), optional
        Elektrot konumu (µm). Varsayılan (DEFAULT_ELEC_DIST, 0, DEFAULT_ELEC_Z).
    pulse_width_ms : float, optional
        Her uyarım fazının süresi (ms). Varsayılan DEFAULT_PULSE_WIDTH = 0.1 ms.

    Döndürür
    --------
    list of dict
        Her eleman run_one_frequency() çıktısıdır.

    Örnek
    -----
    >>> records = run_frequency_sweep([1, 5, 10, 20, 50, 100, 200, 500])
    >>> import pandas as pd
    >>> df = pd.DataFrame(records)
    Kaynak: nerve_frequency_study_colab.ipynb — Cell 30
    """
    records = []
    for f in frequencies:
        if verbose:
            print(f"Çalışıyor: {f} Hz ...")
        rec = run_one_frequency(
            f, amp=amp, n_fibers=n_fibers, verbose=verbose,
            fiber_diam=fiber_diam, n_nodes=n_nodes, elec_pos=elec_pos,
            pulse_width_ms=pulse_width_ms, waveform=waveform,
            analysis_window_ms=analysis_window_ms,
            n_repeats=n_repeats, seed=seed,
        )
        records.append(rec)
    return records
