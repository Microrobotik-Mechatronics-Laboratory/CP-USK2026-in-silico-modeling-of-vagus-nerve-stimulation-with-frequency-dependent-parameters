"""
outputs/mimari_pano.py
==========================
Bildirinin "Amaç ve Kapsam" bölümü için çalışmanın genel mimari diyagramını üretir.

Diyagram, projenin uçtan uca akışını tek şekilde gösterir:

    Uyarım alanı → Seviye 1 (NEURON) → Köprü → Seviye 2 (NTS) → Seviye 3 (bölgeler)
    + kapsam (parametre matrisi), çıktı ölçütleri ve literatür doğrulaması

Kutucukların içindeki mini grafikler şematik değildir; projenin kendi
fonksiyonlarından ve outputs/matris.csv sonuçlarından üretilir:
    - dalga formu      : src.stim.extracellular_field.biphasic_waveform()
    - alan profili     : src.stim.extracellular_field.point_source_potential()
    - lif demeti       : src.network.bridge içindeki jitter + refrakter mantığı
    - NTS kalibrasyonu : config.defaults.NTS_PARAMS ile TM analitik kararlı durumu
    - bölge yanıtları  : outputs/matris.csv (rectangular, 3 mA)

Kullanım:
    .venv/bin/python outputs/mimari_pano.py [matris.csv] [cikti_dizini]
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Circle, FancyArrowPatch, FancyBboxPatch, Rectangle

from config.defaults import (
    AXON_REFRACTORY_MS,
    CA3_PATHWAY_PARAMS,
    ELECTRODE_POS,
    MRG_PARAMS,
    NTS_PARAMS,
    REGION_COLORS,
)
from src.stim.extracellular_field import biphasic_waveform, point_source_potential

DPI = 300
FIG_W, FIG_H = 16.0, 9.0

INK       = "#0F172A"   # ana metin
MUTED     = "#475569"   # ikincil metin
LINE      = "#CBD5E1"   # ince çizgi
CANVAS    = "#FFFFFF"
STRIP_BG  = "#F1F5F9"

# Aşama renkleri (accent, açık ton)
AMBER  = ("#B45309", "#FEF3C7")
RED    = ("#B91C1C", "#FEE2E2")
SLATE  = ("#334155", "#E2E8F0")
TEAL   = ("#0F766E", "#CCFBF1")
VIOLET = ("#6D28D9", "#EDE9FE")
GREEN  = ("#047857", "#ECFDF5")

REGIONS = ["NTS", "NAc", "Insula", "CA3"]
REGION_LABEL = {"NTS": "NTS", "NAc": "NAc", "Insula": "İnsula", "CA3": "CA3"}


# ---------------------------------------------------------------------------
# Çizim yardımcıları — tüm koordinatlar inç cinsindendir (1 birim = 1 inç)
# ---------------------------------------------------------------------------

def rounded(ax, x, y, w, h, face, edge=None, lw=1.2, r=0.10, z=2, alpha=1.0):
    """Yuvarlatılmış köşeli kutu çizer ve patch'i döndürür."""
    box = FancyBboxPatch(
        (x, y), w, h,
        boxstyle=f"round,pad=0,rounding_size={r}",
        facecolor=face, edgecolor=edge or face,
        linewidth=lw, zorder=z, alpha=alpha,
    )
    ax.add_patch(box)
    return box


def shadow(ax, x, y, w, h, r=0.10):
    """Kutuların altına yumuşak gölge koyar (derinlik hissi)."""
    for i, (dx, dy, a) in enumerate([(0.045, -0.045, 0.10), (0.025, -0.025, 0.08)]):
        rounded(ax, x + dx, y + dy, w, h, "#0F172A", lw=0, r=r, z=1 + i * 0.1, alpha=a)


def inset(fig, x, y, w, h):
    """İnç koordinatlarından figür-göreli mini eksen açar."""
    return fig.add_axes([x / FIG_W, y / FIG_H, w / FIG_W, h / FIG_H], zorder=5)


def style_mini(ax, accent):
    """Mini grafikler için ortak sade stil."""
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color("#94A3B8")
        ax.spines[side].set_linewidth(0.8)
    ax.tick_params(labelsize=6.0, colors=MUTED, length=2.2, width=0.7, pad=1.5)
    ax.set_facecolor("none")
    ax.title.set_color(accent)


def chip(ax, x, y, w, h, label, value, accent, value_size=8.6):
    """Üstte küçük başlık, altta koyu değer içeren beyaz bilgi kutucuğu."""
    rounded(ax, x, y, w, h, CANVAS, edge=LINE, lw=0.9, r=0.07, z=3)
    ax.add_patch(Rectangle((x, y + 0.08), 0.055, h - 0.16, color=accent, zorder=4))
    ax.text(x + 0.20, y + h - 0.24, label, fontsize=7.0, color=accent,
            weight="bold", va="center", ha="left", zorder=5)
    ax.text(x + 0.20, y + 0.26, value, fontsize=value_size, color=INK,
            va="center", ha="left", zorder=5)


def strip(ax, x, y, w, h, tag, accent, bg, items, value_size=8.6):
    """Etiketli yatay şerit (KAPSAM / ÇIKTI / DOĞRULAMA) ve içindeki kutucuklar."""
    shadow(ax, x, y, w, h, r=0.12)
    rounded(ax, x, y, w, h, bg, edge=accent, lw=1.1, r=0.12, z=2)

    tag_w = 1.32
    rounded(ax, x + 0.16, y + 0.18, tag_w, h - 0.36, accent, lw=0, r=0.09, z=3)
    ax.text(x + 0.16 + tag_w / 2, y + h / 2, tag, fontsize=8.6, color="white",
            weight="bold", ha="center", va="center", zorder=4)

    first = x + 0.16 + tag_w + 0.18
    span = (x + w - 0.16) - first
    gap = 0.14
    cw = (span - gap * (len(items) - 1)) / len(items)
    for i, (label, value) in enumerate(items):
        chip(ax, first + i * (cw + gap), y + 0.14, cw, h - 0.28,
             label, value, accent, value_size=value_size)


def stage_card(ax, x, y, w, h, number, title, subtitle, accent, tint):
    """Numaralı başlık bandı olan aşama kartı; gövde y-aralığını döndürür."""
    head_h = 0.54
    shadow(ax, x, y, w, h, r=0.16)
    rounded(ax, x, y, w, h, CANVAS, edge=accent, lw=1.4, r=0.16, z=2)

    # Başlık bandı: üst köşeler yuvarlak, alt köşeler düz
    rounded(ax, x, y + h - head_h, w, head_h, accent, lw=0, r=0.16, z=3)
    ax.add_patch(Rectangle((x, y + h - head_h), w, head_h * 0.55,
                           color=accent, zorder=3))

    cy = y + h - head_h / 2
    ax.add_patch(Circle((x + 0.31, cy), 0.155, facecolor="white",
                        edgecolor="none", zorder=4))
    ax.text(x + 0.31, cy - 0.005, str(number), fontsize=9.5, color=accent,
            weight="bold", ha="center", va="center", zorder=5)
    ax.text(x + 0.56, cy - 0.005, title, fontsize=11.2, color="white",
            weight="bold", ha="left", va="center", zorder=5)

    # Alt başlık: hafif tonlu şerit
    sub_y = y + h - head_h - 0.36
    rounded(ax, x + 0.12, sub_y, w - 0.24, 0.30, tint, lw=0, r=0.07, z=3)
    ax.text(x + w / 2, sub_y + 0.15, subtitle, fontsize=7.6, color=accent,
            style="italic", ha="center", va="center", zorder=4)
    return sub_y


def bullets(ax, x, y, lines, accent, dy=0.295, size=7.6):
    """Aşama kartının gövdesine madde işaretli açıklama satırları yazar."""
    for i, text in enumerate(lines):
        yy = y - i * dy
        ax.add_patch(Circle((x + 0.06, yy + 0.02), 0.035, color=accent, zorder=5))
        ax.text(x + 0.20, yy, text, fontsize=size, color="#334155",
                ha="left", va="center", zorder=5)


def flow_arrow(ax, x0, x1, y, label):
    """İki kart arasındaki veri akışı okunu ve etiketini çizer."""
    ax.add_patch(FancyArrowPatch(
        (x0, y), (x1, y), arrowstyle="-|>", mutation_scale=15,
        linewidth=2.0, color="#94A3B8", shrinkA=0, shrinkB=0, zorder=6,
    ))
    ax.text((x0 + x1) / 2, y + 0.20, label, fontsize=6.6, color=MUTED,
            weight="bold", ha="center", va="bottom", linespacing=1.15, zorder=6)


# ---------------------------------------------------------------------------
# Mini grafikler — gerçek proje fonksiyonlarından beslenir
# ---------------------------------------------------------------------------

def mini_waveform(ax, accent):
    """Bifazik ve DC (monofazik) uyarım dalga formlarını üst üste gösterir."""
    t_rect, i_rect = biphasic_waveform(1000.0, 1.0, 3.0, dt=0.002, pulse_width_ms=0.1)
    t_dc, i_dc = biphasic_waveform(1000.0, 1.0, 3.0, dt=0.002, pulse_width_ms=0.1,
                                   waveform="dc")
    ax.plot(t_dc, i_dc + 3.1, color="#94A3B8", lw=1.4)
    ax.plot(t_rect, i_rect, color=accent, lw=1.6)
    ax.axhline(0, color=LINE, lw=0.6, zorder=0)
    ax.axhline(3.1, color=LINE, lw=0.6, zorder=0)
    ax.text(3.02, 3.85, "DC", fontsize=6.4, color="#64748B", ha="right", weight="bold")
    ax.text(3.02, 1.30, "bifazik", fontsize=6.4, color=accent, ha="right", weight="bold")
    ax.set_ylim(-1.7, 4.6)
    ax.set_yticks([])
    ax.set_xticks([0, 1, 2, 3])
    ax.set_xlabel("zaman (ms)", fontsize=6.4, color=MUTED, labelpad=1)
    ax.spines["left"].set_visible(False)
    ax.set_title("uyarım dalga formu", fontsize=7.2, pad=2, weight="bold")


def mini_axon(ax, accent):
    """MRG aksonu, manşet elektrot ve elektrotun oluşturduğu alan profili."""
    node_d, node_l, inter_l, n_lam, axon_d = MRG_PARAMS[8.7]
    n_nodes = 15
    z_end = n_nodes * node_l + (n_nodes - 1) * inter_l          # µm
    z = np.linspace(0, z_end, 400)
    v_e = np.array([point_source_potential(0.0, 0.0, zz, (500.0, 0.0, 3000.0), 1000.0)
                    for zz in z])
    v_n = v_e / v_e.max()

    ax.set_xlim(-z_end * 0.02, z_end * 1.02)
    ax.set_ylim(0, 1.0)
    ax.axis("off")

    # Elektrotun oluşturduğu alan profili V_e(z)
    ax.fill_between(z, 0.62, 0.62 + 0.32 * v_n, color=accent, alpha=0.16, lw=0)
    ax.plot(z, 0.62 + 0.32 * v_n, color=accent, lw=1.5)
    ax.text(z_end, 0.99, r"$V_e(z)$", fontsize=7.2, color=accent,
            ha="right", va="top", weight="bold")

    # Manşet elektrot
    elec_z = 3000.0
    ax.plot([elec_z, elec_z], [0.50, 0.94], color="#64748B", lw=0.9, ls=(0, (2, 2)))
    ax.plot([elec_z], [0.97], marker="v", ms=5.0, color="#334155", clip_on=False)
    ax.text(elec_z - z_end * 0.055, 0.965, "elektrot", fontsize=6.6, color="#334155",
            ha="right", va="center", weight="bold")

    # Akson: miyelinli internode bantları + Ranvier düğümleri
    y0, hh = 0.28, 0.14
    for k in range(n_nodes - 1):
        x0 = node_l + k * (inter_l + node_l)
        ax.add_patch(Rectangle((x0, y0), inter_l, hh, facecolor="#CBD5E1",
                               edgecolor="#94A3B8", lw=0.4, zorder=3))
    for k in range(n_nodes):
        x0 = k * (inter_l + node_l)
        ax.add_patch(Rectangle((x0, y0 - 0.04), node_l * 90, hh + 0.08,
                               color=accent, zorder=4))
    ax.text(0, 0.14, "proksimal", fontsize=6.4, color=MUTED, ha="left", va="center")
    ax.text(z_end, 0.14, "distal düğüm →", fontsize=6.4, color=accent,
            ha="right", va="center", weight="bold")
    ax.text(z_end / 2, 0.02, "15 düğüm · miyelinli internode",
            fontsize=6.2, color=MUTED, ha="center", va="center")


def mini_raster(ax, accent):
    """20 lifli demetin jitter ve refrakter süzgecinden geçmiş spike rasteri."""
    n_fibers, freq, dur = 20, 100.0, 50.0
    base = np.arange(3.0, dur, 1000.0 / freq)
    rng = np.random.default_rng(0)
    trains = []
    for _ in range(n_fibers):
        t = np.sort(np.clip(base + rng.normal(0, 0.4, base.size), 0, None))
        kept, last = [], -np.inf
        for tt in t:                       # bridge.py ile aynı refrakter kuralı
            if tt - last >= AXON_REFRACTORY_MS:
                kept.append(tt)
                last = tt
        trains.append(np.array(kept))
    ax.eventplot(trains, colors=accent, lineoffsets=np.arange(n_fibers),
                 linelengths=0.78, linewidths=1.0)
    ax.set_xlim(0, dur)
    ax.set_ylim(-1, n_fibers)
    ax.set_yticks([0, 19])
    ax.set_yticklabels(["1", "20"])
    ax.set_ylabel("lif", fontsize=6.4, color=MUTED, labelpad=1)
    ax.set_xlabel("zaman (ms)", fontsize=6.4, color=MUTED, labelpad=1)
    ax.set_title("lif demeti · jitter σ = 0.4 ms", fontsize=7.2, pad=2, weight="bold")


def _tm_steady_ratio(freqs, U, tau_f_ms, tau_d_ms):
    """Düzenli uyarımda TM sinapsının kararlı-durum PSP / ilk PSP oranı."""
    isi = 1000.0 / np.asarray(freqs, dtype=float)
    ef, ed = np.exp(-isi / tau_f_ms), np.exp(-isi / tau_d_ms)
    u_ss = U / (1.0 - (1.0 - U) * ef)
    x_ss = (1.0 - ed) / (1.0 - (1.0 - u_ss) * ed)
    return u_ss * x_ss / U


def mini_nts(ax, accent):
    """NTS TM sinapsının Miles (1986) verisine kalibrasyonu."""
    f = np.logspace(0, 2, 200)
    ax.plot(f, _tm_steady_ratio(f, NTS_PARAMS["U"], NTS_PARAMS["tau_f_ms"],
                                NTS_PARAMS["tau_d_ms"]),
            color=accent, lw=1.8, label="model")
    ax.plot([5, 10, 20], [0.65, 0.40, 0.20], "o", ms=4.2, color="#B91C1C",
            zorder=5, label="Miles 1986")
    ax.plot([20], [0.25], "^", ms=4.6, color="#B45309", zorder=5,
            label="Beaumont 2017")
    ax.set_xscale("log")
    ax.set_xlim(1, 100)
    ax.set_ylim(0, 1.05)
    ax.set_yticks([0, 0.5, 1.0])
    ax.set_xlabel("frekans (Hz)", fontsize=6.4, color=MUTED, labelpad=1)
    ax.set_ylabel("PSP oranı", fontsize=6.4, color=MUTED, labelpad=1)
    ax.legend(fontsize=5.6, loc="upper right", frameon=False, handlelength=1.1,
              labelspacing=0.25, borderaxespad=0.1)
    ax.set_title("TM depresyonu · kalibrasyon", fontsize=7.2, pad=2, weight="bold")


def mini_regions(ax, accent, df):
    """Bölge ateşleme hızlarının frekansla değişimi (bifazik puls, 3 mA)."""
    sub = df[(df["waveform"] == "rectangular") & (df["amp_mA"] == 3.0)].sort_values("freq_hz")
    for region in REGIONS:
        ax.plot(sub["freq_hz"], sub[region], "o-", ms=3.4, lw=1.5,
                color=REGION_COLORS[region], label=REGION_LABEL[region])
    ax.set_xscale("log")
    ax.set_xticks([1, 10, 100, 1000, 10000])
    ax.set_xticklabels(["1", "10", "100", "1k", "10k"])
    ax.set_xlabel("frekans (Hz)", fontsize=6.4, color=MUTED, labelpad=1)
    ax.set_ylabel("Hz/nöron", fontsize=6.4, color=MUTED, labelpad=1)
    ax.legend(fontsize=5.6, loc="upper left", frameon=False, ncol=2,
              handlelength=1.1, labelspacing=0.25, columnspacing=0.8,
              borderaxespad=0.1)
    ax.set_title("bölge yanıtı · pulse, 3 mA", fontsize=7.2, pad=2, weight="bold")


# ---------------------------------------------------------------------------
# Ana diyagram
# ---------------------------------------------------------------------------

def build(df: pd.DataFrame, out_dir: str) -> str:
    plt.rcParams["font.family"] = "DejaVu Sans"
    fig = plt.figure(figsize=(FIG_W, FIG_H), facecolor=CANVAS)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, FIG_W)
    ax.set_ylim(0, FIG_H)
    ax.axis("off")
    ax.add_patch(Rectangle((0, 0), FIG_W, FIG_H, color=CANVAS, zorder=0))

    # ---- Başlık -----------------------------------------------------------
    ax.add_patch(Rectangle((0.29, 8.18), 0.09, 0.80, color=VIOLET[0], zorder=3))
    ax.text(0.55, 8.74, "Vagus Siniri Stimülasyonunun Frekansa Bağlı "
                        "Çok Ölçekli in Silico Modeli",
            fontsize=19.5, weight="bold", color=INK, va="center", zorder=3)
    ax.text(0.55, 8.34,
            "Amaç: uyarım frekansı, dalga şekli ve genliğinin NTS rölesi ile "
            "NAc / İnsula / CA3 yanıtlarını nasıl değiştirdiğini uçtan uca simüle etmek",
            fontsize=11.0, color=MUTED, va="center", zorder=3)

    # ---- Kapsam şeridi ----------------------------------------------------
    strip(ax, 0.29, 7.00, 15.42, 0.92, "KAPSAM", VIOLET[0], STRIP_BG, [
        ("DALGA ŞEKLİ", "DC (monofazik) · Pulse (bifazik)"),
        ("GENLİK", "1 · 2 · 3 mA"),
        ("FREKANS", "1 · 10 · 100 · 1k · 10k Hz"),
        ("TASARIM", "2 × 3 × 5 = 30 koşul × 5 tekrar"),
    ])

    # ---- Aşama kartları ---------------------------------------------------
    y0, h = 2.60, 4.14
    w, gap = 2.588, 0.62
    lefts = [0.29 + i * (w + gap) for i in range(5)]

    stages = [
        (AMBER, "UYARIM ALANI", "src/stim · McNeal 1976",
         ["$V_e = \\rho I / 4\\pi r$  (nokta kaynak)",
          "ρ = 300 Ω·cm · elektrot 500 µm",
          "puls 0.1 ms · bifazik / DC / sinüs",
          "1 Hz – 10 kHz uyarım aralığı"]),
        (RED, "SEVİYE 1 · NEURON", "MRG miyelinli akson · 2002",
         ["15 Ranvier düğümü · ø 8.7 µm",
          "miyelin: cm, g_pas ÷ 2·nl → saltatory",
          "dt = 5 µs · e_extracellular",
          "ileti hızı 30–54 m/s ✓"]),
        (SLATE, "KÖPRÜ", "NEURON → Brian2 · tek yönlü",
         ["spike zamanları aktarılır",
          "20 lifli demet · jitter σ = 0.4 ms",
          "1 ms aksonal refrakter periyot",
          "Brian2 dt ızgarasına hizalama"]),
        (TEAL, "SEVİYE 2 · NTS", "Brian2 · Tsodyks–Markram",
         ["30 LIF nöron · $\\tau_m$ = 20 ms",
          "TM: U = 0.19 · $\\tau_d$ = 810 ms",
          "deneysel veriye kalibre edildi",
          "alçak geçiren röle davranışı"]),
        (VIOLET, "SEVİYE 3 · BÖLGELER", "NAc · İnsula · CA3 · 100'er LIF",
         ["NAc: U 0.05 · $\\tau_f$ 500 ms (fasilitasyon)",
          "İnsula: U 0.40 · $\\tau_d$ 150 ms (depresyon)",
          "CA3: U 0.20 + rekürrent %12",
          "yolağa özgü plastisite"]),
    ]

    for i, ((accent, tint), title, subtitle, lines) in enumerate(stages):
        x = lefts[i]
        sub_y = stage_card(ax, x, y0, w, h, i + 1, title, subtitle, accent, tint)
        axm = inset(fig, x + 0.30, sub_y - 1.66, w - 0.50, 1.42)
        style_mini(axm, accent)
        if i == 0:
            mini_waveform(axm, accent)
        elif i == 1:
            mini_axon(axm, accent)
        elif i == 2:
            mini_raster(axm, accent)
        elif i == 3:
            mini_nts(axm, accent)
        else:
            mini_regions(axm, accent, df)
        bullets(ax, x + 0.16, sub_y - 1.98, lines, accent)

    labels = ["$V_e(t, z)$", "spike\nzamanları", "20 lifli\ndemet", "NTS\nspike'ları"]
    for i, label in enumerate(labels):
        flow_arrow(ax, lefts[i] + w + 0.06, lefts[i + 1] - 0.06, 4.55, label)

    # Seviye 3 → çıktı şeridi
    ax.add_patch(FancyArrowPatch(
        (lefts[4] + w / 2, y0 - 0.02), (lefts[4] + w / 2, 2.26),
        arrowstyle="-|>", mutation_scale=15, linewidth=2.0,
        color="#94A3B8", shrinkA=0, shrinkB=0, zorder=6,
    ))

    # ---- Çıktı ve doğrulama şeritleri -------------------------------------
    strip(ax, 0.29, 1.30, 15.42, 0.92, "ÇIKTI", "#1D4ED8", STRIP_BG, [
        ("ATEŞLEME HIZI", "Hz/nöron, ortalama ± SD (5 tekrar)"),
        ("TAKİP ORANI", "akson spike / uygulanan puls"),
        ("AKTİVASYON EŞİĞİ", "~1–2 mA (klinik VNS aralığında)"),
        ("DOSYALAR", "matris.csv → şekil 1–4 + tablo 1–2"),
    ], value_size=8.2)

    strip(ax, 0.29, 0.24, 15.42, 0.92, "DOĞRULAMA", GREEN[0], GREEN[1], [
        ("TM ANALİTİK", "simülasyon ile kalıntı < %0.2"),
        ("NTS PSP · 5/10/20 Hz", "0.60 · 0.41 · 0.26 ↔ Miles 1986"),
        ("AKTARIM @20 Hz", "0.255 ↔ Beaumont 2017 (~%25)"),
        ("İLETİ HIZI", "30–54 m/s ↔ insan vagus Aα"),
    ], value_size=8.2)

    os.makedirs(out_dir, exist_ok=True)
    png = os.path.join(out_dir, "sekil0_mimari_pano.png")
    fig.savefig(png, dpi=DPI, facecolor=CANVAS)
    fig.savefig(os.path.join(out_dir, "sekil0_mimari.pdf"), facecolor=CANVAS)
    plt.close(fig)
    return png


def main() -> None:
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    csv_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(root, "outputs", "matris.csv")
    out_dir = sys.argv[2] if len(sys.argv) > 2 else os.path.join(root, "outputs", "sekiller")
    df = pd.read_csv(csv_path)
    print(f"YAZILDI: {build(df, out_dir)}")


if __name__ == "__main__":
    main()
