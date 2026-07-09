"""
src/network/nts_relay.py
=========================
NTS (Nucleus Tractus Solitarius) röle ağı — Tsodyks-Markram kısa süreli plastisiti.

NTS, beyin sapındaki ilk röle istasyonudur. Vagus sinirinin afferent lifleri
buraya sinaps yapar (medulla oblongata).

Kullanılan model:
    - LIF (Leaky Integrate-and-Fire): Hızlı, büyük ağlarda kullanılabilir.
      Spike şekli değil, spike zamanlaması modellenir.
    - Tsodyks-Markram (TM) plastisiti: Kısa süreli sinaptik depresyon/fasilitasyon.
      Bu mekanizma, farklı frekansların farklı beyin bölgelerini seçici olarak
      aktive etmesinin (dissociation) temel kaynağıdır.

Kaynak: nerve_frequency_study_colab.ipynb — Cell 21
"""

from brian2 import (
    NeuronGroup, Synapses,
    ms, mV, nS,
    defaultclock,
)

# ---------------------------------------------------------------------------
# NTS nöron modeli — LIF denklemleri
# ---------------------------------------------------------------------------
# Leaky Integrate-and-Fire:
#   dv/dt = (v_rest - v)/tau_m + g_syn*(E_syn - v)/(gL*tau_m)
#   Her değişken (v_rest, E_syn, gL, tau_m, tau_syn) per-neuron parametredir.
NTS_EQS = """
dv/dt = (v_rest - v + g_syn*(E_syn - v)/gL) / tau_m : volt (unless refractory)
dg_syn/dt = -g_syn / tau_syn : siemens
v_rest : volt
E_syn  : volt
gL     : siemens
tau_m  : second
tau_syn: second
"""

# ---------------------------------------------------------------------------
# Tsodyks-Markram (TM) sinaptik plastisiti modeli
# ---------------------------------------------------------------------------
# Değişkenler:
#   u : anlık salınım olasılığı (spike yokken tau_f ile sıfıra doğru azalır)
#   x : mevcut vezikül fraksiyonu (spike yokken tau_d ile 1'e doğru toparlanır)
#   w : maksimum sinaptik ağırlık (siemens)
#   U : temel kullanım olasılığı
#
# (event-driven): Denklem yalnızca spike olayında analitik olarak çözülür;
# her zaman adımında sayısal hesaplama yapılmaz → çok daha hızlı.
TM_SYN_EQS = """
w    : siemens
U    : 1
tau_f: second
tau_d: second
du/dt = -u / tau_f : 1 (event-driven)
dx/dt = (1 - x) / tau_d : 1 (event-driven)
"""

# Spike geldiğinde çalışan güncelleme kuralları:
#   1. Fasilitasyon: u her spike'ta artar
#   2. Postsinaptik iletkenlik: w * u * x kadar artar
#   3. Depresyon: kullanılan vezikül stoktan düşer
TM_ON_PRE = """
u += U * (1 - u)
g_syn_post += w * u * x
x -= u * x
"""


def build_nts_relay(n_nts_neurons=50, synapse_type="depressing",
                    tau_m=20.0, refractory_ms=2.0):
    """
    NTS röle popülasyonu oluşturur.

    Parametreler
    ------------
    n_nts_neurons : int, optional
        NTS popülasyon büyüklüğü. Varsayılan 50.
        Not: Notebook'ta 30 kullanılıyor; 50 daha pürüzsüz ortalama verir.
    synapse_type : str, optional
        "depressing" (varsayılan): Yüksek U, uzun tau_d → depresyon dominant.
        "facilitating": Düşük U, uzun tau_f → fasilitasyon dominant.
    tau_m : float, optional
        Membran zaman sabiti (ms). Varsayılan 20 ms.
    refractory_ms : float, optional
        Mutlak refrakter periyod (ms). Varsayılan 2 ms.

    Döndürür
    --------
    tuple(NeuronGroup, callable)
        - NeuronGroup: NTS popülasyonu.
        - make_synapses: Afferent → NTS sinapsı oluşturan fonksiyon.

    Uyarı
    -----
    Brian2'nin "magic network" modundan kaçınmak için döndürülen tüm nesneler
    açık Network() çağrısına eklenmelidir.
    """
    nts = NeuronGroup(
        n_nts_neurons, NTS_EQS,
        threshold="v > -50*mV",
        reset="v = -65*mV",
        refractory=refractory_ms * ms,
        method="euler",
    )
    nts.v = -65 * mV
    nts.v_rest = -65 * mV
    nts.E_syn = 0 * mV
    nts.gL = 10 * nS
    nts.tau_m = tau_m * ms
    nts.tau_syn = 5 * ms

    if synapse_type == "depressing":
        # Depresyon: yüksek U → her spike'ta büyük stok kullanımı → tükenir
        # Kısa tau_d → toparlanma hızlı ama yüksek frekansta yetersiz
        U_val, tau_f_ms, tau_d_ms = 0.5, 20.0, 700.0
    else:
        # Fasilitasyon: düşük U → ilk spike zayıf, art arda spike'larla u birikir
        U_val, tau_f_ms, tau_d_ms = 0.05, 500.0, 100.0

    def make_synapses(source, p=0.3, w=6.0):
        """Afferent kaynak → NTS hedef TM sinapsı oluşturur."""
        syn = Synapses(source, nts, model=TM_SYN_EQS, on_pre=TM_ON_PRE, method="euler")
        syn.connect(p=p)
        syn.w = w * nS
        syn.U = U_val
        syn.tau_f = tau_f_ms * ms
        syn.tau_d = tau_d_ms * ms
        syn.x = 1.0
        syn.u = U_val
        return syn

    return nts, make_synapses


def make_tm_conn(source, target, U, tau_f, tau_d, p, w):
    """
    Genel amaçlı Tsodyks-Markram sinaptik bağlantı oluşturur.

    Herhangi iki Brian2 nöron grubu arasında TM plastisiti ile sinaps kurar.
    run_full_network() ve downstream bölge bağlantıları için kullanılır.

    Parametreler
    ------------
    source : NeuronGroup veya SpikeGeneratorGroup
        Presinaptik nöron grubu.
    target : NeuronGroup
        Postsinaptik nöron grubu.
    U : float
        Temel salınım olasılığı (0-1).
        Düşük U (≈0.05): fasilitasyon dominant → düşük frekansta sessiz.
        Yüksek U (≈0.5): depresyon dominant → yüksek frekansta tükenir.
    tau_f : brian2.Quantity
        Fasilitasyon zaman sabiti (Brian2 birimi, örn. 500*ms).
    tau_d : brian2.Quantity
        Depresyon / toparlanma zaman sabiti (Brian2 birimi).
    p : float
        Bağlantı olasılığı (0-1).
    w : brian2.Quantity
        Maksimum sinaptik ağırlık (Brian2 birimi, örn. 9*nS).

    Döndürür
    --------
    brian2.Synapses
        Yapılandırılmış ve bağlanmış TM sinaps nesnesi.

    Notlar
    ------
    NTS → NAc (güçlü fasilitasyon): U=0.05, tau_f=500ms → yüksek frekansta aktif.
    NTS → İnsula (hafif depresyon): U=0.4, tau_d=150ms → düşük frekanstan yanıt.
    NTS → CA3 (orta fasilitasyon): U=0.2, tau_f=150ms → karma davranış.
    Kaynak: nerve_frequency_study_colab.ipynb — Cell 26
    """
    syn = Synapses(source, target, model=TM_SYN_EQS, on_pre=TM_ON_PRE, method="euler")
    syn.connect(p=p)
    syn.w = w
    syn.U = U
    syn.tau_f = tau_f
    syn.tau_d = tau_d
    syn.x = 1.0
    syn.u = U
    return syn
