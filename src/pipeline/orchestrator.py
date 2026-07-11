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
)
from typing import Any

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
    verbose: bool = True,
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

    Döndürür
    --------
    dict
        Anahtarlar:
            "freq_hz"       : float — stimülasyon frekansı
            "duration_ms"   : float — kullanılan simülasyon süresi
            "n_axon_spikes" : int   — Level 1'de oluşan axon spike sayısı
            "NTS"           : float — NTS ortalama ateşleme hızı (Hz/nöron)
            "NAc"           : float — NAc ortalama ateşleme hızı (Hz/nöron)
            "Insula"        : float — İnsula ortalama ateşleme hızı (Hz/nöron)
            "CA3"           : float — CA3 ortalama ateşleme hızı (Hz/nöron)

    Notlar
    ------
    Eğer axon spike oluşmadıysa (amp çok düşük), tüm bölgeler 0.0 Hz döner.
    Stokastik çalışma: Her çağrı farklı sonuç verebilir.
    Güvenilir sonuç için 5-10 tekrar yapıp ortalamasını alın.
    Kaynak: nerve_frequency_study_colab.ipynb — Cell 28
    """
    duration_ms = cycles_to_duration_ms(freq_hz)
    spikes = run_level1(freq_hz=freq_hz, amp=amp, duration_ms=duration_ms)

    if verbose:
        print(f"  {freq_hz} Hz → axon spikes: {len(spikes)}", end="  ")

    if len(spikes) == 0:
        if verbose:
            print("(eşik altı — tüm bölgeler 0 Hz)")
        return {
            "freq_hz": freq_hz,
            "duration_ms": duration_ms,
            "n_axon_spikes": 0,
            "NTS": 0.0, "NAc": 0.0, "Insula": 0.0, "CA3": 0.0,
        }

    mons = run_full_network(spikes, duration_ms=duration_ms, n_fibers=n_fibers)

    n_neurons = {"NTS": 30, "NAc": 100, "Insula": 100, "CA3": 100}
    rates = {
        region: mon.num_spikes / n_neurons[region] / (duration_ms / 1000.0)
        for region, mon in mons.items()
    }

    if verbose:
        print(f"NTS={rates['NTS']:.2f} NAc={rates['NAc']:.2f} "
              f"Insula={rates['Insula']:.2f} CA3={rates['CA3']:.2f} Hz/nöron")

    rates["freq_hz"] = freq_hz
    rates["duration_ms"] = duration_ms
    rates["n_axon_spikes"] = len(spikes)
    return rates


def run_frequency_sweep(
    frequencies: list[float], amp: float = DEFAULT_AMP, n_fibers: int = DEFAULT_N_FIBERS,
    verbose: bool = True,
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
        rec = run_one_frequency(f, amp=amp, n_fibers=n_fibers, verbose=verbose)
        records.append(rec)
    return records
