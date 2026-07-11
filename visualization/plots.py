"""
visualization/plots.py
=======================
Çok bölgeli frekans yanıt görselleştirmeleri.

Üç ana grafik tipi ve bir dissociation tablosu üretir:
    1. Bölgesel frekans-yanıt eğrileri (log-x)
    2. Isı haritası (region × frequency)
    3. Gruplandırılmış çubuk grafik

Kaynak: nerve_frequency_study_colab.ipynb — Cell 32, 34, 36, 38
"""

import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

from config.defaults import REGION_COLORS, DEFAULT_ACTIVE_THRESHOLD_HZ


def _save_or_show(fig, save_path):
    """
    Grafiği dosyaya kaydeder (save_path verilmişse) veya ekranda gösterir.

    Parametreler
    ------------
    fig : matplotlib.figure.Figure
    save_path : str veya None
        Verilirse dpi=150, bbox_inches="tight" ile kaydedilir.
    """
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
    else:
        plt.show()


def plot_region_curves(df, regions=None, colors=None, save_path=None):
    """
    Her bölge için ateşleme hızı vs. stimülasyon frekansı eğrilerini çizer.

    X ekseni logaritmik ölçekte — sinir sistemi logaritmik ölçekte çalışır
    (Weber-Fechner yasası).

    Parametreler
    ------------
    df : pd.DataFrame
        run_frequency_sweep() çıktısından oluşturulmuş DataFrame.
        Sütunlar: "freq_hz", "NTS", "NAc", "Insula", "CA3".
    regions : list of str, optional
        Çizilecek bölgeler. Varsayılan: ["NTS", "NAc", "Insula", "CA3"].
    colors : dict, optional
        {bölge: renk} sözlüğü. Varsayılan: config.REGION_COLORS.
    save_path : str, optional
        Kaydedilecek dosya yolu. None ise kaydetmez.

    Döndürür
    --------
    tuple(fig, ax)
        Matplotlib Figure ve Axes nesneleri.
    """
    if regions is None:
        regions = ["NTS", "NAc", "Insula", "CA3"]
    if colors is None:
        colors = REGION_COLORS

    fig, ax = plt.subplots(figsize=(8, 5))
    for region in regions:
        ax.plot(
            df["freq_hz"], df[region],
            marker="o", label=region,
            color=colors.get(region, None),
            linewidth=2,
        )

    ax.set_xscale("log")
    ax.set_xlabel("Stimülasyon frekansı (Hz)")
    ax.set_ylabel("Ortalama ateşleme hızı (Hz/nöron)")
    ax.set_title("Bölgeye özgü frekans yanıtı")
    ax.legend()
    ax.grid(True, which="both", alpha=0.3)
    plt.tight_layout()

    _save_or_show(fig, save_path)

    return fig, ax


def plot_heatmap(df, regions=None, save_path=None):
    """
    Bölge × frekans ısı haritası çizer.

    Her hücre, ilgili bölgenin o frekanstaki ortalama ateşleme hızını gösterir.
    Belirli bir bölge/frekans kombinasyonunu hızlıca taramak için kullanışlıdır.

    Parametreler
    ------------
    df : pd.DataFrame
        run_frequency_sweep() çıktısından oluşturulmuş DataFrame.
    regions : list of str, optional
        Satır sırası. Varsayılan: ["NAc", "Insula", "CA3", "NTS"].
    save_path : str, optional
        Kaydedilecek dosya yolu.

    Döndürür
    --------
    tuple(fig, ax)
    """
    if regions is None:
        regions = ["NAc", "Insula", "CA3", "NTS"]

    heat_data = df[regions].to_numpy().T  # satırlar=bölgeler, sütunlar=frekanslar

    fig, ax = plt.subplots(figsize=(8, 4))
    im = ax.imshow(heat_data, aspect="auto", cmap="viridis")
    ax.set_yticks(range(len(regions)))
    ax.set_yticklabels(regions)
    ax.set_xticks(range(len(df["freq_hz"])))
    ax.set_xticklabels(df["freq_hz"])
    ax.set_xlabel("Stimülasyon frekansı (Hz)")
    ax.set_title("Bölge aktivite ısı haritası")

    # Her hücreye sayısal değer yaz
    for i in range(len(regions)):
        for j in range(len(df["freq_hz"])):
            value = heat_data[i, j]
            text_color = "white" if value < heat_data.max() * 0.6 else "black"
            ax.text(j, i, f"{value:.1f}", ha="center", va="center",
                    color=text_color, fontsize=8)

    fig.colorbar(im, ax=ax, label="Hz/nöron")
    plt.tight_layout()

    _save_or_show(fig, save_path)

    return fig, ax


def plot_grouped_bar(df, regions=None, colors=None, save_path=None):
    """
    Her frekans için bölgeleri yan yana karşılaştıran gruplandırılmış çubuk grafik.

    Parametreler
    ------------
    df : pd.DataFrame
        run_frequency_sweep() çıktısından oluşturulmuş DataFrame.
    regions : list of str, optional
        Çizilecek bölgeler. Varsayılan: ["NAc", "Insula", "CA3", "NTS"].
    colors : dict, optional
        {bölge: renk} sözlüğü.
    save_path : str, optional
        Kaydedilecek dosya yolu.

    Döndürür
    --------
    tuple(fig, ax)
    """
    if regions is None:
        regions = ["NAc", "Insula", "CA3", "NTS"]
    if colors is None:
        colors = REGION_COLORS

    fig, ax = plt.subplots(figsize=(10, 5))
    x = np.arange(len(df))
    width = 0.2

    for i, region in enumerate(regions):
        ax.bar(
            x + i * width, df[region],
            width, label=region,
            color=colors.get(region, None),
        )

    ax.set_xticks(x + (len(regions) - 1) * width / 2)
    ax.set_xticklabels(df["freq_hz"])
    ax.set_xlabel("Stimülasyon frekansı (Hz)")
    ax.set_ylabel("Ortalama ateşleme hızı (Hz/nöron)")
    ax.set_title("Frekans başına bölge karşılaştırması")
    ax.legend()
    ax.grid(True, axis="y", alpha=0.3)
    plt.tight_layout()

    _save_or_show(fig, save_path)

    return fig, ax


def plot_dissociation_table(df, regions=None,
                            threshold_hz=DEFAULT_ACTIVE_THRESHOLD_HZ,
                            save_path=None):
    """
    Hangi frekansın hangi bölgeyi aktive ettiğini gösteren dissociation tablosu.

    Her bölge threshold_hz üzerinde ateşliyorsa "aktif" (True) sayılır.

    Parametreler
    ------------
    df : pd.DataFrame
        run_frequency_sweep() çıktısından oluşturulmuş DataFrame.
    regions : list of str, optional
        Analiz edilecek bölgeler. Varsayılan: ["NTS", "NAc", "Insula", "CA3"].
    threshold_hz : float, optional
        Aktiflik eşiği (Hz/nöron). Varsayılan: config.DEFAULT_ACTIVE_THRESHOLD_HZ.
    save_path : str, optional
        CSV olarak kaydedilecek dosya yolu. None ise yazdırılır.

    Döndürür
    --------
    pd.DataFrame
        Dissociation tablosu; bool sütunları: "{bölge}_active".

    Notlar
    ------
    Kaynak: nerve_frequency_study_colab.ipynb — Cell 38
    Uyarı: threshold_hz gerçek elektrofizyoloji verisine göre ayarlanmalıdır.
    """
    if regions is None:
        regions = ["NTS", "NAc", "Insula", "CA3"]

    dissociation = df.copy()
    for region in regions:
        dissociation[region + "_active"] = dissociation[region] > threshold_hz

    active_cols = ["freq_hz"] + [r + "_active" for r in regions]
    result = dissociation[active_cols]

    if save_path:
        result.to_csv(save_path, index=False)
        print(f"Dissociation tablosu kaydedildi: {save_path}")
    else:
        print(result.to_string(index=False))

    return result
