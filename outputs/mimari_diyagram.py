"""
outputs/mimari_diyagram.py
==========================
Poster "Model Bileşenleri ve Kontrol Mimarisi" bölümü için şema figürü.

Yayın figürü düzeni: panel harfleri (A–D), ince siyah çizgi, sınırlı renk,
gerçek eksenli veri panelleri ve altta parametre tablosu. Dekoratif kutu,
gölge veya rozet kullanılmaz.

Panel A — Elektrot–akson geometrisi ve uyarım dalga formu
Panel B — Akson boyunca ekstrasellüler potansiyel profili
Panel C — Ağ mimarisi ve yolağa özgü kısa süreli plastisite
Panel D — Parametre tablosu

Veri panelleri şematik değildir; projenin kendi fonksiyonlarından üretilir
(`biphasic_waveform`, `point_source_potential`, TM kararlı-durum yinelemesi).
Sayısal değerler `config/defaults.py`'den okunur.

Kullanım:
    .venv/bin/python outputs/mimari_diyagram.py [cikti_dizini]
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
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
INK = "#000000"
GRAY = "#555555"
PALE = "#aaaaaa"
FILL = "#dddddd"

C_NAC = "#b8620f"
C_INS = "#0f7a5a"
C_CA3 = "#4f4a9c"

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["DejaVu Sans"],
    "font.size": 7.5,
    "axes.linewidth": 0.7,
    "xtick.major.width": 0.7,
    "ytick.major.width": 0.7,
    "xtick.major.size": 2.5,
    "ytick.major.size": 2.5,
    "mathtext.default": "regular",
})


def panel_letter(ax, letter, title, x=-0.02, y=1.06):
    ax.text(x, y, letter, transform=ax.transAxes, fontsize=11, weight="bold",
            ha="left", va="bottom")
    ax.text(x + 0.045, y, title, transform=ax.transAxes, fontsize=8.4,
            ha="left", va="bottom")


def thin_arrow(ax, p0, p1, color=INK, lw=0.8, ms=7, ls="-"):
    ax.add_patch(FancyArrowPatch(p0, p1, arrowstyle="-|>", mutation_scale=ms,
                                 linewidth=lw, color=color, linestyle=ls,
                                 shrinkA=0, shrinkB=0, zorder=6))


def axon_z_coords():
    """MRGAxon.section_coords() ile aynı z dizilimi (NEURON'suz)."""
    _, node_len, internode_len, _, _ = MRG_PARAMS[DEFAULT_FIBER_DIAM]
    zs, z = [], 0.0
    for _ in range(DEFAULT_N_NODES - 1):
        zs.append(z + node_len / 2); z += node_len
        zs.append(z + internode_len / 2); z += internode_len
    zs.append(z + node_len / 2)
    return np.asarray(zs)


def tm_train(U, tau_f_ms, tau_d_ms, freq_hz, n=6):
    """Ardışık spike'lardaki bağıl EPSC genlikleri (u·x), ilkine normalize."""
    period = 1000.0 / freq_hz
    u, x, out = U, 1.0, []
    for k in range(n):
        if k > 0:
            u *= np.exp(-period / tau_f_ms)
            x = 1.0 - (1.0 - x) * np.exp(-period / tau_d_ms)
        u = u + U * (1.0 - u)
        out.append(u * x)
        x -= u * x
    arr = np.asarray(out)
    return arr / arr[0]


def epsc_icon(ax, x, y, amps, w, h, color):
    """Ardışık EPSC genlikleri — yayın konvansiyonunda küçük simge."""
    ax.plot([x, x + w], [y, y], color=PALE, lw=0.5, zorder=4)
    for xi, a in zip(np.linspace(x + 0.6, x + w - 0.6, len(amps)), amps):
        ax.plot([xi, xi], [y, y + h * a / amps.max()], color=color, lw=1.1,
                solid_capstyle="butt", zorder=5)


def cloud(ax, cx, cy, rx, ry, n, color, seed):
    rng = np.random.default_rng(seed)
    ang = rng.uniform(0, 2 * np.pi, n)
    rad = np.sqrt(rng.uniform(0, 1, n))
    ax.scatter(cx + rx * rad * np.cos(ang), cy + ry * rad * np.sin(ang),
               s=2.6, facecolor=color, edgecolor="none", alpha=0.85, zorder=4)


# ---------------------------------------------------------------------------
# Panel A — geometri ve dalga formu
# ---------------------------------------------------------------------------

def panel_a(ax):
    panel_letter(ax, "A", "Elektrot–akson geometrisi ve uyarım")
    ax.set_xlim(0, 100); ax.set_ylim(0, 46); ax.axis("off")

    _, _, internode_l, n_lamellae, _ = MRG_PARAMS[DEFAULT_FIBER_DIAM]
    axon_y, x0, x1, n_seg, node_w = 19.0, 4.0, 54.0, 5, 1.8
    inter_w = (x1 - x0 - n_seg * node_w) / (n_seg - 1)

    cursor = x0
    for i in range(n_seg):
        ax.add_patch(Rectangle((cursor, axon_y - 1.3), node_w, 2.6,
                               facecolor=INK, edgecolor="none", zorder=5))
        cursor += node_w
        if i < n_seg - 1:
            ax.add_patch(Rectangle((cursor, axon_y - 2.4), inter_w, 4.8,
                                   facecolor=FILL, edgecolor=INK, lw=0.7,
                                   zorder=4))
            cursor += inter_w

    ex = x0 + (x1 - x0) * 0.28
    ey = 36.0
    ax.add_patch(Rectangle((ex - 0.8, ey), 1.6, 6.0, facecolor=INK,
                           edgecolor="none", zorder=6))
    ax.text(ex, ey + 6.8, "elektrot", fontsize=7.2, ha="center", va="bottom")
    ax.plot([ex, ex], [ey, axon_y + 2.6], color=GRAY, lw=0.6, ls=(0, (3, 2)),
            zorder=3)
    ax.annotate("", xy=(ex, axon_y + 2.6), xytext=(ex, ey),
                arrowprops=dict(arrowstyle="<->", lw=0.6, color=GRAY))
    ax.text(ex + 1.5, (ey + axon_y) / 2, f"r = {DEFAULT_ELEC_DIST:.0f} µm",
            fontsize=7.0, color=GRAY, ha="left", va="center")
    ax.text(28.0, 3.0, "$V_e(z) = \\rho I\\,/\\,4\\pi r(z)$",
            fontsize=8.2, ha="center", va="bottom")

    ax.plot([x0 + node_w / 2] * 2, [axon_y - 1.6, axon_y - 6.0], color=GRAY, lw=0.6)
    ax.text(x0 + node_w / 2, axon_y - 6.8, "Ranvier düğümü\n(axnode)", fontsize=7.0,
            ha="left", va="top", color=GRAY, linespacing=1.4)
    mid = x0 + node_w + inter_w / 2
    ax.plot([mid] * 2, [axon_y + 2.6, axon_y + 7.0], color=GRAY, lw=0.6)
    ax.text(mid, axon_y + 7.6,
            f"internode\n{internode_l:.0f} µm, {n_lamellae} lamel",
            fontsize=7.0, ha="center", va="bottom", color=GRAY,
            linespacing=1.4)

    ax.text(x1 + 2.5, axon_y - 5.5, "distal düğüm:\nspike kaydı",
            fontsize=7.0, ha="left", va="top", color=GRAY, linespacing=1.4)
    thin_arrow(ax, (x1 + 0.4, axon_y), (x1 + 1.6, axon_y), GRAY, lw=0.7, ms=6)

    # Gercek dalga formlari (kucuk inset)
    inset = ax.inset_axes([0.63, 0.56, 0.35, 0.40])
    for kind, off, lab, col in (("dc", 2.4, "DC", GRAY),
                                ("rectangular", -2.4, "bifazik", INK)):
        t, i_vec = biphasic_waveform(1000.0, 1.0, 3.0, dt=0.002,
                                     pulse_width_ms=DEFAULT_PULSE_WIDTH,
                                     waveform=kind)
        inset.plot(t, i_vec + off, color=col, lw=0.9)
        inset.text(3.05, off, lab, fontsize=6.8, color=col, va="center",
                   ha="left")
    inset.set_xlim(0, 3.9); inset.set_ylim(-4.4, 4.6)
    inset.set_xlabel("zaman (ms)", fontsize=6.8, labelpad=1.5)
    inset.set_yticks([])
    inset.tick_params(labelsize=6.4)
    for side in ("top", "right", "left"):
        inset.spines[side].set_visible(False)


# ---------------------------------------------------------------------------
# Panel B — alan profili (gercek)
# ---------------------------------------------------------------------------

def panel_b(ax):
    panel_letter(ax, "B", "Akson boyunca ekstrasellüler potansiyel")
    zs = axon_z_coords()
    elec = (DEFAULT_ELEC_DIST, 0.0, DEFAULT_ELEC_Z)
    z_fine = np.linspace(zs.min(), zs.max(), 600)
    ve = np.array([point_source_potential(0.0, 0.0, z, elec, 1000.0)
                   for z in z_fine])
    ve_nodes = np.array([point_source_potential(0.0, 0.0, z, elec, 1000.0)
                         for z in zs[::2]])

    ax.plot(z_fine / 1000.0, ve, color=INK, lw=1.0, zorder=3)
    ax.plot(zs[::2] / 1000.0, ve_nodes, "o", ms=2.6, mfc="white", mec=INK,
            mew=0.7, zorder=4, label="Ranvier düğümleri")
    ax.axvline(DEFAULT_ELEC_Z / 1000.0, color=GRAY, lw=0.6, ls=(0, (3, 2)),
               zorder=2)
    ax.text(DEFAULT_ELEC_Z / 1000.0 + 0.12, ve.max() * 0.95, "elektrot",
            fontsize=6.8, color=GRAY, ha="left", va="top")
    ax.set_xlabel("akson ekseni  z (mm)", labelpad=2)
    ax.set_ylabel("$V_e$ (mV)  ·  I = 1 mA", labelpad=2)
    ax.legend(fontsize=6.6, frameon=False, loc="upper right",
              handletextpad=0.4, borderpad=0.2)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)


# ---------------------------------------------------------------------------
# Panel C — ag mimarisi
# ---------------------------------------------------------------------------

def panel_c(ax):
    panel_letter(ax, "C", "Ağ mimarisi ve yolağa özgü kısa süreli plastisite")
    ax.set_xlim(0, 100); ax.set_ylim(0, 46); ax.axis("off")

    rng = np.random.default_rng(5)
    base = np.array([0.12, 0.34, 0.56, 0.78])

    # Tek akson -> demet
    ax.text(3, 40.5, "tek akson", fontsize=7.2, color=GRAY, ha="left")
    for t in base:
        xi = 3 + 13 * t
        ax.plot([xi, xi], [35.0, 38.0], color=INK, lw=0.9, zorder=5)
    ax.plot([3, 16], [34.0, 34.0], color=PALE, lw=0.5)

    ax.text(22, 40.5, f"{DEFAULT_N_FIBERS} lifli demet", fontsize=7.2,
            color=GRAY, ha="left")
    for k in range(6):
        y = 38.0 - k * 1.5
        for t in np.clip(base + rng.normal(0, 0.013, base.size), 0, 1):
            xi = 22 + 13 * t
            ax.plot([xi, xi], [y, y + 1.0], color=GRAY, lw=0.6, zorder=5)
    thin_arrow(ax, (17.2, 36.0), (20.8, 36.0))

    # NTS
    cloud(ax, 48, 34.5, 5.2, 4.6, int(NTS_PARAMS["n_neurons"]), GRAY, 3)
    ax.text(48, 41.0, "NTS", fontsize=8.6, weight="bold", ha="center")
    ax.text(48, 28.6, f"{int(NTS_PARAMS['n_neurons'])} LIF", fontsize=6.9,
            color=GRAY, ha="center", va="top")
    thin_arrow(ax, (36.2, 36.0), (42.0, 35.2))
    epsc_icon(ax, 35.6, 29.2, tm_train(NTS_PARAMS["U"], NTS_PARAMS["tau_f_ms"],
                                       NTS_PARAMS["tau_d_ms"], 20.0),
              w=5.4, h=3.0, color=INK)
    ax.text(38.3, 27.6, "afferent→NTS", fontsize=6.7, color=GRAY,
            ha="center", va="top")

    # Ucu yolak
    rows = [(38.0, C_NAC, "NAc", NAC_PATHWAY_PARAMS, "fasilitasyon", 11),
            (24.0, C_INS, "İnsula", INSULA_PATHWAY_PARAMS, "depresyon", 12),
            (10.0, C_CA3, "CA3", CA3_PATHWAY_PARAMS, "fasilitasyon", 13)]
    for cy, col, name, prm, kind, seed in rows:
        thin_arrow(ax, (54.0, 34.0), (62.0, cy), col)
        epsc_icon(ax, 62.8, cy - 1.4, tm_train(prm["U"], prm["tau_f_ms"],
                                               prm["tau_d_ms"], 20.0),
                  w=5.6, h=3.2, color=col)
        thin_arrow(ax, (69.2, cy), (73.5, cy), col)
        cloud(ax, 80.0, cy, 5.0, 3.4, int(prm["n_neurons"]), col, seed)
        ax.text(87.0, cy + 1.4, name, fontsize=8.4, weight="bold", color=col,
                ha="left", va="center")
        ax.text(87.0, cy - 1.4, f"{kind}, U = {prm['U']}", fontsize=6.9,
                color=GRAY, ha="left", va="center")

    ax.add_patch(FancyArrowPatch((76.5, 6.4), (83.5, 6.4),
                                 connectionstyle="arc3,rad=-0.85",
                                 arrowstyle="-|>", mutation_scale=7,
                                 lw=0.8, color=C_CA3, zorder=6))
    ax.text(80.0, 2.6, f"rekürrent, p = {CA3_PATHWAY_PARAMS['recurrent_p']}",
            fontsize=6.8, color=C_CA3, ha="center", va="bottom")
    ax.text(65.6, 43.0, "ardışık EPSC genlikleri (20 Hz)", fontsize=6.9,
            color=GRAY, ha="center", va="top")
    ax.text(3, 21.0,
            f"jitter 0.4 ms · refrakter {AXON_REFRACTORY_MS:.0f} ms\n"
            f"Brian2 dt {DEFAULT_BRIAN_DT_MS} ms",
            fontsize=6.9, color=GRAY, ha="left", va="top", linespacing=1.5)


# ---------------------------------------------------------------------------
# Panel D — parametre tablosu
# ---------------------------------------------------------------------------

def panel_d(ax):
    panel_letter(ax, "D", "Sinaptik parametreler")
    ax.set_xlim(0, 100); ax.set_ylim(0, 26); ax.axis("off")

    cols = [2, 20, 32, 46, 60, 70, 80]
    head = ["yolak", "U", "$\\tau_f$ (ms)", "$\\tau_d$ (ms)", "w (nS)", "n",
            "kaynak"]
    rows = [("afferent→NTS", NTS_PARAMS, "Miles 1986; Chen 1999"),
            ("NTS→NAc", NAC_PATHWAY_PARAMS, "el ayarı (TK-005)"),
            ("NTS→İnsula", INSULA_PATHWAY_PARAMS, "el ayarı (TK-005)"),
            ("NTS→CA3", CA3_PATHWAY_PARAMS, "el ayarı (TK-005)")]

    ax.plot([1, 99], [23.5, 23.5], color=INK, lw=1.0)
    for x, h in zip(cols, head):
        ax.text(x, 21.0, h, fontsize=7.2, weight="bold", ha="left", va="center")
    ax.plot([1, 99], [19.0, 19.0], color=INK, lw=0.6)

    for i, (name, prm, src) in enumerate(rows):
        y = 16.2 - i * 3.1
        vals = [name, f"{prm['U']}", f"{prm['tau_f_ms']:.0f}",
                f"{prm['tau_d_ms']:.0f}", f"{prm['w_nS']:.0f}",
                f"{int(prm['n_neurons'])}", src]
        for x, v in zip(cols, vals):
            ax.text(x, y, v, fontsize=7.1, ha="left", va="center")
    ax.plot([1, 99], [4.4, 4.4], color=INK, lw=1.0)

    ax.text(1, 0.6,
            f"Akson: MRG {DEFAULT_FIBER_DIAM} µm, {DEFAULT_N_NODES} düğüm, "
            f"dt {DEFAULT_DT} ms  ·  uyarım: {DEFAULT_PULSE_WIDTH} ms puls, "
            f"1–3 mA, 1 Hz–10 kHz  ·  {DEFAULT_N_REPEATS} tekrar (ort. ± SD)",
            fontsize=6.8, color=GRAY, ha="left", va="bottom")


def main() -> None:
    out_dir = sys.argv[1] if len(sys.argv) > 1 else "outputs/sekiller"
    os.makedirs(out_dir, exist_ok=True)

    fig = plt.figure(figsize=(7.9, 8.9))
    gs = GridSpec(4, 1, figure=fig, height_ratios=[0.88, 0.85, 1.28, 0.66],
                  hspace=0.62, left=0.09, right=0.97, top=0.955, bottom=0.045)

    panel_a(fig.add_subplot(gs[0]))
    panel_b(fig.add_subplot(gs[1]))
    panel_c(fig.add_subplot(gs[2]))
    panel_d(fig.add_subplot(gs[3]))

    path = os.path.join(out_dir, "sekil0_mimari.png")
    fig.savefig(path, dpi=DPI, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("Yazıldı:", path)


if __name__ == "__main__":
    main()
