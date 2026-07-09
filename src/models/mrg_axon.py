"""
src/models/mrg_axon.py
=======================
Miyelinli periferik sinir aksonu modeli — MRG (McIntyre-Richardson-Grill 2002).

MRG modeli, periferik miyelinli sinir liflerinin en detaylı ve yaygın kullanılan
hesaplamalı modelidir (ModelDB Accession: 3810).

Yapı:
    [Node]---[Internode]---[Node]---[Internode]---[Node]
      ~1 µm     ~750 µm     ~1 µm     ~750 µm     ~1 µm

    - Ranvier düğümü (Node): İyon kanalları yoğun, AP burada yenilenir.
    - Internode: Miyelin kılıf, pasif kablo iletimi.
    - Saltatory conduction: AP düğümden düğüme 'sıçrar' (120 m/s'ye kadar).

Mekanizma önceliği:
    1. axnode70 / MRGaxon (gerçek MRG mekanizması — derlenmiş .mod gerektirir)
    2. HH (Hodgkin-Huxley) fallback — kurulum gerektirmez, kalitatif sonuçlar

Kaynak: nerve_frequency_study_colab.ipynb — Cell 10
"""

import numpy as np
from neuron import h

from config.defaults import MRG_PARAMS

h.load_file("stdrun.hoc")


def _has_mrg_mechanism():
    """
    Derlenmiş MRG mekanizmasının (axnode70 veya MRGaxon) mevcut olup
    olmadığını kontrol eder.

    Döndürür
    --------
    bool
        True: gerçek MRG mekanizması kullanılabilir.
        False: HH fallback kullanılacak.

    Notlar
    ------
    axnode70: MRG modelinin Ranvier düğümü mekanizması.
    Nav1.6, Nav1.1, geciktirilmiş K+, kalıcı Na+ kanallarını içerir.
    Derleme: `nrnivmodl` komutu ile .mod dosyalarından oluşturulur.
    """
    return hasattr(h, "axnode70") or hasattr(h, "MRGaxon")


class MRGAxon:
    """
    McIntyre-Richardson-Grill (2002) miyelinli akson modeli.

    Parametreler
    ------------
    diameter_um : float
        Fiber çapı (µm). MRG_PARAMS'ta tanımlı çaplardan biri olmalıdır:
        5.7 (Aδ), 8.7 (Aβ), 12.8 (Aα), 16.0 (Aα kalın).
    n_nodes : int, optional
        Ranvier düğümü sayısı. Varsayılan 21 (klasik MRG); 15 daha hızlıdır.

    Özellikler
    ----------
    nodes : list of h.Section
        Ranvier düğümleri.
    internodes : list of h.Section
        Miyelin kaplı internode bölgeleri.

    Örnek
    -----
    >>> fiber = MRGAxon(diameter_um=8.7, n_nodes=15)
    >>> sections = fiber.all_sections()
    >>> coords = fiber.section_coords()
    >>> spikes = fiber.record_last_node_spikes()
    """

    def __init__(self, diameter_um=8.7, n_nodes=21):
        if diameter_um not in MRG_PARAMS:
            raise ValueError(
                f"Desteklenmeyen fiber çapı: {diameter_um} µm. "
                f"Geçerli değerler: {list(MRG_PARAMS.keys())}"
            )
        self.diameter = diameter_um
        self.n_nodes = n_nodes

        node_diam, node_len, internode_len, n_lamellae = MRG_PARAMS[diameter_um]
        self._node_diam = node_diam
        self._node_len = node_len
        self._internode_len = internode_len
        self._n_lamellae = n_lamellae

        self.nodes = []
        self.internodes = []
        self._build()

    def _build(self):
        """Akson geometrisini ve iyon kanallarını oluşturur."""
        use_mrg = _has_mrg_mechanism()

        # --- Ranvier düğümleri ---
        for i in range(self.n_nodes):
            node = h.Section(name=f"node_{i}")
            node.diam = self._node_diam
            node.L = self._node_len
            node.nseg = 1  # 1 µm kısa bölüm — tek segment yeterli

            node.insert("extracellular")  # e_extracellular için zorunlu

            if use_mrg:
                node.insert("axnode70")
            else:
                # Hodgkin-Huxley fallback
                # HH: Nobel 1963, kalamar dev aksonunu 4 denklemle (m, h, n, V) modelliyor.
                # Periferik sinire özgü değil; eşikler ve ileti hızları farklı çıkar.
                node.insert("hh")
                node.insert("pas")
                node.g_pas = 0.0001   # S/cm² — sızıntı iletkenliği (K2P kanalları)
                node.e_pas = -80      # mV — dinlenme potansiyelini belirleyen ana faktör

            self.nodes.append(node)

        # --- Internodlar ---
        for i in range(self.n_nodes - 1):
            inter = h.Section(name=f"internode_{i}")
            # g-ratio ≈ 0.7: iç akson çapı / toplam fiber çapı
            # ~0.6-0.7 optimal; daha düşükse yavaşlar, daha yüksekse miyelin yetersiz
            inter.diam = self.diameter * 0.7
            inter.L = self._internode_len
            inter.nseg = 6  # 750 µm bölüm — lambda/10 kuralı için 6 segment

            inter.insert("extracellular")
            inter.insert("pas")
            inter.g_pas = 1e-6    # S/cm² — çok düşük: miyelin mükemmel yalıtır
            inter.e_pas = -80     # mV

            self.internodes.append(inter)

        # --- Topolojik bağlantı: node → internode → node → ... ---
        # (0): proximal uç, (1): distal uç
        for i in range(self.n_nodes - 1):
            self.internodes[i].connect(self.nodes[i](1), 0)
            self.nodes[i + 1].connect(self.internodes[i](1), 0)

    def all_sections(self):
        """
        Tüm section'ları (node + internode) sıralı liste olarak döndürür.

        Döndürür
        --------
        list of h.Section
            [node_0, internode_0, node_1, internode_1, ..., node_N]
        """
        sections = []
        for i in range(self.n_nodes - 1):
            sections.append(self.nodes[i])
            sections.append(self.internodes[i])
        sections.append(self.nodes[-1])
        return sections

    def section_coords(self, elec_z=5000.0):
        """
        Her section için (x, y, z) koordinatlarını hesaplar.

        Akson x ekseni boyunca uzanır. Her section'ın koordinatı,
        o section'ın z-ekseni orta noktasıdır.

        Parametreler
        ------------
        elec_z : float, optional
            Elektrotun z koordinatı (µm). Koordinat sistemini ayarlamak için.

        Döndürür
        --------
        list of tuple(float, float, float)
            all_sections() ile aynı sırада koordinatlar.
        """
        coords = []
        z = 0.0
        for i in range(self.n_nodes - 1):
            coords.append((0.0, 0.0, z + self._node_len / 2))
            z += self._node_len
            coords.append((0.0, 0.0, z + self._internode_len / 2))
            z += self._internode_len
        coords.append((0.0, 0.0, z + self._node_len / 2))
        return coords

    def record_last_node_spikes(self):
        """
        Aksonun distal ucundaki (son düğüm) spike zamanlarını kaydeden
        NetCon nesnesi ve spike zaman vektörü oluşturur.

        Döndürür
        --------
        h.Vector
            Spike zamanları (ms). Simülasyon bittikten sonra doldurulur.

        Notlar
        ------
        NetCon hedefi None — sinaptik bağlantı yok, yalnızca izleme.
        threshold=-20 mV: membran potansiyeli bu değeri aşınca spike sayılır.
        Son düğüm [-1]: aksonun distal ucu — buraya spike ulaşırsa iletim başarılı.
        """
        last_node = self.nodes[-1]
        nc = h.NetCon(
            last_node(0.5)._ref_v,
            None,
            sec=last_node
        )
        nc.threshold = -20  # mV
        spike_times = h.Vector()
        nc.record(spike_times)
        # NetCon'u garbage collector'dan korumak için referans sakla
        self._nc = nc
        self._spike_times = spike_times
        return spike_times
