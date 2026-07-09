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

import numpy as np


def point_source_potential(x, y, z, elec_pos, current, rho=300.0):
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
    """
    ex, ey, ez = elec_pos
    r = np.sqrt((x - ex) ** 2 + (y - ey) ** 2 + (z - ez) ** 2)  # µm
    r_cm = np.maximum(r * 1e-4, 1e-6)  # µm → cm, singularite koruması
    return (rho * current) / (4 * np.pi * r_cm)


def biphasic_waveform(freq_hz, amp, duration_ms, dt=0.005,
                      pulse_width_ms=0.1, waveform="rectangular",
                      interphase_gap_ms=0.05):
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
        "rectangular" (varsayılan) veya "sinusoidal" (KHFAC blok deneyleri için).
    interphase_gap_ms : float, optional
        İki faz arasındaki boşluk (ms). Varsayılan 0.05 ms.
        Birinci fazın etkisinin tam oluşması için bekleme süresi.

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
        # Dikdörtgen biphasic puls treni
        period_ms = 1000.0 / freq_hz  # ms
        for t_start in np.arange(0, duration_ms, period_ms):
            # Faz 1: pozitif puls
            mask1 = (t_vec >= t_start) & (t_vec < t_start + pulse_width_ms)
            i_vec[mask1] = amp
            # Interphase gap: sıfır akım
            gap_start = t_start + pulse_width_ms
            # Faz 2: negatif puls (yükü dengeler)
            neg_start = gap_start + interphase_gap_ms
            mask2 = (t_vec >= neg_start) & (t_vec < neg_start + pulse_width_ms)
            i_vec[mask2] = -amp

    return t_vec, i_vec


def apply_extracellular_field(sections, coords, elec_pos, current):
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
