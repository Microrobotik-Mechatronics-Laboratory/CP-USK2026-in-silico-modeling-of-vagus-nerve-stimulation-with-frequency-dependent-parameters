"""
outputs/mimari_diyagram.py
==========================
Poster "Model Bileşenleri ve Kontrol Mimarisi" bölümü için şema diyagramı.

Tüm sayısal değerler `config/defaults.py`'den okunur; parametreler değişirse
diyagram da güncel kalır (elle senkronlanacak sabit yoktur).

Kullanım:
    .venv/bin/python outputs/mimari_diyagram.py outputs/sekiller
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle

from config.defaults import (
    AXON_REFRACTORY_MS,
    CA3_PATHWAY_PARAMS,
    DEFAULT_BRIAN_DT_MS,
    DEFAULT_DT,
    DEFAULT_ELEC_DIST,
    DEFAULT_ELEC_Z,
    DEFAULT_FIBER_DIAM,
    DEFAULT_N_FIBERS,
    DEFAULT_N_NODES,
    DEFAULT_N_REPEATS,
    DEFAULT_PULSE_WIDTH,
    INSULA_PATHWAY_PARAMS,
    MRG_PARAMS,
    NAC_PATHWAY_PARAMS,
    NTS_PARAMS,
    REGION_COLORS,
)

DPI = 300

C_STIM = "#4C72B0"
C_L1 = "#b45f06"
C_BRIDGE = "#7f7f7f"
C_NTS = REGION_COLORS["NTS"]
C_NAC = REGION_COLORS["NAc"]
C_INS = REGION_COLORS["Insula"]
C_CA3 = REGION_COLORS["CA3"]
C_OUT = "#4a4a4a"
INK = "#1a1a1a"


def band(ax, x, y, w, h, color, title, subtitle=None, lw=2.0, fill_alpha=0.07):
    """Başlık şeridi olan yuvarlak köşeli kutu çizer."""
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h, boxstyle="round,pad=0.6,rounding_size=1.2",
        linewidth=lw, edgecolor=color, facecolor=color, alpha=fill_alpha, zorder=1))
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h, boxstyle="round,pad=0.6,rounding_size=1.2",
        linewidth=lw, edgecolor=color, facecolor="none", zorder=3))
    ax.text(x + 1.4, y + h - 2.0, title, fontsize=12.5, weight="bold",
            color=color, va="top", ha="left", zorder=4)
    if subtitle:
        ax.text(x + w - 1.4, y + h - 2.0, subtitle, fontsize=9.5,
                color=color, va="top", ha="right", style="italic", zorder=4)


def arrow(ax, x0, y0, x1, y1, color=INK, label=None, lw=2.2, label_dx=1.2):
    ax.add_patch(FancyArrowPatch(
        (x0, y0), (x1, y1), arrowstyle="-|>", mutation_scale=18,
        linewidth=lw, color=color, zorder=5,
        shrinkA=0, shrinkB=0))
    if label:
        ax.text((x0 + x1) / 2 + label_dx, (y0 + y1) / 2, label,
                fontsize=8.8, color=color, va="center", ha="left", zorder=6)


def draw_axon(ax, x, y, w, n_nodes=7):
    """Miyelinli akson şeması: düğüm (koyu) + internode (açık, miyelinli)."""
    node_w, gap = w * 0.022, w * 0.128
    cursor = x
    for i in range(n_nodes):
        ax.add_patch(Rectangle((cursor, y - 0.9), node_w, 1.8,
                               facecolor=C_L1, edgecolor="none", zorder=4))
        cursor += node_w
        if i < n_nodes - 1:
            ax.add_patch(Rectangle((cursor, y - 1.5), gap, 3.0,
                                   facecolor="white", edgecolor=C_L1,
                                   linewidth=1.4, zorder=3))
            ax.text(cursor + gap / 2, y, "▨", fontsize=6.5, color=C_L1,
                    ha="center", va="center", zorder=4)
            cursor += gap
    ax.text(x, y - 3.0, "Ranvier düğümü (axnode)", fontsize=7.6, color=C_L1,
            ha="left", va="top")
    ax.text(cursor, y - 3.0, "internode (miyelin)", fontsize=7.6, color=C_L1,
            ha="right", va="top")
    return cursor


def main() -> None:
    out_dir = sys.argv[1] if len(sys.argv) > 1 else "outputs/sekiller"
    os.makedirs(out_dir, exist_ok=True)

    node_d, node_l, internode_l, n_lamellae, axon_d = MRG_PARAMS[DEFAULT_FIBER_DIAM]

    fig, ax = plt.subplots(figsize=(11.5, 15.4))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 149)
    ax.axis("off")

    # ---------------------------------------------------------------- Uyarım
    band(ax, 6, 131, 88, 16, C_STIM, "UYARIM",
         "ekstrasellüler, nokta kaynak (McNeal 1976)")
    ax.text(9, 141.0,
            f"$V_e = \\rho I\\,/\\,(4\\pi r)$   ·   ρ = 300 Ω·cm   ·   "
            f"elektrot (x, z) = ({DEFAULT_ELEC_DIST:.0f}, {DEFAULT_ELEC_Z:.0f}) µm",
            fontsize=10.2, color=INK, va="top", ha="left")
    ax.text(9, 136.8,
            f"dalga şekli: DC (monofazik) · pulse (bifazik kare) · sinüs (KHFAC)   ·   "
            f"puls genişliği {DEFAULT_PULSE_WIDTH} ms",
            fontsize=9.4, color=INK, va="top", ha="left")
    ax.text(9, 133.6, "genlik 1 / 2 / 3 mA   ·   frekans 1 Hz – 10 kHz",
            fontsize=9.4, color=INK, va="top", ha="left")

    arrow(ax, 50, 130.4, 50, 124.6, C_STIM,
          "  her segmentin $e_{extracellular}$ değeri")

    # -------------------------------------------------------------- Level 1
    band(ax, 6, 96, 88, 28, C_L1, "LEVEL 1 — NEURON",
         "periferik akson biyofiziği")
    draw_axon(ax, 11, 115.0, 78)
    ax.text(9, 108.0,
            "MRG miyelinli akson (McIntyre ve ark. 2002, ModelDB 3810)",
            fontsize=10.0, color=INK, va="top", ha="left", weight="bold")
    ax.text(9, 104.7,
            f"çap {DEFAULT_FIBER_DIAM} µm  ·  {DEFAULT_N_NODES} düğüm  ·  "
            f"internode {internode_l:.0f} µm  ·  {n_lamellae} miyelin lameli",
            fontsize=9.2, color=INK, va="top", ha="left")
    ax.text(9, 101.5,
            f"internode: $c_m = 1/(2n_l)$, $g_{{pas}} = 0.001/(2n_l)$   ·   "
            f"dt = {DEFAULT_DT} ms",
            fontsize=9.2, color=INK, va="top", ha="left")
    ax.text(9, 98.3,
            "çıktı: distal düğümde spike zamanları (eşik −20 mV)",
            fontsize=9.2, color=INK, va="top", ha="left", style="italic")

    arrow(ax, 50, 95.4, 50, 89.6, C_BRIDGE)

    # --------------------------------------------------------------- Köprü
    band(ax, 6, 73, 88, 16, C_BRIDGE, "KÖPRÜ — NEURON → Brian2",
         "tek yönlü (offline) bağlaşım", fill_alpha=0.05)
    ax.text(9, 83.2,
            f"tek aksonun spike treni → {DEFAULT_N_FIBERS} fiberlik demet "
            f"(Gauss jitter 0.4 ms)",
            fontsize=9.8, color=INK, va="top", ha="left")
    ax.text(9, 79.6,
            f"fiber başına mutlak refrakter periyot {AXON_REFRACTORY_MS:.0f} ms  ·  "
            f"Brian2 dt = {DEFAULT_BRIAN_DT_MS} ms ızgarasına oturtma",
            fontsize=9.2, color=INK, va="top", ha="left")
    ax.text(9, 76.2, "SpikeGeneratorGroup",
            fontsize=9.0, color=C_BRIDGE, va="top", ha="left", family="monospace")

    arrow(ax, 50, 72.4, 50, 66.6, C_NTS)

    # -------------------------------------------------------------- Level 2
    band(ax, 6, 50, 88, 16, C_NTS, "LEVEL 2 — Brian2",
         "beyin sapı rölesi")
    ax.text(9, 60.2,
            f"NTS (nucleus tractus solitarius) — {int(NTS_PARAMS['n_neurons'])} LIF nöron",
            fontsize=10.0, color=INK, va="top", ha="left", weight="bold")
    ax.text(9, 56.8,
            f"afferent → NTS Tsodyks–Markram sinapsı:  "
            f"U = {NTS_PARAMS['U']}, "
            f"$\\tau_f$ = {NTS_PARAMS['tau_f_ms']:.0f} ms, "
            f"$\\tau_d$ = {NTS_PARAMS['tau_d_ms']:.0f} ms, "
            f"p = {NTS_PARAMS['p']}, w = {NTS_PARAMS['w_nS']:.0f} nS",
            fontsize=9.2, color=INK, va="top", ha="left")
    ax.text(9, 53.4,
            "deneysel kalibrasyon: Miles (1986) + Chen ve ark. (1999); "
            "bağımsız doğrulama: Beaumont ve ark. (2017)",
            fontsize=8.8, color=C_NTS, va="top", ha="left", style="italic")

    # Level 2 -> Level 3 dallanmasi
    arrow(ax, 50, 49.4, 50, 45.5, INK)
    ax.plot([19.5, 79.5], [45.5, 45.5], color=INK, lw=2.2, zorder=5,
            solid_capstyle="round")
    ax.text(51.5, 47.0, "yolağa özgü TM plastisitesi", fontsize=8.8,
            color=INK, va="center", ha="left")
    for xc, col in ((19.5, C_NAC), (50, C_INS), (79.5, C_CA3)):
        arrow(ax, xc, 45.5, xc, 40.6, col)

    # -------------------------------------------------------------- Level 3
    ax.text(50, 37.4, "LEVEL 3 — Brian2  ·  üst merkez popülasyonları",
            fontsize=12.5, weight="bold", color=INK, ha="center", va="bottom")

    specs = [
        (6, C_NAC, "NAc", NAC_PATHWAY_PARAMS,
         "güçlü fasilitasyon", "ödül / motivasyon"),
        (36.5, C_INS, "İnsula", INSULA_PATHWAY_PARAMS,
         "hafif depresyon", "interosepsiyon"),
        (67, C_CA3, "CA3", CA3_PATHWAY_PARAMS,
         "orta fasilitasyon",
         f"rekürrent kolateral: p = {CA3_PATHWAY_PARAMS['recurrent_p']}, "
         f"w = {CA3_PATHWAY_PARAMS['recurrent_w_nS']:.0f} nS"),
    ]
    for x0, col, name, prm, kind, footer in specs:
        band(ax, x0, 14, 27, 21, col, name, None)
        ax.text(x0 + 1.4, 30.2, kind, fontsize=9.2, color=col,
                va="top", ha="left", style="italic")
        ax.text(x0 + 1.4, 27.2,
                f"{int(prm['n_neurons'])} LIF nöron  ·  "
                f"$\\tau_m$ = {prm['tau_m_ms']:.0f} ms",
                fontsize=8.6, color=INK, va="top", ha="left")
        ax.text(x0 + 1.4, 24.0, f"U = {prm['U']}",
                fontsize=8.6, color=INK, va="top", ha="left")
        ax.text(x0 + 1.4, 21.4,
                f"$\\tau_f$ = {prm['tau_f_ms']:.0f} ms, "
                f"$\\tau_d$ = {prm['tau_d_ms']:.0f} ms",
                fontsize=8.6, color=INK, va="top", ha="left")
        ax.text(x0 + 1.4, 18.8,
                f"p = {prm['p']}, w = {prm['w_nS']:.0f} nS",
                fontsize=8.6, color=INK, va="top", ha="left")
        ax.text(x0 + 1.4, 15.4, footer, fontsize=7.8, color=col,
                va="bottom", ha="left", wrap=True)

    for xc, col in ((19.5, C_NAC), (50, C_INS), (79.5, C_CA3)):
        arrow(ax, xc, 13.4, xc, 10.6, col)

    # ---------------------------------------------------------------- Çıktı
    band(ax, 6, 1, 88, 9, C_OUT, "ÇIKTI VE ANALİZ", None, fill_alpha=0.05)
    ax.text(9, 5.6,
            "nöron başına ortalama ateşleme hızı (Hz/nöron)  ·  takip oranı "
            "(akson spike / puls)  ·  ayrışma tablosu",
            fontsize=9.2, color=INK, ha="left", va="top")
    ax.text(9, 2.9,
            f"sabit analiz penceresi  ·  koşul başına {DEFAULT_N_REPEATS} tekrar "
            f"(ortalama ± SD), sabit tohum",
            fontsize=9.2, color=INK, ha="left", va="top")

    fig.suptitle("Model Bileşenleri ve Kontrol Mimarisi",
                 fontsize=17, weight="bold", y=0.988)
    fig.text(0.5, 0.9715,
             "Vagus siniri stimülasyonunun çok ölçekli in siliko modeli — "
             "NEURON (Level 1) + Brian2 (Level 2–3)",
             fontsize=10.5, color="#555555", ha="center", va="top")
    fig.tight_layout(rect=(0, 0, 1, 0.966))

    path = os.path.join(out_dir, "sekil0_mimari.png")
    fig.savefig(path, dpi=DPI, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("Yazıldı:", path)


if __name__ == "__main__":
    main()
