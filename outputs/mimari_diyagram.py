"""
outputs/mimari_diyagram.py
==========================
Poster "Model Bileşenleri ve Kontrol Mimarisi" bölümü için şema figürü.

Yayın figürü düzeni: panel harfleri (A–G), ince siyah çizgi, sınırlı renk,
gerçek eksenli veri panelleri, booktabs tarzı tablolar. Dekoratif kutu,
gölge, rozet veya kutu-arası ok zinciri kullanılmaz.

    A  Elektrot–akson geometrisi ve uyarım dalga formları
    B  Akson boyunca ekstrasellüler potansiyel profili
    C  Lif demeti — jitter ve refrakter filtre
    D  Ağ mimarisi ve yolağa özgü kısa süreli plastisite
    E  NTS kalibrasyonu (deneysel veriyle karşılaştırma)
    F  Bölge frekans yanıtı (matris sonuçları)
    G  Parametre tablosu ve doğrulama özeti

Veri panelleri şematik değildir; projenin kendi fonksiyonlarından ve
outputs/matris.csv sonuçlarından üretilir. Sayısal değerler
config/defaults.py'den okunur.

Kullanım:
    .venv/bin/python outputs/mimari_diyagram.py [matris.csv] [cikti_dizini]
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.gridspec import GridSpec
from matplotlib.patches import FancyArrowPatch, Rectangle

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
)
from src.stim.extracellular_field import biphasic_waveform, point_source_potential

DPI = 300
INK, GRAY, PALE, FILL = "#000000", "#555555", "#aaaaaa", "#dddddd"
C_NTS, C_NAC, C_INS, C_CA3 = "#666666", "#b8620f", "#0f7a5a", "#4f4a9c"

# Deneysel referans noktalari
MILES_F = np.array([5.0, 10.0, 20.0])          # Miles 1986, J Neurophysiol 55:1076
MILES_R = np.array([0.65, 0.40, 0.20])
BEAUMONT = (20.0, 0.25)                        # Beaumont 2017, Am J Physiol 313:H354
CV_MODEL = "30–54"                             # bu çalışma (ölçüldü)
CV_REF = "30.5–62.8"                           # Musselman 2023, insan vagus Aα

plt.rcParams.update({
    "font.family": "sans-serif", "font.sans-serif": ["DejaVu Sans"],
    "font.size": 7.2, "axes.linewidth": 0.7,
    "xtick.major.width": 0.7, "ytick.major.width": 0.7,
    "xtick.major.size": 2.4, "ytick.major.size": 2.4,
    "mathtext.default": "regular",
})


def panel_letter(ax, letter, title, y=1.07):
    ax.text(-0.02, y, letter, transform=ax.transAxes, fontsize=10.5,
            weight="bold", ha="left", va="bottom")
    ax.text(0.045, y, title, transform=ax.transAxes, fontsize=8.0,
            ha="left", va="bottom")


def despine(ax):
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)


def thin_arrow(ax, p0, p1, color=INK, lw=0.8, ms=7):
    ax.add_patch(FancyArrowPatch(p0, p1, arrowstyle="-|>", mutation_scale=ms,
                                 linewidth=lw, color=color, shrinkA=0,
                                 shrinkB=0, zorder=6))


def axon_z_coords():
    _, node_len, internode_len, _, _ = MRG_PARAMS[DEFAULT_FIBER_DIAM]
    zs, z = [], 0.0
    for _ in range(DEFAULT_N_NODES - 1):
        zs.append(z + node_len / 2); z += node_len
        zs.append(z + internode_len / 2); z += internode_len
    zs.append(z + node_len / 2)
    return np.asarray(zs)


def tm_steady(U, tau_f, tau_d, f):
    T = 1000.0 / f
    u = U / (1.0 - (1.0 - U) * np.exp(-T / tau_f))
    x = (1.0 - np.exp(-T / tau_d)) / (1.0 - (1.0 - u) * np.exp(-T / tau_d))
    return u * x


def tm_train(U, tau_f, tau_d, f, n=6):
    T, u, x, out = 1000.0 / f, U, 1.0, []
    for k in range(n):
        if k:
            u *= np.exp(-T / tau_f)
            x = 1.0 - (1.0 - x) * np.exp(-T / tau_d)
        u = u + U * (1.0 - u)
        out.append(u * x); x -= u * x
    arr = np.asarray(out)
    return arr / arr[0]


def epsc_icon(ax, x, y, amps, w, h, color):
    ax.plot([x, x + w], [y, y], color=PALE, lw=0.5, zorder=4)
    for xi, a in zip(np.linspace(x + 0.6, x + w - 0.6, len(amps)), amps):
        ax.plot([xi, xi], [y, y + h * a / amps.max()], color=color, lw=1.1,
                solid_capstyle="butt", zorder=5)


def cloud(ax, cx, cy, rx, ry, n, color, seed):
    rng = np.random.default_rng(seed)
    ang, rad = rng.uniform(0, 2 * np.pi, n), np.sqrt(rng.uniform(0, 1, n))
    ax.scatter(cx + rx * rad * np.cos(ang), cy + ry * rad * np.sin(ang),
               s=2.4, facecolor=color, edgecolor="none", alpha=0.85, zorder=4)


# ------------------------------------------------------------------ A
def panel_a(ax):
    panel_letter(ax, "A", "Elektrot–akson geometrisi ve uyarım")
    ax.set_xlim(0, 100); ax.set_ylim(0, 44); ax.axis("off")
    _, _, internode_l, n_lamellae, _ = MRG_PARAMS[DEFAULT_FIBER_DIAM]

    axon_y, x0, x1, n_seg, node_w = 18.0, 4.0, 52.0, 5, 1.8
    inter_w = (x1 - x0 - n_seg * node_w) / (n_seg - 1)
    cursor = x0
    for i in range(n_seg):
        ax.add_patch(Rectangle((cursor, axon_y - 1.3), node_w, 2.6,
                               facecolor=INK, edgecolor="none", zorder=5))
        cursor += node_w
        if i < n_seg - 1:
            ax.add_patch(Rectangle((cursor, axon_y - 2.4), inter_w, 4.8,
                                   facecolor=FILL, edgecolor=INK, lw=0.7, zorder=4))
            cursor += inter_w

    ex, ey = x0 + (x1 - x0) * 0.30, 34.0
    ax.add_patch(Rectangle((ex - 0.8, ey), 1.6, 5.5, facecolor=INK,
                           edgecolor="none", zorder=6))
    ax.text(ex, ey + 6.3, "elektrot", fontsize=7.0, ha="center", va="bottom")
    ax.annotate("", xy=(ex, axon_y + 2.6), xytext=(ex, ey),
                arrowprops=dict(arrowstyle="<->", lw=0.6, color=GRAY))
    ax.text(ex + 1.4, (ey + axon_y) / 2, f"r = {DEFAULT_ELEC_DIST:.0f} µm",
            fontsize=6.9, color=GRAY, ha="left", va="center")

    ax.plot([x0 + node_w / 2] * 2, [axon_y - 1.6, axon_y - 5.5], color=GRAY, lw=0.6)
    ax.text(x0 + node_w / 2, axon_y - 6.2, "Ranvier düğümü (axnode)",
            fontsize=6.9, ha="left", va="top", color=GRAY)
    mid = x0 + node_w + inter_w / 2
    ax.plot([mid] * 2, [axon_y + 2.6, axon_y + 6.5], color=GRAY, lw=0.6)
    ax.text(mid, axon_y + 7.1, f"internode\n{internode_l:.0f} µm, {n_lamellae} lamel",
            fontsize=6.9, ha="center", va="bottom", color=GRAY, linespacing=1.4)
    thin_arrow(ax, (x1 + 0.4, axon_y), (x1 + 1.8, axon_y), GRAY, lw=0.7, ms=6)
    ax.text(x1 - 14.0, axon_y - 5.2, "distal düğüm: spike kaydı",
            fontsize=6.9, ha="left", va="top", color=GRAY)
    ax.text(4.0, 1.0,
            "$V_e(z) = \\rho I\\,/\\,4\\pi r(z)$   ·   ρ = 300 Ω·cm   ·   "
            "puls " + f"{DEFAULT_PULSE_WIDTH} ms",
            fontsize=7.4, ha="left", va="bottom")

    ins = ax.inset_axes([0.66, 0.50, 0.33, 0.44])
    for kind, off, lab, col in (("dc", 2.4, "DC", GRAY),
                                ("rectangular", -2.4, "bifazik", INK)):
        t, iv = biphasic_waveform(1000.0, 1.0, 3.0, dt=0.002,
                                  pulse_width_ms=DEFAULT_PULSE_WIDTH, waveform=kind)
        ins.plot(t, iv + off, color=col, lw=0.9)
        ins.text(3.06, off, lab, fontsize=6.5, color=col, va="center", ha="left")
    ins.set_xlim(0, 3.9); ins.set_ylim(-4.4, 4.6)
    ins.set_xlabel("zaman (ms)", fontsize=6.5, labelpad=1.2)
    ins.set_yticks([]); ins.tick_params(labelsize=6.2)
    for side in ("top", "right", "left"):
        ins.spines[side].set_visible(False)


# ------------------------------------------------------------------ B
def panel_b(ax):
    panel_letter(ax, "B", "Ekstrasellüler potansiyel profili")
    zs = axon_z_coords()
    elec = (DEFAULT_ELEC_DIST, 0.0, DEFAULT_ELEC_Z)
    zf = np.linspace(zs.min(), zs.max(), 500)
    ax.plot(zf / 1000.0, [point_source_potential(0, 0, z, elec, 1000.0) for z in zf],
            color=INK, lw=1.0, zorder=3)
    ax.plot(zs[::2] / 1000.0,
            [point_source_potential(0, 0, z, elec, 1000.0) for z in zs[::2]],
            "o", ms=2.4, mfc="white", mec=INK, mew=0.7, zorder=4,
            label="Ranvier düğümleri")
    ax.axvline(DEFAULT_ELEC_Z / 1000.0, color=GRAY, lw=0.6, ls=(0, (3, 2)))
    ax.set_xlabel("akson ekseni  z (mm)", labelpad=2)
    ax.set_ylabel("$V_e$ (mV),  I = 1 mA", labelpad=2)
    ax.legend(fontsize=6.4, frameon=False, loc="upper right", handletextpad=0.4)
    despine(ax)


# ------------------------------------------------------------------ C
def panel_c(ax):
    panel_letter(ax, "C", "Lif demeti")
    rng = np.random.default_rng(7)
    base = np.array([0.10, 0.32, 0.54, 0.76])
    ax.plot(base, [DEFAULT_N_FIBERS + 1.5] * base.size, "|", color=INK,
            ms=7, mew=1.1)
    ax.text(-0.02, DEFAULT_N_FIBERS + 2.6, "tek akson", fontsize=6.8,
            color=INK, ha="left", va="bottom")
    for f in range(DEFAULT_N_FIBERS):
        jit = np.clip(base + rng.normal(0, 0.012, base.size), 0, 1)
        ax.plot(jit, [f] * jit.size, "|", color=GRAY, ms=4.5, mew=0.7)
    ax.set_ylim(-1.5, DEFAULT_N_FIBERS + 4.5)
    ax.set_xlim(0, 0.92)
    ax.set_xlabel("normalize zaman", labelpad=2)
    ax.set_ylabel("lif no", labelpad=2)
    ax.set_yticks([0, 10, 19]); ax.set_yticklabels(["1", "11", "20"])
    ax.text(1.0, 1.07,
            f"jitter 0.4 ms · refrakter {AXON_REFRACTORY_MS:.0f} ms · "
            f"dt {DEFAULT_BRIAN_DT_MS} ms",
            transform=ax.transAxes, fontsize=6.4, color=GRAY,
            ha="right", va="bottom")
    despine(ax)


# ------------------------------------------------------------------ D
def panel_d(ax):
    panel_letter(ax, "D", "Ağ mimarisi ve yolağa özgü kısa süreli plastisite")
    ax.set_xlim(0, 100); ax.set_ylim(0, 42); ax.axis("off")

    cloud(ax, 14, 21, 5.0, 5.6, int(NTS_PARAMS["n_neurons"]), C_NTS, 3)
    ax.text(14, 29.0, "NTS", fontsize=8.2, weight="bold", ha="center")
    ax.text(14, 13.6, f"{int(NTS_PARAMS['n_neurons'])} LIF", fontsize=6.7,
            color=GRAY, ha="center", va="top")
    thin_arrow(ax, (2.0, 21.0), (8.0, 21.0), INK)
    ax.text(2.0, 23.0, "afferent\ndemet", fontsize=6.7, color=GRAY,
            ha="left", va="bottom", linespacing=1.4)
    epsc_icon(ax, 1.5, 15.0, tm_train(NTS_PARAMS["U"], NTS_PARAMS["tau_f_ms"],
                                      NTS_PARAMS["tau_d_ms"], 20.0),
              w=5.0, h=2.8, color=INK)

    rows = [(35.0, C_NAC, "NAc", NAC_PATHWAY_PARAMS, "fasilitasyon", 11),
            (21.0, C_INS, "İnsula", INSULA_PATHWAY_PARAMS, "depresyon", 12),
            (7.0, C_CA3, "CA3", CA3_PATHWAY_PARAMS, "fasilitasyon", 13)]
    for cy, col, name, prm, kind, seed in rows:
        thin_arrow(ax, (20.0, 21.0), (30.0, cy), col)
        epsc_icon(ax, 31.0, cy - 1.4, tm_train(prm["U"], prm["tau_f_ms"],
                                               prm["tau_d_ms"], 20.0),
                  w=5.4, h=3.0, color=col)
        thin_arrow(ax, (37.2, cy), (41.5, cy), col)
        cloud(ax, 48.0, cy, 4.8, 3.2, int(prm["n_neurons"]), col, seed)
        ax.text(55.0, cy + 1.3, name, fontsize=8.0, weight="bold", color=col,
                ha="left", va="center")
        ax.text(55.0, cy - 1.4,
                f"{kind} · U = {prm['U']} · $\\tau_f$ = {prm['tau_f_ms']:.0f} ms",
                fontsize=6.7, color=GRAY, ha="left", va="center")
    ax.add_patch(FancyArrowPatch((44.5, 3.4), (51.5, 3.4),
                                 connectionstyle="arc3,rad=-0.85",
                                 arrowstyle="-|>", mutation_scale=7, lw=0.8,
                                 color=C_CA3, zorder=6))
    ax.text(48.0, 0.2, f"rekürrent, p = {CA3_PATHWAY_PARAMS['recurrent_p']}",
            fontsize=6.5, color=C_CA3, ha="center", va="bottom")
    ax.text(33.7, 40.5, "ardışık EPSC genlikleri (20 Hz)", fontsize=6.7,
            color=GRAY, ha="center", va="top")


# ------------------------------------------------------------------ E
def panel_e(ax):
    panel_letter(ax, "E", "NTS kalibrasyonu")
    grid = np.logspace(0, 2, 120)
    p = NTS_PARAMS
    ax.plot(grid, [tm_steady(p["U"], p["tau_f_ms"], p["tau_d_ms"], f) / p["U"]
                   for f in grid], color=INK, lw=1.1, label="model")
    ax.plot(MILES_F, MILES_R, "s", ms=4.5, mfc="white", mec=INK, mew=0.9,
            label="Miles 1986")
    ax.plot(*BEAUMONT, "^", ms=5.0, color=INK, label="Beaumont 2017")
    ax.set_xscale("log")
    ax.set_xlabel("uyarım frekansı (Hz)", labelpad=2)
    ax.set_ylabel("kararlı-durum PSP / ilk PSP", labelpad=2)
    ax.set_ylim(0, 1.05)
    ax.legend(fontsize=6.3, frameon=False, loc="upper right", handletextpad=0.5)
    despine(ax)


# ------------------------------------------------------------------ F
def panel_f(ax, df):
    panel_letter(ax, "F", "Bölge frekans yanıtı (3 mA, pulse)")
    if df is None:
        ax.text(0.5, 0.5, "matris.csv bulunamadı", transform=ax.transAxes,
                fontsize=7, color=GRAY, ha="center", va="center")
        ax.axis("off"); return
    sub = df[(df.waveform == "rectangular") & (np.isclose(df.amp_mA, 3.0))] \
        .sort_values("freq_hz")
    for reg, col, lab in (("NTS", C_NTS, "NTS"), ("NAc", C_NAC, "NAc"),
                          ("Insula", C_INS, "İnsula"), ("CA3", C_CA3, "CA3")):
        ax.errorbar(sub.freq_hz, sub[reg], yerr=sub[f"{reg}_sd"], marker="o",
                    ms=3.2, lw=1.0, capsize=1.8, elinewidth=0.7, color=col,
                    label=lab)
    ax.set_xscale("log")
    ax.set_xlabel("stimülasyon frekansı (Hz)", labelpad=2)
    ax.set_ylabel("ateşleme hızı (Hz/nöron)", labelpad=2)
    ax.legend(fontsize=6.3, frameon=False, loc="upper left", ncol=2,
              handletextpad=0.5, columnspacing=1.0)
    despine(ax)


# ------------------------------------------------------------------ G
def panel_g(ax):
    panel_letter(ax, "G", "Parametreler ve doğrulama")
    ax.set_xlim(0, 100); ax.set_ylim(0, 30); ax.axis("off")
    p = NTS_PARAMS
    ratios = [tm_steady(p["U"], p["tau_f_ms"], p["tau_d_ms"], f) / p["U"]
              for f in MILES_F]

    # Sol tablo — sinaptik parametreler
    cols = [0, 12, 20, 30, 40]
    ax.plot([0, 47], [27, 27], color=INK, lw=1.0)
    for x, h in zip(cols, ["yolak", "U", "$\\tau_f$", "$\\tau_d$", "w (nS)"]):
        ax.text(x, 24.6, h, fontsize=7.0, weight="bold", ha="left", va="center")
    ax.plot([0, 47], [22.6, 22.6], color=INK, lw=0.6)
    for i, (name, prm) in enumerate([("afferent→NTS", NTS_PARAMS),
                                     ("NTS→NAc", NAC_PATHWAY_PARAMS),
                                     ("NTS→İnsula", INSULA_PATHWAY_PARAMS),
                                     ("NTS→CA3", CA3_PATHWAY_PARAMS)]):
        y = 19.8 - i * 3.4
        for x, v in zip(cols, [name, f"{prm['U']}", f"{prm['tau_f_ms']:.0f}",
                               f"{prm['tau_d_ms']:.0f}", f"{prm['w_nS']:.0f}"]):
            ax.text(x, y, v, fontsize=6.9, ha="left", va="center")
    ax.plot([0, 47], [4.8, 4.8], color=INK, lw=1.0)
    ax.text(0, 2.6, "τ ms cinsinden · n = 30 (NTS), 100 (bölgeler)",
            fontsize=6.4, color=GRAY, ha="left", va="center")

    # Sag tablo — dogrulama
    cx = [53, 75, 88]
    ax.plot([53, 100], [27, 27], color=INK, lw=1.0)
    for x, h in zip(cx, ["ölçüt", "model", "literatür"]):
        ax.text(x, 24.6, h, fontsize=7.0, weight="bold", ha="left", va="center")
    ax.plot([53, 100], [22.6, 22.6], color=INK, lw=0.6)
    checks = [
        ("TM analitik ↔ simülasyon", "< %0.2", "TM 1997"),
        ("NTS PSP  5/10/20 Hz",
         "/".join(f"{r:.2f}" for r in ratios), "0.65/0.40/0.20"),
        ("aktarım @20 Hz", f"{ratios[-1]:.2f}", "~0.25"),
        ("ileti hızı (m/s)", CV_MODEL, CV_REF),
        ("aktivasyon eşiği", "~1–2 mA", "0.25–3.5 mA"),
    ]
    for i, (a, b, c) in enumerate(checks):
        y = 20.4 - i * 3.2
        for x, v in zip(cx, [a, b, c]):
            ax.text(x, y, v, fontsize=6.7, ha="left", va="center")
    ax.plot([53, 100], [4.8, 4.8], color=INK, lw=1.0)
    ax.text(53, 2.6,
            "Miles 1986 · Beaumont 2017 · Musselman 2023 · Krahl & Clark 2012",
            fontsize=6.4, color=GRAY, ha="left", va="center")


def main() -> None:
    csv_path = sys.argv[1] if len(sys.argv) > 1 else "outputs/matris.csv"
    out_dir = sys.argv[2] if len(sys.argv) > 2 else "outputs/sekiller"
    os.makedirs(out_dir, exist_ok=True)
    df = pd.read_csv(csv_path) if os.path.exists(csv_path) else None

    fig = plt.figure(figsize=(8.3, 11.4))
    gs = GridSpec(5, 2, figure=fig, height_ratios=[0.92, 0.80, 1.10, 0.80, 0.72],
                  hspace=0.78, wspace=0.30,
                  left=0.085, right=0.975, top=0.932, bottom=0.035)

    panel_a(fig.add_subplot(gs[0, :]))
    panel_b(fig.add_subplot(gs[1, 0]))
    panel_c(fig.add_subplot(gs[1, 1]))
    panel_d(fig.add_subplot(gs[2, :]))
    panel_e(fig.add_subplot(gs[3, 0]))
    panel_f(fig.add_subplot(gs[3, 1]), df)
    panel_g(fig.add_subplot(gs[4, :]))

    fig.text(0.085, 0.984,
             "Kapsam: 2 dalga şekli × 3 genlik (1–3 mA) × 5 frekans "
             f"(1 Hz–10 kHz) = 30 koşul × {DEFAULT_N_REPEATS} tekrar   ·   "
             f"MRG {DEFAULT_FIBER_DIAM} µm, {DEFAULT_N_NODES} düğüm, "
             f"dt {DEFAULT_DT} ms",
             fontsize=7.0, color=GRAY, ha="left", va="top")

    path = os.path.join(out_dir, "sekil0_mimari.png")
    fig.savefig(path, dpi=DPI, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("Yazıldı:", path)


if __name__ == "__main__":
    main()
