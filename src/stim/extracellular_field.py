"""
src/stim/extracellular_field.py
================================
Ekstrasellüler alan hesaplama ve uyarım dalga formu üreteci.

İçerik:
    - point_source_potential  : Noktasal akım kaynağının oluşturduğu potansiyel (McNeal 1976 / Rattay 1986)
    - biphasic_waveform       : Biphasic veya sinüsoidal (KHFAC) dalga formu üreteci
    - apply_extracellular_field : Hesaplanan potansiyeli NEURON aksonuna uygular

Kaynak: nerve_frequency_study_colab.ipynb — Cell 8
"""

from typing import Any

import numpy as np

# rho [Ω·cm] * I [µA] / r [cm] çarpımı Ω·µA = 1e-6 V = 1e-3 mV verir.
# NEURON'un e_extracellular alanı mV beklediği için bu dönüşüm zorunludur.
_UV_TO_MV: float = 1e-3


def point_source_potential(
    x: float, y: float, z: float,
    elec_pos: tuple[float, float, float],
    current: float, rho: float = 300.0,
) -> float:
    """
    Noktasal akım kaynağının oluşturduğu ekstrasellüler potansiyeli hesaplar.

    Fizik arka planı — Coulomb Yasası'nın elektrofizyolojik versiyonu:
        V_e = (rho * I) / (4 * pi * r)

    Parametreler
    ------------
    x, y, z : float
        Ölçüm noktasının koordinatları (µm cinsinden).
    elec_pos : tuple(float, float, float)
        Elektrot konumu (ex, ey, ez) — µm cinsinden.
    current : float
        Elektrottan enjekte edilen akım (µA).
    rho : float, optional
        Doku özgül direnci (Ω·cm). Varsayılan 300 Ω·cm (izotropik, homojen ortam varsayımı).

    Döndürür
    --------
    float
        Ekstrasellüler potansiyel (mV).

    Notlar
    ------
    - r=0 singularitesini önlemek için minimum mesafe 1e-6 cm ile sınırlanır.
    - McNeal (1976): Ekstrasellüler stimülasyon modellemesinin öncüsü.
    - Rattay (1986): 'Activating function' kavramı — e_extracellular'ın ikinci
      uzaysal türevi sinirin neresinin uyarılacağını belirler.

    Birim zinciri (kritik)
    ----------------------
    rho [Ω·cm] * current [µA] / r [cm]  →  Ω·µA = 1e-6 V = 1e-3 mV
    Yani ham bölme mikrovolt üretir. NEURON'un `e_extracellular` alanı
    **milivolt** beklediği için sonuç `_UV_TO_MV` ile ölçeklenir. Bu çarpan
    olmadan aksona 1000 kat büyük bir alan uygulanır (3 µA fiilen 3 mA gibi
    davranır) ve eşikler fizyolojik aralığın çok altında görünür.
    """
    ex, ey, ez = elec_pos
    r = np.sqrt((x - ex) ** 2 + (y - ey) ** 2 + (z - ez) ** 2)  # µm
    r_cm = np.maximum(r * 1e-4, 1e-6)  # µm → cm, singularite koruması
    return _UV_TO_MV * (rho * current) / (4 * np.pi * r_cm)


def biphasic_waveform(
    freq_hz: float, amp: float, duration_ms: float, dt: float = 0.005,
    pulse_width_ms: float = 0.1, waveform: str = "rectangular",
    interphase_gap_ms: float = 0.05,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Biphasic (çift fazlı) veya sinüsoidal (KHFAC) uyarım dalga formu üretir.

    Parametreler
    ------------
    freq_hz : float
        Uyarım frekansı (Hz). 1 Hz — 50 kHz aralığında.
    amp : float
        Akım genliği (µA). Pozitif değer; negatif faz otomatik eklenir.
    duration_ms : float
        Toplam dalga formu süresi (ms).
    dt : float, optional
        Zaman adımı (ms). Varsayılan 0.005 ms = 5 µs.
    pulse_width_ms : float, optional
        Her fazın süresi (ms). Varsayılan 0.1 ms = 100 µs.
    waveform : str, optional
        "rectangular" (varsayılan): yük dengeli bifazik kare dalga.
        "dc": monofazik ("DC") puls treni — negatif dengeleyici faz yok.
        "sinusoidal": sürekli sinüs dalgası (KHFAC blok deneyleri için).
    interphase_gap_ms : float, optional
        İki faz arasındaki boşluk (ms). Varsayılan 0.05 ms.
        Birinci fazın etkisinin tam oluşması için bekleme süresi.
        "dc" dalga formunda kullanılmaz.

    Döndürür
    --------
    t_vec : np.ndarray
        Zaman vektörü (ms).
    i_vec : np.ndarray
        Akım vektörü (µA); t_vec ile aynı uzunlukta.

    Notlar
    ------
    Biphasic tasarım: pozitif + negatif puls → net yük = 0 → doku hasarı önlenir.
    KHFAC (Kilohertz-Frequency Alternating Current): sinüsoidal dalga ile Na+
    kanallarını inaktive ederek sinir iletimini bloke eder (engellemek için).
    """
    t_vec = np.arange(0, duration_ms, dt)
    i_vec = np.zeros_like(t_vec)

    if waveform == "sinusoidal":
        # KHFAC için sürekli sinüsoidal dalga
        i_vec = amp * np.sin(2 * np.pi * freq_hz * t_vec * 1e-3)
    else:
        period_ms = 1000.0 / freq_hz  # ms

        # Yüksek frekansta (>= ~2.5 kHz) varsayılan 0.1 ms puls periyoda
        # sığmaz ve ardışık pulslar birbirinin üzerine yazılır. Puls genişliği
        # ve interphase gap periyoda göre sınırlanır: dalga formu her zaman
        # tek bir periyot içinde tamamlanır.
        pw = min(pulse_width_ms, period_ms / 4.0)
        gap = min(interphase_gap_ms, period_ms / 8.0)

        for t_start in np.arange(0, duration_ms, period_ms):
            # Faz 1: pozitif puls (her iki dalga formunda da var)
            mask1 = (t_vec >= t_start) & (t_vec < t_start + pw)
            i_vec[mask1] = amp

            if waveform == "dc":
                # Monofazik ("DC") puls: yük dengeleyici negatif faz yok.
                # Net yük sıfırdan farklıdır; kronik kullanımda doku hasarı
                # riski taşır, burada karşılaştırma amacıyla modellenir.
                continue

            # Faz 2: negatif puls (yükü dengeler) — bifazik "rectangular"
            neg_start = t_start + pw + gap
            mask2 = (t_vec >= neg_start) & (t_vec < neg_start + pw)
            i_vec[mask2] = -amp

    return t_vec, i_vec


def run_stimulation_loop(
    sections: list[Any], coords: list[tuple[float, float, float]],
    elec_pos: tuple[float, float, float], i_vec: np.ndarray, dt: float,
    v_init: float = -65.0,
) -> None:
    """
    Bir akım dalga formunu (i_vec) NEURON aksonuna adım adım uygular.

    h.dt ayarlar, h.finitialize(v_init) çağırır, sonra i_vec'teki her değeri
    apply_extracellular_field() ile uygulayıp h.fadvance() ile ilerler.
    level1.py ve frequency_sweep.py'deki tekrar eden NEURON run-loop deseni
    için ortak yardımcı fonksiyon.

    Parametreler
    ------------
    sections : list of h.Section
    coords : list of tuple(float, float, float)
    elec_pos : tuple(float, float, float)
    i_vec : np.ndarray
        Her zaman adımı için akım değeri (µA).
    dt : float
        Zaman adımı (ms).
    v_init : float, optional
        Başlangıç/dinlenme membran potansiyeli (mV). Varsayılan -65.0.

    Notlar
    ------
    h.finitialize(v_init) her çağrıda dinlenme potansiyeline sıfırlar — bu
    fonksiyon birden fazla kez çağrılabilir (örn. sweep_fiber() içinde her
    frekans için yeni fiber + yeni loop). Bu modül NEURON import'unu
    fonksiyon içinde tutar; dosyanın geri kalanı (point_source_potential,
    biphasic_waveform) NEURON kurulu olmadan da test edilebilir kalır.
    """
    from neuron import h

    h.dt = dt
    h.finitialize(v_init)
    for i_t in i_vec:
        apply_extracellular_field(sections, coords, elec_pos, i_t)
        h.fadvance()


def apply_extracellular_field(
    sections: list[Any], coords: list[tuple[float, float, float]],
    elec_pos: tuple[float, float, float], current: float,
) -> None:
    """
    Hesaplanan ekstrasellüler potansiyeli NEURON aksonu üzerindeki tüm
    segmentlere uygular.

    Her segmentin koordinatına göre point_source_potential() hesaplanır ve
    NEURON'un `e_extracellular` değişkenine atanır.

    Parametreler
    ------------
    sections : list
        NEURON Section nesnelerinin listesi (MRGAxon.all_sections() çıktısı).
    coords : list of tuple
        Her section için (x, y, z) koordinatı — µm cinsinden.
        sections ile aynı uzunlukta olmalıdır.
    elec_pos : tuple(float, float, float)
        Elektrot konumu (µm).
    current : float
        Anlık akım değeri (µA).

    Notlar
    ------
    `e_extracellular` NEURON'un extracellular mekanizmasına özgüdür.
    IClamp (intraselüler enjeksiyon) ile karıştırılmamalıdır.
    Aktivasyon fonksiyonu = e_extracellular'ın uzay boyunca ikinci türevi.
    """
    for sec, (x, y, z) in zip(sections, coords):
        v_ext = point_source_potential(x, y, z, elec_pos, current)
        for seg in sec:
            seg.e_extracellular = v_ext
