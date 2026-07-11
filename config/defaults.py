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
ELECTRODE_POS = (500.0, 0.0, 5000.0)  # µm

# ---------------------------------------------------------------------------
# MRG akson parametreleri
# McIntyre, Richardson, Grill (2002) — ModelDB Acc. 3810
# Anahtar: fiber çapı (µm)
# Değer: (node_diam, node_length, internode_length, n_myelin_lamellae)
# ---------------------------------------------------------------------------
MRG_PARAMS = {
    5.7:  (1.9, 1.0,  500, 80),   # Aδ — ağrı, sıcaklık
    8.7:  (2.8, 1.0,  750, 110),  # Aβ — dokunma
    12.8: (3.4, 1.0, 1150, 130),  # Aα — motor, propriosepsiyon
    16.0: (4.7, 1.0, 1400, 150),  # Aα (kalın) — büyük motor
}

# ---------------------------------------------------------------------------
# Varsayılan simülasyon parametreleri
# ---------------------------------------------------------------------------
DEFAULT_AMP           = 3.0    # Uyarım genliği (µA)
DEFAULT_N_FIBERS      = 20     # Fiber demeti büyüklüğü
DEFAULT_FIBER_DIAM    = 8.7    # MRG akson çapı (µm)
DEFAULT_N_NODES       = 15     # MRG düğüm sayısı
DEFAULT_ELEC_Z        = 3000.0 # Elektrot z konumu run_level1 için (µm)
DEFAULT_PULSE_WIDTH   = 0.1    # Puls genişliği (ms)
DEFAULT_CELSIUS       = 37.0   # Fizyolojik hedef sıcaklık (°C) — ŞUANDA KULLANILMIYOR.
                                # AXNODE.mod parametreleri NEURON varsayılanı (6.3°C)
                                # için kalibre edilmiş; 37°C'de eşik ~50 µA oluyor
                                # (fizyolojik ~1-2 µA olmalı). Faz 4'te .mod
                                # parametrelerini 37°C için yeniden fit etmek gerekiyor.
DEFAULT_DT            = 0.005  # Zaman adımı (ms)
DEFAULT_N_CYCLES      = 8      # Adaptif süre hesabı için minimum döngü sayısı
DEFAULT_MIN_MS        = 200    # Minimum simülasyon süresi (ms)
                                # ADR (2026-07-11): Bu değer 200 ms olarak bırakıldı.
                                # Faz 3 sweep testinde NAc hiç aktive olmadı (tüm frekanslarda 0.00).
                                # Kök neden: NAc TM fasilitasyon zaman sabiti tau_f=500 ms;
                                # 50+ Hz'de cycles_to_duration_ms() bu zemine çarpar (200 ms < 500 ms)
                                # → fasilitasyon birikmeden simülasyon biter → NAc = 0.
                                # Karar: Değeri 1000 ms'e çıkarmak NAc'ı aktive edebilir
                                # ama yüksek frekanslarda simülasyon ~5x yavaşlar.
DEFAULT_MAX_MS        = 1000   # Maksimum simülasyon süresi (ms)

# ---------------------------------------------------------------------------
# LIF / Brian2 ortak biyofizik sabitleri (nts_relay.py + brain_regions.py)
# ---------------------------------------------------------------------------
DEFAULT_V_INIT_MV = -65.0  # Başlangıç/dinlenme membran potansiyeli (mV) — NEURON tarafı
                            # (run_stimulation_loop/h.finitialize). Brian2 popülasyon
                            # dinlenme durumundan (LIF_V_REST_MV) kasıtlı olarak ayrı
                            # tutulur — sayısal değer aynı ama kavramsal alan farklı.
LIF_THRESHOLD_MV   = -50.0  # Spike eşiği (mV) — NTS + tüm downstream bölgeler ortak
LIF_RESET_MV       = -65.0  # Reset potansiyeli (mV)
LIF_V_REST_MV      = -65.0  # Dinlenme potansiyeli (mV)
LIF_E_SYN_MV       = 0.0    # Sinaptik ters çevirme potansiyeli (mV) — AMPA benzeri eksitasyon
LIF_GL_NS          = 10.0   # Sızıntı iletkenliği (nS)
LIF_TAU_SYN_MS     = 5.0    # Sinaptik iletkenlik azalma zaman sabiti (ms)

# ---------------------------------------------------------------------------
# Brian2 simülasyon zaman adımı (level23.py)
# ---------------------------------------------------------------------------
DEFAULT_BRIAN_DT_MS = 0.1   # defaultclock.dt (ms) — run_levels_2_3 ve run_full_network ortak

# ---------------------------------------------------------------------------
# Tarama frekansları
# ---------------------------------------------------------------------------
# Aktivasyon bölgesi (düşük frekans) + KHFAC blok bölgesi (yüksek frekans)
DEFAULT_FREQUENCIES = [1, 5, 10, 20, 50, 100, 200, 500]

LOW_FREQ_RANGE  = [1, 2, 5, 10, 20, 50, 100, 200, 500]        # Hz
HIGH_FREQ_RANGE = [1000, 2000, 5000, 10000, 20000, 50000]      # Hz (KHFAC)

# ---------------------------------------------------------------------------
# Analiz eşiği
# ---------------------------------------------------------------------------
DEFAULT_ACTIVE_THRESHOLD_HZ = 0.5  # Hz/nöron — bu değerin üstü "aktif" sayılır

# ---------------------------------------------------------------------------
# NTS relay parametreleri (Level 2)
# ---------------------------------------------------------------------------
NTS_PARAMS = {
    "n_neurons": 30,
    "tau_m_ms": 20.0,
    "refractory_ms": 2.0,
    # Afferent → NTS TM sinaps parametreleri
    "U": 0.5,
    "tau_f_ms": 20.0,
    "tau_d_ms": 700.0,
    "p": 0.3,
    "w_nS": 6.0,
}

# ---------------------------------------------------------------------------
# Downstream bölge parametreleri (Level 3)
# ---------------------------------------------------------------------------

# NAc — Nucleus Accumbens
# Güçlü fasilitasyon: düşük frekansta sessiz, yüksek frekansta aktif
NAC_PATHWAY_PARAMS = {
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
INSULA_PATHWAY_PARAMS = {
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
CA3_PATHWAY_PARAMS = {
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
REGION_COLORS = {
    "NTS":   "#888888",
    "NAc":   "#d95f02",
    "Insula": "#1b9e77",
    "CA3":   "#7570b3",
}
