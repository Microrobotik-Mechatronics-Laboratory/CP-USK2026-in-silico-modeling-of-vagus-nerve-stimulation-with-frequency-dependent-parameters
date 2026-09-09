"""
outputs/sekilleri_uret.py
=========================
Poster için tüm şekilleri ve tabloları üretir.

Üretilenler (outputs/sekiller/ altına, 300 dpi PNG):
    sekil1_frekans_yaniti.png      Bölge frekans-yanıt eğrileri (dalga x genlik)
    sekil2_isi_haritasi.png        Bölge x frekans ısı haritası
    sekil3_dc_vs_pulse.png         DC ve pulse uyarımın karşılaştırması
    sekil4_takip_orani.png         Aksonun 1:1 takip oranı vs frekans
    dogrulama1_tm_analitik.png     TM analitik çözüm <-> simülasyon
    dogrulama2_nts_kalibrasyon.png NTS <-> Miles 1986 + Beaumont 2017
    dogrulama3_ileti_hizi.png      İleti hızı <-> Boyd & Kalu 1979
    tablo1_atesleme_hizlari.csv    Ateşleme hızları (ortalama +- SD)
    tablo2_aktivasyon.csv          Aktivasyon eşiği tablosu

Kullanım:
    .venv/bin/python outputs/sekilleri_uret.py outputs/matris.csv outputs/sekiller
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from config.defaults import (
    REGION_COLORS,
    DEFAULT_ACTIVE_THRESHOLD_HZ,
    MRG_PARAMS,
    NTS_PARAMS,
    NAC_PATHWAY_PARAMS,
    INSULA_PATHWAY_PARAMS,
    CA3_PATHWAY_PARAMS,
)

DPI = 300
REGIONS = ["NTS", "NAc", "Insula", "CA3"]
LABEL = {"NTS": "NTS", "NAc": "NAc", "Insula": "İnsula", "CA3": "CA3"}
WAVE_LABEL = {"dc": "DC (monofazik)", "rectangular": "Pulse (bifazik kare dalga)"}

# Boyd & Kalu (1979) J Physiol 289:277 — CV/çap ölçek katsayıları
BOYD_KALU_LOW, BOYD_KALU_HIGH = 4.60, 5.66
# Miles (1986) J Neurophysiol 55:1076 — NTS kararlı-durum PSP oranları
MILES_FREQ = np.array([5.0, 10.0, 20.0])
MILES_RATIO = np.array([0.65, 0.40, 0.20])
# Beaumont ve ark. (2017) Am J Physiol 313:H354 — 20 Hz'de ~%25 aktarım
BEAUMONT_POINT = (20.0, 0.25)


def _freq_tick(f: float) -> str:
    return f"{int(f)}" if f < 1000 else f"{int(f / 1000)}k"


def _save(fig: plt.Figure, out_dir: str, name: str) -> None:
    path = os.path.join(out_dir, name)
    fig.savefig(path, dpi=DPI, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("  ", name)


# ---------------------------------------------------------------------------
# Analitik yardımcılar
# ---------------------------------------------------------------------------

def tm_steady_state(U: float, tau_f_ms: float, tau_d_ms: float, freq_hz: float) -> float:
    """Tsodyks-Markram kararlı-durum genliği (u*x), düzenli spike treni için."""
    period = 1000.0 / freq_hz
    u = U / (1.0 - (1.0 - U) * np.exp(-period / tau_f_ms))
    x = (1.0 - np.exp(-period / tau_d_ms)) / (1.0 - (1.0 - u) * np.exp(-period / tau_d_ms))
    return float(u * x)


# ---------------------------------------------------------------------------
# Ana sonuç şekilleri
# ---------------------------------------------------------------------------

def figure_frequency_response(df: pd.DataFrame, out_dir: str) -> None:
    waves = [w for w in ("dc", "rectangular") if w in df.waveform.unique()]
    amps = sorted(df.amp_mA.unique())
    fig, axes = plt.subplots(len(waves), len(amps),
                             figsize=(4.3 * len(amps), 3.6 * len(waves)),
                             sharex=True, sharey=True, squeeze=False)
    for r, wave in enumerate(waves):
        for c, amp in enumerate(amps):
            ax = axes[r][c]
            sub = df[(df.waveform == wave) & (df.amp_mA == amp)].sort_values("freq_hz")
            for region in REGIONS:
                mean = sub[region].to_numpy()
                sd = sub[f"{region}_sd"].to_numpy()
                ax.plot(sub.freq_hz, mean, marker="o", ms=5, lw=2,
                        color=REGION_COLORS[region], label=LABEL[region])
                ax.fill_between(sub.freq_hz, mean - sd, mean + sd,
                                color=REGION_COLORS[region], alpha=0.20)
            ax.set_xscale("log")
            ax.grid(True, which="both", alpha=0.3)
            ax.axvspan(20, 30, color="0.85", alpha=0.5, zorder=0)
            if r == 0:
                ax.set_title(f"{amp:.0f} mA", fontsize=12, weight="bold")
            if c == 0:
                ax.set_ylabel(f"{WAVE_LABEL[wave]}\nOrt. ateşleme hızı (Hz/nöron)",
                              fontsize=10)
            if r == len(waves) - 1:
                ax.set_xlabel("Stimülasyon frekansı (Hz)")
    axes[0][0].legend(fontsize=9, loc="upper left")
    fig.suptitle("Bölgeye özgü frekans yanıtı (ortalama ± SD, n=5; gri bant: klinik VNS 20–30 Hz)",
                 fontsize=13, weight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    _save(fig, out_dir, "sekil1_frekans_yaniti.png")


def figure_heatmap(df: pd.DataFrame, out_dir: str) -> None:
    waves = [w for w in ("dc", "rectangular") if w in df.waveform.unique()]
    amps = sorted(df.amp_mA.unique())
    freqs = sorted(df.freq_hz.unique())
    vmax = max(df[r].max() for r in REGIONS)
    fig, axes = plt.subplots(len(waves), len(amps),
                             figsize=(4.3 * len(amps), 3.1 * len(waves)),
                             squeeze=False)
    image = None
    for r, wave in enumerate(waves):
        for c, amp in enumerate(amps):
            ax = axes[r][c]
            sub = df[(df.waveform == wave) & (df.amp_mA == amp)].sort_values("freq_hz")
            data = np.array([sub[region].to_numpy() for region in REGIONS])
            image = ax.imshow(data, aspect="auto", cmap="viridis", vmin=0, vmax=vmax)
            ax.set_yticks(range(len(REGIONS)))
            ax.set_yticklabels([LABEL[x] for x in REGIONS], fontsize=9)
            ax.set_xticks(range(len(freqs)))
            ax.set_xticklabels([_freq_tick(f) for f in freqs], fontsize=9)
            for i in range(data.shape[0]):
                for j in range(data.shape[1]):
                    ax.text(j, i, f"{data[i, j]:.1f}", ha="center", va="center",
                            fontsize=8,
                            color="white" if data[i, j] < vmax * 0.6 else "black")
            if r == 0:
                ax.set_title(f"{amp:.0f} mA", fontsize=12, weight="bold")
            if c == 0:
                ax.set_ylabel(WAVE_LABEL[wave], fontsize=10)
            if r == len(waves) - 1:
                ax.set_xlabel("Frekans (Hz)")
    if image is not None:
        fig.colorbar(image, ax=axes, label="Hz/nöron", fraction=0.02)
    fig.suptitle("Bölge aktivite ısı haritası", fontsize=13, weight="bold")
    _save(fig, out_dir, "sekil2_isi_haritasi.png")


def figure_dc_vs_pulse(df: pd.DataFrame, out_dir: str) -> None:
    regions = ["NAc", "Insula", "CA3"]
    freqs = sorted(df.freq_hz.unique())
    waves = [w for w in ("dc", "rectangular") if w in df.waveform.unique()]
    fig, axes = plt.subplots(1, len(regions), figsize=(5.0 * len(regions), 4.2),
                             sharey=True, squeeze=False)
    x = np.arange(len(freqs))
    width = 0.8 / max(len(waves), 1)
    for c, region in enumerate(regions):
        ax = axes[0][c]
        for k, wave in enumerate(waves):
            grouped = (df[df.waveform == wave]
                       .groupby("freq_hz")[[region, f"{region}_sd"]]
                       .mean().reset_index().sort_values("freq_hz"))
            ax.bar(x + k * width, grouped[region], width,
                   yerr=grouped[f"{region}_sd"], capsize=3,
                   label=WAVE_LABEL[wave], color=["#4C72B0", "#DD8452"][k])
        ax.set_xticks(x + width * (len(waves) - 1) / 2)
        ax.set_xticklabels([_freq_tick(f) for f in freqs])
        ax.set_title(LABEL[region], fontsize=12, weight="bold")
        ax.set_xlabel("Frekans (Hz)")
        ax.grid(True, axis="y", alpha=0.3)
        if c == 0:
            ax.set_ylabel("Ort. ateşleme hızı (Hz/nöron)")
            ax.legend(fontsize=9)
    fig.suptitle("DC ve pulse uyarımın karşılaştırması (genlikler ortalanmış)",
                 fontsize=13, weight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    _save(fig, out_dir, "sekil3_dc_vs_pulse.png")


def figure_follow_ratio(df: pd.DataFrame, out_dir: str) -> None:
    waves = [w for w in ("dc", "rectangular") if w in df.waveform.unique()]
    fig, axes = plt.subplots(1, len(waves), figsize=(5.4 * len(waves), 4.3),
                             sharey=True, squeeze=False)
    colors = plt.cm.viridis(np.linspace(0.15, 0.85, len(sorted(df.amp_mA.unique()))))
    for c, wave in enumerate(waves):
        ax = axes[0][c]
        for color, amp in zip(colors, sorted(df.amp_mA.unique())):
            sub = df[(df.waveform == wave) & (df.amp_mA == amp)].sort_values("freq_hz")
            ax.plot(sub.freq_hz, sub.follow_ratio, marker="o", ms=6, lw=2,
                    color=color, label=f"{amp:.0f} mA")
        ax.axhline(1.0, color="k", ls="--", lw=1.2, alpha=0.7)
        ax.text(1.2, 1.04, "1:1 takip", fontsize=8)
        ax.set_xscale("log")
        ax.set_xlabel("Stimülasyon frekansı (Hz)")
        ax.set_title(WAVE_LABEL[wave], fontsize=12, weight="bold")
        ax.grid(True, which="both", alpha=0.3)
        if c == 0:
            ax.set_ylabel("Takip oranı (akson spike / puls)")
            ax.legend(fontsize=9)
    fig.suptitle("Aksonun uyarımı takip oranı — yüksek frekansta iletim bloku",
                 fontsize=13, weight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    _save(fig, out_dir, "sekil4_takip_orani.png")


# ---------------------------------------------------------------------------
# Doğrulama şekilleri
# ---------------------------------------------------------------------------

def figure_tm_validation(out_dir: str) -> None:
    from brian2 import (NeuronGroup, Network, Synapses, SpikeGeneratorGroup,
                        StateMonitor, defaultclock, ms, start_scope)

    def simulate(U: float, tau_f: float, tau_d: float, freq: float,
                 n_spikes: int = 60) -> float:
        start_scope()
        defaultclock.dt = 0.05 * ms
        period = 1000.0 / freq
        times = np.arange(1, n_spikes + 1) * period
        src = SpikeGeneratorGroup(1, np.zeros(n_spikes, dtype=int), times * ms)
        tgt = NeuronGroup(1, "dv/dt = -v/(10*ms) : 1")
        syn = Synapses(src, tgt, model="""
            U : 1
            tau_f : second
            tau_d : second
            du/dt = -u/tau_f : 1 (clock-driven)
            dx/dt = (1-x)/tau_d : 1 (clock-driven)
            ux : 1
        """, on_pre="u += U*(1-u); ux = u*x; x -= u*x", method="euler")
        syn.connect()
        syn.U, syn.tau_f, syn.tau_d = U, tau_f * ms, tau_d * ms
        syn.x, syn.u = 1.0, U
        mon = StateMonitor(syn, "ux", record=0, dt=period * ms)
        Network(src, tgt, syn, mon).run((times[-1] + period) * ms)
        return float(np.asarray(mon.ux[0])[-1])

    pathways = [("NTS (afferent)", NTS_PARAMS), ("NAc", NAC_PATHWAY_PARAMS),
                ("İnsula", INSULA_PATHWAY_PARAMS), ("CA3", CA3_PATHWAY_PARAMS)]
    colors = {"NTS (afferent)": REGION_COLORS["NTS"], "NAc": REGION_COLORS["NAc"],
              "İnsula": REGION_COLORS["Insula"], "CA3": REGION_COLORS["CA3"]}
    freqs = np.array([1, 2, 5, 10, 20, 50, 100, 200, 500], dtype=float)

    fig, (ax1, ax2, ax3) = plt.subplots(
        3, 1, figsize=(7.4, 9.6), sharex=True,
        gridspec_kw={"height_ratios": [3, 3, 1.3]})
    worst = 0.0
    for name, params in pathways:
        analytic = np.array([tm_steady_state(params["U"], params["tau_f_ms"],
                                             params["tau_d_ms"], f) for f in freqs])
        sim = np.array([simulate(params["U"], params["tau_f_ms"],
                                 params["tau_d_ms"], f) for f in freqs])
        ax1.plot(freqs, analytic, "-", color=colors[name], lw=2, label=f"{name}")
        ax1.plot(freqs, sim, "o", color=colors[name], ms=6, mfc="white", mew=1.8)
        ax2.plot(freqs, freqs * analytic, "-", color=colors[name], lw=2, label=name)
        ax2.plot(freqs, freqs * sim, "o", color=colors[name], ms=6, mfc="white", mew=1.8)
        ax2.axhline(1000.0 / params["tau_d_ms"], color=colors[name],
                    ls=":", lw=1.2, alpha=0.8)
        residual = 100.0 * (sim - analytic) / analytic
        worst = max(worst, float(np.max(np.abs(residual))))
        ax3.plot(freqs, residual, "o-", color=colors[name], ms=4, lw=1.2)

    ax1.set_xscale("log"); ax1.set_yscale("log")
    ax1.set_ylabel("Kararlı-durum genliği  u·x")
    ax1.legend(fontsize=8, ncol=2); ax1.grid(True, which="both", alpha=0.3)
    ax1.set_title("Simülasyon, Tsodyks–Markram analitik çözümüyle örtüşüyor "
                  f"(maks. kalıntı %{worst:.2f})", fontsize=12, weight="bold")
    ax2.set_xscale("log"); ax2.set_ylabel("İletilen sürüş  f·u·x  (Hz)")
    ax2.grid(True, which="both", alpha=0.3); ax2.legend(fontsize=8, ncol=2)
    ax2.text(0.02, 0.95, "noktalı çizgiler: doygunluk sınırı 1/τ_d",
             transform=ax2.transAxes, fontsize=8, va="top")
    ax3.axhline(0, color="k", lw=0.8); ax3.set_ylim(-8, 8)
    ax3.set_ylabel("kalıntı (%)"); ax3.set_xlabel("Frekans (Hz)")
    ax3.grid(True, which="both", alpha=0.3)
    fig.tight_layout()
    _save(fig, out_dir, "dogrulama1_tm_analitik.png")


def figure_nts_calibration(out_dir: str) -> None:
    def ratio(U: float, tau_f: float, tau_d: float, f: float) -> float:
        return tm_steady_state(U, tau_f, tau_d, f) / U

    tau_f = NTS_PARAMS["tau_f_ms"]
    grid = np.logspace(0, 2, 80)
    fig, ax = plt.subplots(figsize=(7.2, 4.9))
    ax.plot(grid, [ratio(NTS_PARAMS["U"], tau_f, NTS_PARAMS["tau_d_ms"], f) for f in grid],
            lw=2.4, color="#27ae60",
            label=(f"Model (kalibre): U={NTS_PARAMS['U']}, "
                   f"τ_d={NTS_PARAMS['tau_d_ms']:.0f} ms"))
    ax.plot(grid, [ratio(0.5, tau_f, 700.0, f) for f in grid],
            lw=2.0, color="#c0392b", ls="--",
            label="Kalibrasyon öncesi: U=0.50, τ_d=700 ms")
    ax.plot(MILES_FREQ, MILES_RATIO, "ks", ms=11, zorder=5,
            label="Miles (1986) — deneysel")
    ax.plot(*BEAUMONT_POINT, "k^", ms=11, zorder=5,
            label="Beaumont (2017) — bağımsız doğrulama")
    ax.set_xscale("log")
    ax.set_xlabel("Uyarım frekansı (Hz)")
    ax.set_ylabel("Kararlı-durum PSP / ilk PSP")
    ax.set_title("NTS röle sinapsı deneysel frekans-depresyon eğrisini yeniden üretiyor",
                 fontsize=12, weight="bold")
    ax.grid(True, which="both", alpha=0.3)
    ax.legend(fontsize=9)
    fig.tight_layout()
    _save(fig, out_dir, "dogrulama2_nts_kalibrasyon.png")


def figure_conduction_velocity(out_dir: str) -> None:
    from neuron import h
    from src.models.mrg_axon import MRGAxon
    from src.stim.extracellular_field import biphasic_waveform, run_stimulation_loop

    def measure(diam: float, n_nodes: int = 15, dur: float = 40.0,
                dt: float = 0.005) -> float | None:
        for amp in (250.0, 500.0, 1000.0, 2000.0, 4000.0, 8000.0, 16000.0):
            fiber = MRGAxon(diameter_um=diam, n_nodes=n_nodes)
            coords, secs = fiber.section_coords(), fiber.all_sections()
            keep, rec = [], {}
            for idx in (4, n_nodes - 2):
                nc = h.NetCon(fiber.nodes[idx](0.5)._ref_v, None, sec=fiber.nodes[idx])
                nc.threshold = -20
                vec = h.Vector(); nc.record(vec)
                keep.append(nc); rec[idx] = vec
            _, i_vec = biphasic_waveform(1000.0 / dur, amp, dur, dt, pulse_width_ms=0.1)
            run_stimulation_loop(secs, coords, (500.0, 0.0, 3000.0), i_vec, dt,
                                 v_init=-80.0)
            prox, dist = list(rec[4]), list(rec[n_nodes - 2])
            if prox and dist and dist[0] > prox[0]:
                distance_m = (coords[2 * (n_nodes - 2)][2] - coords[2 * 4][2]) * 1e-6
                return distance_m / ((dist[0] - prox[0]) * 1e-3)
        return None

    diams = sorted(MRG_PARAMS.keys())
    measured = [measure(d) for d in diams]

    fig, ax = plt.subplots(figsize=(7.2, 5.0))
    grid = np.linspace(min(diams) - 1, max(diams) + 2, 60)
    ax.fill_between(grid, BOYD_KALU_LOW * grid, BOYD_KALU_HIGH * grid,
                    color="0.75", alpha=0.55,
                    label="Boyd & Kalu (1979) deneysel bant\n(4.60·D – 5.66·D)")
    ax.plot(grid, BOYD_KALU_LOW * grid, color="0.45", lw=1)
    ax.plot(grid, BOYD_KALU_HIGH * grid, color="0.45", lw=1)
    ax.axhspan(30.5, 62.8, color="#27ae60", alpha=0.12,
               label="İnsan vagus Aα aralığı\n(Musselman ve ark. 2023)")
    xs = [d for d, v in zip(diams, measured) if v]
    ys = [v for v in measured if v]
    ax.plot(xs, ys, "o-", color="#27ae60", ms=10, lw=2, label="Model (bu çalışma)")
    ax.set_xlabel("Lif çapı (µm)")
    ax.set_ylabel("İleti hızı (m/s)")
    ax.set_title("İleti hızı — lif çapı ilişkisi", fontsize=12, weight="bold")
    ax.grid(True, which="both", alpha=0.3)
    ax.legend(fontsize=9, loc="upper left")
    fig.tight_layout()
    _save(fig, out_dir, "dogrulama3_ileti_hizi.png")
    for d, v in zip(diams, measured):
        print(f"     CV {d:>5} µm -> {v if v is None else round(v, 1)} m/s "
              f"(beklenen {BOYD_KALU_LOW * d:.0f}-{BOYD_KALU_HIGH * d:.0f})")


# ---------------------------------------------------------------------------
# Tablolar
# ---------------------------------------------------------------------------

def write_tables(df: pd.DataFrame, out_dir: str) -> None:
    table1 = df[["waveform", "amp_mA", "freq_hz", "n_pulses",
                 "n_axon_spikes", "follow_ratio"]].copy()
    for region in REGIONS:
        table1[LABEL[region]] = (df[region].round(2).astype(str) + " ± "
                                 + df[f"{region}_sd"].round(2).astype(str))
    table1.to_csv(os.path.join(out_dir, "tablo1_atesleme_hizlari.csv"), index=False)
    print("   tablo1_atesleme_hizlari.csv")

    table2 = df[["waveform", "amp_mA", "freq_hz"]].copy()
    for region in REGIONS:
        table2[LABEL[region]] = np.where(df[region] > DEFAULT_ACTIVE_THRESHOLD_HZ, "+", "-")
    table2.to_csv(os.path.join(out_dir, "tablo2_aktivasyon.csv"), index=False)
    print("   tablo2_aktivasyon.csv")


def main() -> None:
    csv_path = sys.argv[1] if len(sys.argv) > 1 else "outputs/matris.csv"
    out_dir = sys.argv[2] if len(sys.argv) > 2 else "outputs/sekiller"
    os.makedirs(out_dir, exist_ok=True)
    df = pd.read_csv(csv_path)

    print("Ana sonuç şekilleri:")
    figure_frequency_response(df, out_dir)
    figure_heatmap(df, out_dir)
    figure_dc_vs_pulse(df, out_dir)
    figure_follow_ratio(df, out_dir)

    print("Doğrulama şekilleri:")
    figure_tm_validation(out_dir)
    figure_nts_calibration(out_dir)
    figure_conduction_velocity(out_dir)

    print("Tablolar:")
    write_tables(df, out_dir)
    print(f"\nTümü hazır -> {out_dir}")


if __name__ == "__main__":
    main()
