"""
src/pipeline/level23.py
========================
Level 2-3 pipeline — Brian2 NTS relay ve downstream beyin bölgeleri ağı.

Level 1'den gelen spike zamanları (NEURON çıktısı) burada Brian2'ye aktarılır
ve tüm ağ simülasyonu çalıştırılır.

İçerik:
    - run_levels_2_3   : Basit NTS → CA3 pipeline (end-to-end test için)
    - run_full_network : Tam NAc / İnsula / CA3 pathway-specific plastisiti ağı

Kaynak: nerve_frequency_study_colab.ipynb — Cell 24 (run_levels_2_3) + Cell 26-27
"""

from brian2 import (
    NeuronGroup, Synapses, SpikeMonitor, Network,
    run,
    ms, mV, nS,
    defaultclock,
    start_scope,
)
from typing import Sequence

from src.network.bridge import bundle_from_single_fiber
from src.network.nts_relay import build_nts_relay, make_tm_conn
from src.network.brain_regions import build_pop, build_ca3_r
from config.defaults import (
    NTS_PARAMS,
    NAC_PATHWAY_PARAMS,
    INSULA_PATHWAY_PARAMS,
    CA3_PATHWAY_PARAMS,
    DEFAULT_BRIAN_DT_MS,
)


def _connect_region_simple(
    source: NeuronGroup, target: NeuronGroup, p: float = 0.25, w: float = 5.0,
) -> Synapses:
    """
    İki popülasyon arasında basit AMPA benzeri sinaps kurar (TM plastisiti olmadan).

    Yalnızca run_levels_2_3() (test amaçlı basit pipeline) için kullanılır.
    TM plastisitesi YOK — sabit ağırlıklı statik AMPA sinapsı. Gerçek pipeline
    (run_full_network()) için src/network/nts_relay.py içindeki make_tm_conn()
    kullanılır (tam Tsodyks-Markram plastisitesi).

    Parametreler
    ------------
    source : NeuronGroup
        Presinaptik popülasyon.
    target : NeuronGroup
        Postsinaptik popülasyon.
    p : float, optional
        Bağlantı olasılığı. Varsayılan 0.25.
    w : float, optional
        Sinaptik ağırlık (nS). Varsayılan 5.0 nS.

    Döndürür
    --------
    brian2.Synapses
    """
    syn = Synapses(source, target, on_pre="g_syn_post += w", model="w : siemens")
    syn.connect(p=p)
    syn.w = w * nS
    return syn


def run_levels_2_3(
    spike_times_ms: Sequence[float], duration_ms: float = 200,
    n_nts: int = 30, n_ca3: int = 100,
) -> tuple[SpikeMonitor, SpikeMonitor]:
    """
    Basitleştirilmiş Level 2-3 pipeline: NTS relay → CA3.

    End-to-end pipeline bağlantısını test etmek için kullanılır (Section 10).
    Yalnızca NTS ve CA3 içerir; NAc ve İnsula yok.

    Parametreler
    ------------
    spike_times_ms : list of float
        Level 1'den gelen axon spike zamanları (ms).
    duration_ms : float, optional
        Simülasyon süresi (ms). Varsayılan 200 ms.
    n_nts : int, optional
        NTS nöron sayısı. Varsayılan 30.
    n_ca3 : int, optional
        CA3 nöron sayısı. Varsayılan 100.

    Döndürür
    --------
    tuple(SpikeMonitor, SpikeMonitor)
        - nts_mon: NTS spike monitörü.
        - ca3_mon: CA3 spike monitörü.

    Notlar
    ------
    Bu fonksiyon "magic network" modunda çalışır (açık Network() yok).
    Daha güvenilir sonuç için run_full_network() kullanın.
    """
    start_scope()

    afferent = bundle_from_single_fiber(spike_times_ms, n_fibers=20)

    nts, make_synapses = build_nts_relay(
        n_nts_neurons=n_nts,
        synapse_type="depressing",
        tau_m=NTS_PARAMS["tau_m_ms"],
        refractory_ms=NTS_PARAMS["refractory_ms"],
    )
    nts_syn = make_synapses(afferent, p=NTS_PARAMS["p"], w=NTS_PARAMS["w_nS"])

    ca3_pop, ca3_recurrent = build_ca3_r(n=n_ca3)
    relay_to_ca3 = _connect_region_simple(nts, ca3_pop, p=0.25)

    nts_mon = SpikeMonitor(nts)
    ca3_mon = SpikeMonitor(ca3_pop)

    defaultclock.dt = DEFAULT_BRIAN_DT_MS * ms
    run(duration_ms * ms)

    return nts_mon, ca3_mon


def run_full_network(
    spike_times_ms: Sequence[float], duration_ms: float, n_fibers: int = 20,
) -> dict[str, SpikeMonitor]:
    """
    Tam Level 2-3 ağı: fiber demeti → NTS → NAc / İnsula / CA3.

    Her downstream bölge kendi pathway-specific TM plastisitesine sahiptir.
    Açık Network() nesnesi kullanılır — hiçbir bileşen sessizce atlanmaz.

    Parametreler
    ------------
    spike_times_ms : list of float
        Level 1'den gelen axon spike zamanları (ms).
    duration_ms : float
        Simülasyon süresi (ms).
    n_fibers : int, optional
        Fiber demet büyüklüğü. Varsayılan 20.

    Döndürür
    --------
    dict of {str: SpikeMonitor}
        Anahtarlar: "NTS", "NAc", "Insula", "CA3".
        Her değer: ilgili popülasyonun SpikeMonitor nesnesi.

    Notlar
    ------
    NAc (güçlü fasilitasyon, U=0.05, tau_f=500ms):
        Düşük frekansta sessiz → yüksek frekansta aktif.
    İnsula (hafif depresyon, U=0.4, tau_d=150ms):
        Düşük frekanstan itibaren yanıt — direkt röle gibi.
    CA3 (orta fasilitasyon, U=0.2, tau_f=150ms + rekürrent):
        Karma davranış + rekürrent amplifikasyon.

    Uyarı
    -----
    CA3 rekürrent ağırlığı (1 nS) kasıtlı olarak düşük tutulmuştur.
    Daha yüksek değer → runaway excitation (sonsuz döngü) riski.
    Gelecek iyileştirme: GABAerjik inhibitör internöron eklemek.
    Kaynak: nerve_frequency_study_colab.ipynb — Cell 27
    """
    start_scope()

    afferent = bundle_from_single_fiber(spike_times_ms, n_fibers=n_fibers)

    # NTS röle
    nts = build_pop(int(NTS_PARAMS["n_neurons"]), tau_m=NTS_PARAMS["tau_m_ms"] * ms,
                    refractory=NTS_PARAMS["refractory_ms"] * ms)
    nts_syn = make_tm_conn(
        afferent, nts,
        U=NTS_PARAMS["U"],
        tau_f=NTS_PARAMS["tau_f_ms"] * ms,
        tau_d=NTS_PARAMS["tau_d_ms"] * ms,
        p=NTS_PARAMS["p"],
        w=NTS_PARAMS["w_nS"] * nS,
    )

    # Downstream bölgeler
    nac_pop    = build_pop(int(NAC_PATHWAY_PARAMS["n_neurons"]),
                           tau_m=NAC_PATHWAY_PARAMS["tau_m_ms"] * ms,
                           refractory=NAC_PATHWAY_PARAMS["refractory_ms"] * ms)
    insula_pop = build_pop(int(INSULA_PATHWAY_PARAMS["n_neurons"]),
                           tau_m=INSULA_PATHWAY_PARAMS["tau_m_ms"] * ms,
                           refractory=INSULA_PATHWAY_PARAMS["refractory_ms"] * ms)
    ca3_pop, ca3_rec = build_ca3_r(
        n=int(CA3_PATHWAY_PARAMS["n_neurons"]),
        recurrent_p=CA3_PATHWAY_PARAMS["recurrent_p"],
        recurrent_w=CA3_PATHWAY_PARAMS["recurrent_w_nS"] * nS,
    )

    # Pathway-specific TM sinapsları
    c_nac = make_tm_conn(
        nts, nac_pop,
        U=NAC_PATHWAY_PARAMS["U"],
        tau_f=NAC_PATHWAY_PARAMS["tau_f_ms"] * ms,
        tau_d=NAC_PATHWAY_PARAMS["tau_d_ms"] * ms,
        p=NAC_PATHWAY_PARAMS["p"],
        w=NAC_PATHWAY_PARAMS["w_nS"] * nS,
    )
    c_insula = make_tm_conn(
        nts, insula_pop,
        U=INSULA_PATHWAY_PARAMS["U"],
        tau_f=INSULA_PATHWAY_PARAMS["tau_f_ms"] * ms,
        tau_d=INSULA_PATHWAY_PARAMS["tau_d_ms"] * ms,
        p=INSULA_PATHWAY_PARAMS["p"],
        w=INSULA_PATHWAY_PARAMS["w_nS"] * nS,
    )
    c_ca3 = make_tm_conn(
        nts, ca3_pop,
        U=CA3_PATHWAY_PARAMS["U"],
        tau_f=CA3_PATHWAY_PARAMS["tau_f_ms"] * ms,
        tau_d=CA3_PATHWAY_PARAMS["tau_d_ms"] * ms,
        p=CA3_PATHWAY_PARAMS["p"],
        w=CA3_PATHWAY_PARAMS["w_nS"] * nS,
    )

    # Spike monitörleri
    mons = {
        "NTS":   SpikeMonitor(nts),
        "NAc":   SpikeMonitor(nac_pop),
        "Insula": SpikeMonitor(insula_pop),
        "CA3":   SpikeMonitor(ca3_pop),
    }

    defaultclock.dt = DEFAULT_BRIAN_DT_MS * ms
    net = Network(
        afferent, nts, nts_syn,
        nac_pop, insula_pop, ca3_pop, ca3_rec,
        c_nac, c_insula, c_ca3,
        *mons.values(),
    )
    net.run(duration_ms * ms)
    return mons
