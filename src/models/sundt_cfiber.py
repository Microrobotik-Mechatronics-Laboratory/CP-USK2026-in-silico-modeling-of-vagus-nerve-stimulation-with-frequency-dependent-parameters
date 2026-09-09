"""
src/models/sundt_cfiber.py
===========================
Miyelinsiz C-fiber akson modeli — Sundt/Gamper/Jaffe (2015).

C-fiber, ağrı ve visseral duyuların (vagus sinirinin büyük çoğunluğu)
taşıyıcısıdır. MRG'nin aksine miyelin kılıfı yoktur; sürekli (continuous)
ileti gösterir.

Karakteristikler:
    - Çap: 0.2 – 1.5 µm
    - İleti hızı: 0.5 – 2 m/s (A-fiber'ın 1/60'ı)
    - Na+ kanalları: Nav1.7, Nav1.8, Nav1.9 (ağrı araştırmasının hedefleri)

Mekanizma önceliği:
    1. nahh + borgkdr (Sundt/Gamper/Jaffe — derlenmiş .mod gerektirir)
       ModelDB Accession: 187473
    2. HH (Hodgkin-Huxley) fallback

Kaynak: nerve_frequency_study_colab.ipynb — Cell 12
"""

from typing import Any

import numpy as np
from neuron import h

from src.models._neuron_mechanisms import ensure_mechanisms_loaded

h.load_file("stdrun.hoc")


def _has_sundt_mechanism() -> bool:
    """
    Derlenmiş Sundt/Gamper/Jaffe mekanizmalarının mevcut olup olmadığını kontrol eder.

    Döndürür
    --------
    bool
        True: nahh ve borgkdr mekanizmaları kullanılabilir.
        False: HH fallback kullanılacak.

    Notlar
    ------
    nahh: C-fiber'a özgü Na+ kanal kinetiği.
    borgkdr: Geciktirilmiş düzeltici K+ kanalı (delayed rectifier).
    """
    ensure_mechanisms_loaded()
    return hasattr(h, "nahh") or hasattr(h, "borgkdr")


class CFiber:
    """
    Sundt/Gamper/Jaffe (2015) miyelinsiz C-fiber modeli.

    MRG'nin aksine tek bir Section olarak modellenir — miyelin kılıfı olmadığı için
    düğüm/internode ayrımı yoktur; akım sürekli (continuous) olarak iletilir.

    Parametreler
    ------------
    diameter_um : float, optional
        C-fiber çapı (µm). Tipik: 0.4 – 1.2 µm. Varsayılan 0.8 µm.
    length_um : float, optional
        Akson uzunluğu (µm). Varsayılan 20,000 µm = 20 mm.
        Not: Kısa aksonda sınır koşulları yapay yansımalar üretebilir.
        20 mm, elektrot konumundan yeterince uzak uçlar sağlar.
    seg_length_um : float, optional
        Kompartman uzunluğu (µm). Her 100 µm'de bir segment → 200 segment.
        Varsayılan 100 µm.

    Özellikler
    ----------
    section : h.Section
        Aksonun tamamını temsil eden tek NEURON section.
    n_segs : int
        Toplam segment sayısı.

    Örnek
    -----
    >>> fiber = CFiber(diameter_um=0.8, length_um=20000)
    >>> spikes = fiber.record_distal_spikes()
    """

    def __init__(self, diameter_um: float = 0.8, length_um: float = 20000, seg_length_um: float = 100) -> None:
        self.diameter = diameter_um
        self.length = length_um
        self.n_segs = max(1, int(length_um / seg_length_um))

        self.section = h.Section(name="cfib_axon")
        self._build()

    def _build(self) -> None:
        """C-fiber section'ı oluşturur ve iyon kanallarını ekler."""
        sec = self.section
        sec.diam = self.diameter
        sec.L = self.length
        sec.nseg = self.n_segs

        sec.insert("extracellular")  # e_extracellular için zorunlu

        if _has_sundt_mechanism():
            # C-fiber'a özgü iyon kanalları
            sec.insert("nahh")    # Nav1.7, Nav1.8, Nav1.9 kinetiği
            sec.insert("borgkdr") # Geciktirilmiş düzeltici K+ kanalı
        else:
            # HH fallback — kalitatif sonuçlar, eşikler ve ileti hızları farklı
            sec.insert("hh")
            sec.insert("pas")
            sec.g_pas = 0.001  # S/cm² — miyelinsiz lif için daha yüksek sızıntı
            sec.e_pas = -70    # mV — C-fiber dinlenme potansiyeli

    def all_sections(self) -> list[Any]:
        """
        Section listesi döndürür (tek elemanlı — MRGAxon API uyumu için).

        Döndürür
        --------
        list of h.Section
            [section]
        """
        return [self.section]

    def section_coords(self) -> list[tuple[float, float, float]]:
        """
        Section koordinatını (x, y, z) döndürür.

        C-fiber z ekseni boyunca, z=0'dan başlayarak uzanır (x=y=0).

        Döndürür
        --------
        list of tuple(float, float, float)
            all_sections() ile aynı sırada koordinatlar (tek elemanlı).

        Notlar
        ------
        Akson elektrota göre hizalanmaz; hizalama çağıranın sorumluluğudur —
        elektrotun z konumu akson aralığı (0 – length_um) içinde kalmalıdır.
        """
        # Tek section olduğundan orta noktasını döndürüyoruz
        return [(0.0, 0.0, self.length / 2)]

    def record_distal_spikes(self, threshold: float = -20.0) -> Any:
        """
        Aksonun distal ucundaki spike zamanlarını kaydeden NetCon oluşturur.

        Parametreler
        ------------
        threshold : float, optional
            Spike algılama eşiği (mV). Varsayılan -20 mV.

        Döndürür
        --------
        h.Vector
            Spike zamanları (ms). Simülasyon bittikten sonra doldurulur.
        """
        # Distal uç: segmentlerin sonuncusu (1.0'a yakın konum)
        distal_pos = (2 * self.n_segs - 1) / (2 * self.n_segs)
        nc = h.NetCon(
            self.section(distal_pos)._ref_v,
            None,
            sec=self.section
        )
        nc.threshold = threshold
        spike_times = h.Vector()
        nc.record(spike_times)
        # Referans sakla
        self._nc = nc
        self._spike_times = spike_times
        return spike_times
