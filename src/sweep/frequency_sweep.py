"""
src/sweep/frequency_sweep.py
=============================
Frekans tarama protokolü — aktivasyon ve KHFAC blok eşiklerini frekans boyunca tarar.

Logaritmik dağılım kullanılır çünkü sinir sistemi logaritmik ölçekte çalışır
(Weber-Fechner yasası).

İki mod:
    - "activation": Düşük frekanslarda (1 – 500 Hz) aktivasyon eşiği.
    - "block"     : Yüksek frekanslarda (1 – 50 kHz, KHFAC) iletim blok eşiği.

Bu modül `main.py` CLI pipeline'ına entegre değildir (yalnızca
`default_frequency_range()` `--full-range` bayrağı için kullanılır);
`sweep_fiber()` ve ilişkili eşik-bulma fonksiyonları (`find_threshold`,
`verify_bracket`) bağımsız/isteğe bağlı bir analiz aracı olarak kasıtlı
olarak ayrı tutuluyor — sabit genlikle sweep yapan `run_frequency_sweep()`
(orchestrator.py) ana pipeline'dır, bu modül alternatif bir eşik-frekans
analizi sunar.

Kaynak: nerve_frequency_study_colab.ipynb — Cell 16
"""

from typing import Any, Callable, Optional

import numpy as np

from config.defaults import (
    ELECTRODE_POS,
    LOW_FREQ_RANGE,
    HIGH_FREQ_RANGE,
    DEFAULT_PULSE_WIDTH,
    DEFAULT_DT,
    DEFAULT_V_INIT_MV,
)
from src.stim.extracellular_field import biphasic_waveform, run_stimulation_loop
from src.analysis.threshold_finder import find_threshold, verify_bracket


# ---------------------------------------------------------------------------
# İç yardımcı fonksiyonlar
# ---------------------------------------------------------------------------

def _record_spikes(fiber: Any) -> Any:
    """
    Fiber tipine uygun spike kaydı metodunu çağırır.

    MRGAxon.record_last_node_spikes() veya CFiber.record_distal_spikes() —
    ikisi de aynı imzayı (h.Vector döner) paylaşır ama farklı isimlendirilmiş.

    Parametreler
    ------------
    fiber : MRGAxon veya CFiber

    Döndürür
    --------
    h.Vector
        Spike zamanları.
    """
    if hasattr(fiber, "record_last_node_spikes"):
        return fiber.record_last_node_spikes()
    return fiber.record_distal_spikes()


def _run_activation_trial(
    fiber: Any, amp: float, freq_hz: float, duration_ms: float = 50, dt: float = DEFAULT_DT,
) -> bool:
    """
    Tek bir aktivasyon denemesi çalıştırır.

    Verilen amp değeriyle biphasic uyarım uygular ve distal düğümde
    en az bir spike oluşup oluşmadığını döndürür.

    Parametreler
    ------------
    fiber : MRGAxon or CFiber
        Simüle edilecek akson nesnesi.
    amp : float
        Uyarım genliği (µA).
    freq_hz : float
        Uyarım frekansı (Hz).
    duration_ms : float, optional
        Simülasyon süresi (ms). Varsayılan 50 ms.
    dt : float, optional
        Zaman adımı (ms). Varsayılan 0.005 ms = 5 µs.

    Döndürür
    --------
    bool
        True: En az bir spike oluştu (aktivasyon başarılı).
    """
    coords = fiber.section_coords()
    sections = fiber.all_sections()
    spikes = _record_spikes(fiber)

    t_vec, i_vec = biphasic_waveform(
        freq_hz, amp, duration_ms, dt,
        pulse_width_ms=DEFAULT_PULSE_WIDTH,
        waveform="rectangular",
    )
    run_stimulation_loop(sections, coords, ELECTRODE_POS, i_vec, dt, v_init=DEFAULT_V_INIT_MV)

    return spikes.size() > 0


def _run_block_trial(
    fiber: Any, amp: float, freq_hz: float, block_duration_ms: float = 200, dt: float = DEFAULT_DT,
    test_pulse_time_ms: float = 50, test_pulse_amp: float = 2.0,
) -> bool:
    """
    Tek bir KHFAC blok denemesi çalıştırır.

    Protokol:
        1. Yüksek frekanslı sinüsoidal akım başlat (KHFAC).
        2. test_pulse_time_ms bekle (Na+ kanallarının inaktive olması için).
        3. Bir test pulsu gönder (normal koşullarda spike oluşturması beklenen güçte).
        4. Test pulsu spike oluşturamadıysa → blok başarılı!

    Parametreler
    ------------
    fiber : MRGAxon or CFiber
        Simüle edilecek akson nesnesi.
    amp : float
        KHFAC akım genliği (µA).
    freq_hz : float
        KHFAC frekansı (Hz) — tipik olarak 1000 – 50,000 Hz.
    block_duration_ms : float, optional
        Toplam simülasyon süresi (ms). Varsayılan 200 ms.
    dt : float, optional
        Zaman adımı (ms). Varsayılan 0.005 ms.
    test_pulse_time_ms : float, optional
        Test pulsunun uygulanacağı zaman (ms). Varsayılan 50 ms.
    test_pulse_amp : float, optional
        Test pulsunun genliği (µA). Varsayılan 2.0 µA.

    Döndürür
    --------
    bool
        True: Blok başarılı (test pulsu spike üretemedi).
    """
    coords = fiber.section_coords()
    sections = fiber.all_sections()
    spikes = _record_spikes(fiber)

    t_vec, i_khfac = biphasic_waveform(
        freq_hz, amp, block_duration_ms, dt, waveform="sinusoidal"
    )
    _, i_test = biphasic_waveform(
        10, test_pulse_amp, block_duration_ms, dt,
        pulse_width_ms=DEFAULT_PULSE_WIDTH, waveform="rectangular"
    )

    # Test pulsunu yalnızca test_pulse_time_ms sonrasında ekle
    test_mask = t_vec >= test_pulse_time_ms
    i_combined = i_khfac.copy()
    i_combined[test_mask] += i_test[test_mask]

    run_stimulation_loop(sections, coords, ELECTRODE_POS, i_combined, dt, v_init=DEFAULT_V_INIT_MV)

    # Blok başarılıysa test pulse sonrasında spike yok
    return spikes.size() == 0


# ---------------------------------------------------------------------------
# Genel arayüz
# ---------------------------------------------------------------------------

def default_frequency_range() -> list[float]:
    """
    Varsayılan frekans aralığını döndürür.

    Düşük frekanslar (aktivasyon, 1 – 500 Hz) + yüksek frekanslar (KHFAC blok, 1 – 50 kHz).

    Döndürür
    --------
    list of float
        Sıralanmış frekans listesi (Hz).
    """
    return sorted(LOW_FREQ_RANGE + HIGH_FREQ_RANGE)


def sweep_fiber(
    fiber_builder: Callable[..., Any], diameter: float,
    frequencies_hz: Optional[list[float]] = None, mode: str = "activation",
    amp_low: float = 0.01, amp_high: float = 5.0,
) -> list[dict[str, Any]]:
    """
    Verilen fiber tipi ve çapı için frekans boyunca eşik taraması yapar.

    Her frekans için:
        1. Yeni bir fiber oluştur (temiz durum).
        2. Bisection aralığını doğrula (verify_bracket).
        3. Eşiği bul (find_threshold).
        4. Sonuçları kaydet.

    Parametreler
    ------------
    fiber_builder : callable
        f(diameter_um=float) → fiber nesnesi döndüren factory fonksiyonu.
        Örnek: lambda d: MRGAxon(diameter_um=d, n_nodes=15)
    diameter : float
        Fiber çapı (µm). fiber_builder'a iletilir.
    frequencies_hz : list of float, optional
        Taranacak frekanslar (Hz). None ise default_frequency_range() kullanılır.
    mode : str, optional
        "activation" (varsayılan) veya "block" (KHFAC).
    amp_low : float, optional
        Bisection alt sınırı (µA). Varsayılan 0.01 µA.
    amp_high : float, optional
        Bisection üst sınırı başlangıcı (µA). Varsayılan 5.0 µA.

    Döndürür
    --------
    list of dict
        Her eleman: {"freq_hz": float, "threshold_uA": float or None}

    Uyarı
    -----
    Tam tarama (tüm frekanslar × iki fiber tipi × birden fazla çap) saatler alabilir.
    Hızlı test için küçük bir frekans listesi kullanın.
    """
    if frequencies_hz is None:
        frequencies_hz = default_frequency_range()

    results = []
    for freq_hz in frequencies_hz:
        fiber = fiber_builder(diameter_um=diameter)

        if mode == "activation":
            trial_fn = lambda amp, f=freq_hz: _run_activation_trial(fiber, amp, f)
        else:
            trial_fn = lambda amp, f=freq_hz: _run_block_trial(fiber, amp, f)

        bracket = verify_bracket(trial_fn, amp_low, amp_high)
        if bracket is None:
            threshold = None
        else:
            lo, hi = bracket
            threshold = find_threshold(trial_fn, lo, hi)

        results.append({"freq_hz": freq_hz, "threshold_uA": threshold})
        print(f"  {freq_hz:>6} Hz → eşik = {threshold:.4f} µA" if threshold else
              f"  {freq_hz:>6} Hz → eşik bulunamadı")

    return results
