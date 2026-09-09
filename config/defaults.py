"""
config/defaults.py
==================
Tüm simülasyon parametrelerinin merkezi deposu.

Notebook'taki dağınık sabitler burada toplandı. main.py'deki argparse
argümanlarının varsayılan değerleri buradan okunur; bu sayede tek bir
yerden tüm parametreler değiştirilebilir.

Kaynak: nerve_frequency_study_colab.ipynb — çeşitli hücrelerden toplanan sabitler.
"""

# ---------------------------------------------------------------------------
# Elektrot geometrisi
# ---------------------------------------------------------------------------
# (x, y, z) koordinatları mikrometre cinsinden.
# Aksondan 500 µm uzakta, z ekseni boyunca 5 mm konumda.
ELECTRODE_POS: tuple[float, float, float] = (500.0, 0.0, 5000.0)  # µm

# ---------------------------------------------------------------------------
# MRG akson parametreleri
# McIntyre, Richardson, Grill (2002) — ModelDB Acc. 3810
# Anahtar: fiber çapı (µm)
# Değer: (node_diam, node_length, internode_length, n_myelin_lamellae, axon_diam)
#
# Değerler ModelDB 3810'daki MRGaxon.hoc dosyasından birebir alınmıştır
# (nodeD, deltax, nl, axonD sütunları; node_length tüm çaplarda 1.0 µm).
# ---------------------------------------------------------------------------
MRG_PARAMS: dict[float, tuple[float, float, int, int, float]] = {
    5.7:  (1.9, 1.0,  500,  80, 3.4),   # Aδ — ağrı, sıcaklık
    8.7:  (2.8, 1.0, 1000, 110, 5.8),   # Aβ — dokunma
    12.8: (4.2, 1.0, 1350, 135, 9.2),   # Aα — motor, propriosepsiyon
    16.0: (5.5, 1.0, 1500, 150, 12.7),  # Aα (kalın) — büyük motor
}

# Miyelin kılıfının tek katman değerleri. Internode'un eşdeğer kapasitansı ve
# iletkenliği bunların 2*n_lamellae'ye bölünmesiyle bulunur (seri bağlı
# membran katmanları). Bu ölçekleme uygulanmazsa internode çıplak pasif kablo
# gibi davranır ve saltatory iletim oluşmaz — bkz. src/models/mrg_axon.py.
MYELIN_CM_UF_CM2: float = 1.0    # µF/cm² — tek membran katmanı kapasitansı
MYELIN_G_S_CM2: float   = 0.001  # S/cm²  — tek membran katmanı sızıntısı

# ---------------------------------------------------------------------------
# Varsayılan simülasyon parametreleri
# ---------------------------------------------------------------------------
DEFAULT_AMP: float           = 3.0    # Uyarım genliği (µA)
DEFAULT_N_FIBERS: int        = 20     # Fiber demeti büyüklüğü
DEFAULT_FIBER_DIAM: float    = 8.7    # MRG akson çapı (µm)
DEFAULT_N_NODES: int         = 15     # MRG düğüm sayısı
DEFAULT_ELEC_DIST: float     = 500.0  # Elektrot-akson mesafesi, x ekseni (µm)
DEFAULT_ELEC_Z: float        = 3000.0 # Elektrot z konumu run_level1 için (µm)
DEFAULT_PULSE_WIDTH: float   = 0.1    # Puls genişliği (ms)
DEFAULT_CELSIUS: float       = 37.0   # Fizyolojik hedef sıcaklık (°C) — ŞUANDA KULLANILMIYOR.
                                # AXNODE.mod parametreleri NEURON varsayılanı (6.3°C)
                                # için kalibre edilmiş; 37°C'de eşik ~50 µA oluyor
                                # (fizyolojik ~1-2 µA olmalı). Faz 4'te .mod
                                # parametrelerini 37°C için yeniden fit etmek gerekiyor.
DEFAULT_DT: float            = 0.005  # Zaman adımı (ms)
DEFAULT_N_CYCLES: int        = 8      # Adaptif süre hesabı için minimum döngü sayısı
DEFAULT_MIN_MS: float        = 200    # Minimum simülasyon süresi (ms)
                                # ADR (2026-07-11): Bu değer 200 ms olarak bırakıldı.
                                # Faz 3 sweep testinde NAc hiç aktive olmadı (tüm frekanslarda 0.00).
                                # Kök neden: NAc TM fasilitasyon zaman sabiti tau_f=500 ms;
                                # 50+ Hz'de cycles_to_duration_ms() bu zemine çarpar (200 ms < 500 ms)
                                # → fasilitasyon birikmeden simülasyon biter → NAc = 0.
                                # Karar: Değeri 1000 ms'e çıkarmak NAc'ı aktive edebilir
                                # ama yüksek frekanslarda simülasyon ~5x yavaşlar.
DEFAULT_MAX_MS: float        = 1000   # Maksimum simülasyon süresi (ms)

# ---------------------------------------------------------------------------
# LIF / Brian2 ortak biyofizik sabitleri (nts_relay.py + brain_regions.py)
# ---------------------------------------------------------------------------
DEFAULT_V_INIT_MV: float = -65.0  # Başlangıç/dinlenme membran potansiyeli (mV) — NEURON tarafı
                            # (run_stimulation_loop/h.finitialize). Brian2 popülasyon
                            # dinlenme durumundan (LIF_V_REST_MV) kasıtlı olarak ayrı
                            # tutulur — sayısal değer aynı ama kavramsal alan farklı.
LIF_THRESHOLD_MV: float   = -50.0  # Spike eşiği (mV) — NTS + tüm downstream bölgeler ortak
LIF_RESET_MV: float       = -65.0  # Reset potansiyeli (mV)
LIF_V_REST_MV: float      = -65.0  # Dinlenme potansiyeli (mV)
LIF_E_SYN_MV: float       = 0.0    # Sinaptik ters çevirme potansiyeli (mV) — AMPA benzeri eksitasyon
LIF_GL_NS: float          = 10.0   # Sızıntı iletkenliği (nS)
LIF_TAU_SYN_MS: float     = 5.0    # Sinaptik iletkenlik azalma zaman sabiti (ms)

# ---------------------------------------------------------------------------
# Brian2 simülasyon zaman adımı (level23.py)
# ---------------------------------------------------------------------------
DEFAULT_BRIAN_DT_MS: float = 0.1   # defaultclock.dt (ms) — run_levels_2_3 ve run_full_network ortak

# Aksonal mutlak refrakter periyot (ms). bridge.py'de fiber demeti kurulurken
# uygulanır: bir akson bu süre içinde ikinci kez ateşleyemez. Jitter eklendikten
# sonra çakışan spike'ları eler; bu olmadan >= 1 kHz uyarımda Brian2'nin
# SpikeGeneratorGroup'u "aynı zaman adımında birden fazla spike" hatası veriyor.
AXON_REFRACTORY_MS: float = 1.0

# ---------------------------------------------------------------------------
# Tekrarlanabilirlik ve istatistik
# ---------------------------------------------------------------------------
# Level 1 (NEURON) deterministiktir; stokastiklik yalnızca Level 2-3'te
# (Brian2 bağlantı örneklemesi ve fiber jitter'ı) bulunur. Bu yüzden akson
# simülasyonu bir kez çalıştırılıp spike treni tekrarlar arasında paylaşılır —
# tekrar maliyeti neredeyse sıfırdır.
DEFAULT_N_REPEATS: int = 5    # Koşul başına tekrar sayısı (ortalama ± SD için)
DEFAULT_SEED: int      = 1000  # Taban rastgele tohum; tekrar r için seed + r

# ---------------------------------------------------------------------------
# Tarama frekansları
# ---------------------------------------------------------------------------
# Aktivasyon bölgesi (düşük frekans) + KHFAC blok bölgesi (yüksek frekans)
DEFAULT_FREQUENCIES: list[float] = [1, 5, 10, 20, 50, 100, 200, 500]

LOW_FREQ_RANGE: list[float]  = [1, 2, 5, 10, 20, 50, 100, 200, 500]        # Hz
HIGH_FREQ_RANGE: list[float] = [1000, 2000, 5000, 10000, 20000, 50000]      # Hz (KHFAC)

# ---------------------------------------------------------------------------
# Analiz eşiği
# ---------------------------------------------------------------------------
DEFAULT_ACTIVE_THRESHOLD_HZ: float = 0.5  # Hz/nöron — bu değerin üstü "aktif" sayılır

# ---------------------------------------------------------------------------
# NTS relay parametreleri (Level 2)
# ---------------------------------------------------------------------------
NTS_PARAMS: dict[str, float] = {
    "n_neurons": 30,
    "tau_m_ms": 20.0,
    "refractory_ms": 2.0,
    # Afferent → NTS TM sinaps parametreleri — deneysel veriye kalibre edildi.
    #
    # tau_d_ms: Chen, Horowitz & Bonham (1999), Am J Physiol 277:H1350 —
    #   sıçan NTS diliminde ölçülen sinaptik toparlanma zaman sabiti
    #   0.8-1.2 s. Bu doğrudan ölçülmüş bir büyüklüktür, sabit tutuldu.
    # U: Miles (1986), J Neurophysiol 55:1076 — kobay NTS'de kararlı-durum
    #   PSP depresyonu 5 Hz'de %35, 10 Hz'de %60, 20 Hz'de %80 (yani
    #   steady-state/ilk PSP oranı 0.65 / 0.40 / 0.20). tau_d yukarıdaki
    #   aralıkta sabitlenip U bu üç noktaya fit edildi (RMSE 0.045).
    #
    # Doğrulama: bu parametrelerle 20 Hz'de aktarım oranı 0.255; Beaumont
    # ve ark. (2017), Am J Physiol 313:H354, klinik tarzda 20 Hz VNS'de
    # NTS nöronlarında ~%25 senkronize AP başarısı bildiriyor.
    #
    # Not: Peters ve ark. (2011) paired-pulse verisinden U≈0.5 türetiyor;
    # tek havuzlu TM modeli Miles'ın kararlı-durum eğrisi ile Chen'in
    # toparlanma sabitini aynı anda sağlayamıyor. tau_d ölçülmüş bir
    # büyüklük olduğu için o sabitlendi. Bkz. README "Bilinen Kısıtlar".
    "U": 0.19,
    "tau_f_ms": 20.0,
    "tau_d_ms": 810.0,
    "p": 0.3,
    "w_nS": 6.0,
}

# NTS afferent sinapsının alternatif "facilitating" varyantı.
# build_nts_relay(synapse_type="facilitating") bu değerleri kullanır; ana
# pipeline (run_full_network) her zaman yukarıdaki NTS_PARAMS'ı kullanır.
NTS_FACILITATING_PARAMS: dict[str, float] = {
    "U": 0.05,
    "tau_f_ms": 500.0,
    "tau_d_ms": 100.0,
}

# ---------------------------------------------------------------------------
# Downstream bölge parametreleri (Level 3)
# ---------------------------------------------------------------------------

# NAc — Nucleus Accumbens
# Güçlü fasilitasyon: düşük frekansta sessiz, yüksek frekansta aktif
NAC_PATHWAY_PARAMS: dict[str, float] = {
    "n_neurons": 100,
    "tau_m_ms": 30.0,
    "refractory_ms": 3.0,
    # NTS → NAc TM sinaps parametreleri
    # ADR (2026-07-11): U=0.05 (çok düşük salınım olasılığı) + tau_f_ms=500.0
    # kombinasyonu NAc'ın yüksek frekansta aktive olmasını tasarım gereği sağlar.
    # Ancak simülasyon süresi bu tau_f değerinden kısa olursa (bkz. DEFAULT_MIN_MS)
    # fasilitasyon birikmez ve NAc hiç ateşlemez. Bu iki parametre birlikte ele alınmalı.
    "U": 0.05,
    "tau_f_ms": 500.0,
    "tau_d_ms": 100.0,
    "p": 0.3,
    "w_nS": 9.0,
}

# Insula — İnsüla Korteksi
# Hafif depresyon: düşük frekanstan itibaren yanıt — direkt röle gibi
INSULA_PATHWAY_PARAMS: dict[str, float] = {
    "n_neurons": 100,
    "tau_m_ms": 20.0,
    "refractory_ms": 3.0,
    # NTS → İnsula TM sinaps parametreleri
    "U": 0.4,
    "tau_f_ms": 10.0,
    "tau_d_ms": 150.0,
    "p": 0.3,
    "w_nS": 7.0,
}

# CA3 — Cornu Ammonis 3 (Hipokampüs)
# Orta fasilitasyon + rekürrent kolateraller
CA3_PATHWAY_PARAMS: dict[str, float] = {
    "n_neurons": 100,
    "tau_m_ms": 20.0,
    "refractory_ms": 3.0,
    # NTS → CA3 TM sinaps parametreleri
    "U": 0.2,
    "tau_f_ms": 150.0,
    "tau_d_ms": 300.0,
    "p": 0.3,
    "w_nS": 6.0,
    # Rekürrent kolateral parametreleri
    "recurrent_p": 0.12,
    "recurrent_w_nS": 1.0,
}

# ---------------------------------------------------------------------------
# Görselleştirme renkleri (bölgeye göre)
# ---------------------------------------------------------------------------
REGION_COLORS: dict[str, str] = {
    "NTS":   "#888888",
    "NAc":   "#d95f02",
    "Insula": "#1b9e77",
    "CA3":   "#7570b3",
}
