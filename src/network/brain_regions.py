"""
src/network/brain_regions.py
==============================
Downstream beyin bölgesi popülasyonları — NAc, İnsula, CA3.

Her bölge LIF (Leaky Integrate-and-Fire) nöron modeliyle temsil edilir.
CA3 ek olarak rekürrent kolateraller içerir (Cornu Ammonis 3'ün özelliği).

LIF vs HH:
    - Bu çalışmada spike şekli değil, spike zamanlaması önemlidir → LIF yeterli.
    - LIF: 2 denklem, hızlı, büyük ağlarda kullanılabilir.
    - Alternatifler: Izhikevich (bursting), AdEx (adaptasyon), EIF (yumuşak eşik).

Bölge özellikleri:
    NAc (Nucleus Accumbens):
        tau_m=30ms, U=0.05, tau_f=500ms → güçlü fasilitasyon → yüksek frekansta aktif.
    İnsula (İnsüla Korteksi):
        tau_m=20ms, U=0.4, tau_d=150ms → hafif depresyon → direkt röle.
    CA3 (Cornu Ammonis 3, Hipokampüs):
        tau_m=20ms + rekürrent kolateraller → örüntü tamamlama ağı.

Kaynak: nerve_frequency_study_colab.ipynb — Cell 22, Cell 26 (kısmen)
"""

from brian2 import (
    NeuronGroup, Synapses,
    ms, mV, nS,
)

# ---------------------------------------------------------------------------
# LIF denklemleri (brain_regions için — nts_relay ile aynı form)
# ---------------------------------------------------------------------------
# v_rest, E_syn, gL, tau_m, tau_syn: per-neuron parametreler
LIF_EQS = """
dv/dt = (v_rest - v + g_syn*(E_syn - v)/gL) / tau_m : volt (unless refractory)
dg_syn/dt = -g_syn / tau_syn : siemens
v_rest : volt
E_syn  : volt
gL     : siemens
tau_m  : second
tau_syn: second
"""


def build_lif_population(n, tau_m, v_rest=-65 * mV, refractory=3 * ms):
    """
    Genel amaçlı LIF popülasyonu oluşturur.

    Parametreler
    ------------
    n : int
        Nöron sayısı.
    tau_m : brian2.Quantity
        Membran zaman sabiti (Brian2 birimi, örn. 20*ms).
    v_rest : brian2.Quantity, optional
        Dinlenme potansiyeli. Varsayılan -65 mV.
    refractory : brian2.Quantity, optional
        Mutlak refrakter periyod. Varsayılan 3 ms.

    Döndürür
    --------
    brian2.NeuronGroup
        Yapılandırılmış LIF popülasyonu.
    """
    pop = NeuronGroup(
        n, LIF_EQS,
        threshold="v > -50*mV",
        reset="v = -65*mV",
        refractory=refractory,
        method="euler",
    )
    pop.v = v_rest
    pop.v_rest = v_rest
    pop.E_syn = 0 * mV    # AMPA benzeri eksitasyonlu sinaptik tersine çevirme potansiyeli
    pop.gL = 10 * nS      # Sızıntı iletkenliği
    pop.tau_m = tau_m
    pop.tau_syn = 5 * ms  # Sinaptik iletkenlik azalma hızı
    return pop


def build_pop(n, tau_m, refractory=3 * ms):
    """
    build_lif_population için kısa takma ad.

    Notebook Cell 26 ile API uyumu sağlar.

    Parametreler
    ------------
    n : int
        Nöron sayısı.
    tau_m : brian2.Quantity
        Membran zaman sabiti.
    refractory : brian2.Quantity, optional
        Refrakter periyod. Varsayılan 3 ms.

    Döndürür
    --------
    brian2.NeuronGroup
    """
    return build_lif_population(n, tau_m, refractory=refractory)


def build_ca3_r(n=100, recurrent_p=0.12, recurrent_w=1.0 * nS):
    """
    CA3 (Cornu Ammonis 3) rekürrent kolateral ağı oluşturur.

    CA3, hipokampüsün örüntü tamamlama (pattern completion) bölgesidir.
    Nöronlar birbiriyle bağlantılıdır — autoassociative network (Hopfield ağı benzeri).

    Parametreler
    ------------
    n : int, optional
        CA3 nöron sayısı. Varsayılan 100.
        Not: Gerçekte milyonlarca CA3 nöronu var; 100, dinamikleri yakalamak için yeterli.
    recurrent_p : float, optional
        Rekürrent bağlantı olasılığı. Varsayılan 0.12 (%12).
        Gerçek CA3'te ~%5-10. Biraz daha yüksek tutuldu.
    recurrent_w : brian2.Quantity, optional
        Rekürrent sinaptik ağırlık. Varsayılan 1.0 nS.
        Dikkat: Çok yüksek tutulursa → runaway excitation (sonsuz döngü).
        İnhibisyon (GABAerjik internöron) olmadan bu değer düşük tutulmalıdır.

    Döndürür
    --------
    tuple(NeuronGroup, Synapses)
        - pop: CA3 nöron popülasyonu.
        - rec: Rekürrent kolateral sinapsları.

    Uyarı
    -----
    Rekürrent bağlantılar pozitif geri besleme oluşturur. Gelecek iyileştirme:
    GABAerjik inhibitör internöron popülasyonu eklemek (Faz 4).
    """
    pop = build_pop(n, tau_m=20 * ms)
    rec = Synapses(pop, pop, on_pre="g_syn_post += w", model="w : siemens")
    rec.connect(condition="i != j", p=recurrent_p)  # autapse yok (i != j)
    rec.w = recurrent_w
    return pop, rec


# ---------------------------------------------------------------------------
# Bölgeye özgü kolaylık builder'ları
# ---------------------------------------------------------------------------

def build_nac(n=100):
    """
    NAc (Nucleus Accumbens) popülasyonu.

    Ödül ve motivasyon merkezi. VNS'de anti-depresan etki bu bölgenin
    yüksek frekanslarda aktive edilmesiyle ilişkilidir.
    tau_m=30ms: Orta dikenli nöronlar (medium spiny neurons) için tipik.

    Döndürür
    --------
    brian2.NeuronGroup
    """
    return build_pop(n, tau_m=30 * ms, refractory=3 * ms)


def build_insula(n=100):
    """
    İnsula (İnsüla Korteksi) popülasyonu.

    İnterosepsiyon, ağrı algısı ve duygusal farkındalık merkezi.
    Craig (2002) mimarisi: NTS → Talamus (VPM/VPL) → İnsula.
    Bu modelde talamatik ara istasyon atlanmış (basitleştirilmiş bağlantı).

    Döndürür
    --------
    brian2.NeuronGroup
    """
    return build_pop(n, tau_m=20 * ms, refractory=3 * ms)


def build_ca3(n=100, recurrent_p=0.12, recurrent_w=1.0 * nS):
    """
    CA3 popülasyonu (build_ca3_r takma adı — daha açıklayıcı isim).

    Episodik bellek ve örüntü tamamlama merkezi.

    Döndürür
    --------
    tuple(NeuronGroup, Synapses)
    """
    return build_ca3_r(n=n, recurrent_p=recurrent_p, recurrent_w=recurrent_w)
