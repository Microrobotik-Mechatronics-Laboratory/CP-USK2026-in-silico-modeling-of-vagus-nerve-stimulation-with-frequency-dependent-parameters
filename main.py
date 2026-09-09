#!/usr/bin/env python3
"""
main.py — Periferik Sinir Stimülasyonu Frekans Çalışması
=========================================================
Periferik sinir stimülasyonunun frekansa bağlı beyin bölgesi yanıtlarını
multi-scale simülasyon ile inceler.

Pipeline:
    Level 1 (NEURON): Periferik MRG aksonu → spike zamanları
    Level 2 (Brian2): NTS relay (Tsodyks-Markram plastisiti)
    Level 3 (Brian2): NAc / İnsula / CA3 downstream bölgeler

Kullanım Örnekleri
------------------
Hızlı test (varsayılan parametreler):
    python main.py

Özel frekans listesi:
    python main.py --frequencies 1 10 50 100

Tam sweep, yüksek genlik:
    python main.py --frequencies 1 5 10 20 50 100 200 500 --amp 5.0

Sonuçları CSV'ye kaydet:
    python main.py --output results.csv

Grafikleri dosyaya kaydet:
    python main.py --save-plots outputs/

Farklı fiber tipi:
    python main.py --fiber-diam 12.8 --n-nodes 21

Yalnızca dissociation tablosu:
    python main.py --no-plot --output results.csv
"""

import argparse
import os
import sys


# ---------------------------------------------------------------------------
# Argüman ayrıştırıcı
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    """CLI argüman ayrıştırıcısını oluşturur."""
    parser = argparse.ArgumentParser(
        prog="main.py",
        description=(
            "Periferik sinir stimülasyonunun frekansa bağlı beyin bölgesi yanıtlarını "
            "multi-scale simülasyon (NEURON + Brian2) ile inceler."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # --- Frekans parametreleri ---
    freq_group = parser.add_argument_group("Frekans Parametreleri")
    freq_group.add_argument(
        "--frequencies",
        nargs="+",
        type=float,
        default=None,
        metavar="HZ",
        help=(
            "Taranacak frekanslar (Hz). Boşlukla ayırın. "
            "Varsayılan: config/defaults.py'deki DEFAULT_FREQUENCIES."
        ),
    )
    freq_group.add_argument(
        "--full-range",
        action="store_true",
        default=False,
        help=(
            "Varsayılan tam frekans aralığını kullan "
            "(1 Hz – 50 kHz, aktivasyon + KHFAC blok). Yavaş!"
        ),
    )

    # --- Uyarım parametreleri ---
    stim_group = parser.add_argument_group("Uyarım Parametreleri")
    stim_group.add_argument(
        "--amp",
        type=float,
        default=None,
        metavar="uA",
        help="Uyarım genliği (µA). Varsayılan: config/defaults.py → DEFAULT_AMP.",
    )
    stim_group.add_argument(
        "--pulse-width",
        type=float,
        default=None,
        metavar="MS",
        help="Puls genişliği (ms). Varsayılan: 0.1 ms = 100 µs.",
    )

    # --- Fiber/elektrot parametreleri ---
    fiber_group = parser.add_argument_group("Fiber / Elektrot Parametreleri")
    fiber_group.add_argument(
        "--fiber-diam",
        type=float,
        default=None,
        metavar="UM",
        choices=[5.7, 8.7, 12.8, 16.0],
        help=(
            "MRG akson çapı (µm). "
            "Geçerli değerler: 5.7 (Aδ), 8.7 (Aβ), 12.8 (Aα), 16.0 (Aα kalın). "
            "Varsayılan: 8.7 µm."
        ),
    )
    fiber_group.add_argument(
        "--n-nodes",
        type=int,
        default=None,
        metavar="N",
        help="MRG Ranvier düğümü sayısı. Varsayılan: 15 (hız/doğruluk dengesi).",
    )
    fiber_group.add_argument(
        "--elec-dist",
        type=float,
        default=None,
        metavar="UM",
        help=(
            "Elektrot-akson mesafesi x ekseninde (µm). "
            "Varsayılan: config/defaults.py → DEFAULT_ELEC_DIST = 500 µm."
        ),
    )

    # --- Brian2 ağ parametreleri ---
    net_group = parser.add_argument_group("Brian2 Ağ Parametreleri")
    net_group.add_argument(
        "--n-fibers",
        type=int,
        default=None,
        metavar="N",
        help=(
            "Fiber demet büyüklüğü. Varsayılan: 20. "
            "Daha fazla fiber → pürüzsüz yanıt ama yavaş."
        ),
    )
    net_group.add_argument(
        "--active-threshold",
        type=float,
        default=None,
        metavar="HZ",
        help="Bölgeyi 'aktif' sayan ateşleme hızı eşiği (Hz/nöron). Varsayılan: 0.5.",
    )

    # --- Çıktı parametreleri ---
    out_group = parser.add_argument_group("Çıktı Parametreleri")
    out_group.add_argument(
        "--output",
        type=str,
        default=None,
        metavar="DOSYA.csv",
        help="Sonuçları bu CSV dosyasına kaydet. Varsayılan: kaydetme.",
    )
    out_group.add_argument(
        "--save-plots",
        type=str,
        default=None,
        metavar="DIZIN",
        help="Grafikleri bu dizine PNG olarak kaydet. Varsayılan: ekranda göster.",
    )
    out_group.add_argument(
        "--no-plot",
        action="store_true",
        default=False,
        help="Hiçbir grafik gösterme veya kaydetme.",
    )
    out_group.add_argument(
        "--quiet",
        action="store_true",
        default=False,
        help="Frekans başına ilerleme mesajlarını gizle.",
    )

    return parser


# ---------------------------------------------------------------------------
# Ana fonksiyon
# ---------------------------------------------------------------------------

def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    # --- Geç import: NEURON ve Brian2 yalnızca gerçekten çalışırken yüklenir ---
    # Bu, `python main.py --help` komutunun NEURON kurulmadan çalışmasını sağlar.
    try:
        import pandas as pd
        from config.defaults import (
            DEFAULT_FREQUENCIES,
            DEFAULT_AMP,
            DEFAULT_N_FIBERS,
            DEFAULT_FIBER_DIAM,
            DEFAULT_N_NODES,
            DEFAULT_ELEC_DIST,
            DEFAULT_ELEC_Z,
            DEFAULT_PULSE_WIDTH,
            DEFAULT_ACTIVE_THRESHOLD_HZ,
        )
        from src.pipeline.orchestrator import run_frequency_sweep
        from src.sweep.frequency_sweep import default_frequency_range
        from visualization.plots import (
            plot_region_curves,
            plot_heatmap,
            plot_grouped_bar,
            plot_dissociation_table,
        )
    except ImportError as e:
        print(f"[HATA] Gerekli modül yüklenemedi: {e}")
        print("Kurulum: pip install neuron brian2 numpy pandas matplotlib")
        sys.exit(1)

    # --- Parametreleri çöz (CLI → defaults öncelik sırası) ---
    frequencies = (
        default_frequency_range() if args.full_range
        else (args.frequencies or DEFAULT_FREQUENCIES)
    )
    # Not: "or DEFAULT_X" yerine "is not None" — 0 Python'da falsy olduğu için
    # --amp 0 (uyarımsız temel çizgi) veya --active-threshold 0 (her spike aktif
    # sayılsın) gibi anlamlı sıfır değerleri sessizce varsayılana dönmemeli.
    amp           = args.amp         if args.amp         is not None else DEFAULT_AMP
    n_fibers      = args.n_fibers    if args.n_fibers    is not None else DEFAULT_N_FIBERS
    fiber_diam    = args.fiber_diam  if args.fiber_diam  is not None else DEFAULT_FIBER_DIAM
    n_nodes       = args.n_nodes     if args.n_nodes     is not None else DEFAULT_N_NODES
    elec_dist     = args.elec_dist   if args.elec_dist   is not None else DEFAULT_ELEC_DIST
    pulse_width   = args.pulse_width if args.pulse_width is not None else DEFAULT_PULSE_WIDTH
    active_thresh = (args.active_threshold if args.active_threshold is not None
                     else DEFAULT_ACTIVE_THRESHOLD_HZ)
    verbose       = not args.quiet

    # Elektrot konumu: --elec-dist x eksenindeki mesafeyi belirler; z konumu
    # config/defaults.py'deki DEFAULT_ELEC_Z'den gelir (aksonun ortasına yakın).
    elec_pos = (elec_dist, 0.0, DEFAULT_ELEC_Z)

    print("=" * 60)
    print("Periferik Sinir Stimülasyonu — Frekans Çalışması")
    print("=" * 60)
    print(f"  Frekanslar : {frequencies} Hz")
    print(f"  Genlik     : {amp} µA")
    print(f"  Puls genişliği: {pulse_width} ms")
    print(f"  Fiber çapı : {fiber_diam} µm  |  Düğüm sayısı: {n_nodes}")
    print(f"  Elektrot   : x={elec_dist} µm, z={DEFAULT_ELEC_Z} µm")
    print(f"  Fiber demeti: {n_fibers} fiber")
    print(f"  Aktif eşiği: {active_thresh} Hz/nöron")
    print("=" * 60)

    # --- Simülasyon ---
    records = run_frequency_sweep(
        frequencies=frequencies,
        amp=amp,
        n_fibers=n_fibers,
        verbose=verbose,
        fiber_diam=fiber_diam,
        n_nodes=n_nodes,
        elec_pos=elec_pos,
        pulse_width_ms=pulse_width,
    )

    df = pd.DataFrame(records)

    # --- CSV çıktısı ---
    if args.output:
        df.to_csv(args.output, index=False)
        print(f"\nSonuçlar kaydedildi: {args.output}")

    # --- Konsol özeti ---
    print("\n--- Sonuç Özeti ---")
    print(df[["freq_hz", "n_axon_spikes", "NTS", "NAc", "Insula", "CA3"]].to_string(index=False))

    # --- Dissociation tablosu ---
    print("\n--- Dissociation Tablosu ---")
    dissoc_save = None
    if args.output:
        dissoc_save = args.output.replace(".csv", "_dissociation.csv")
    plot_dissociation_table(df, threshold_hz=active_thresh, save_path=dissoc_save)

    # --- Grafikler ---
    if not args.no_plot:
        save_dir = args.save_plots
        if save_dir:
            os.makedirs(save_dir, exist_ok=True)

        _p = lambda name: os.path.join(save_dir, name) if save_dir else None

        plot_region_curves(df,  save_path=_p("fig1_region_curves.png"))
        plot_heatmap(df,         save_path=_p("fig2_heatmap.png"))
        plot_grouped_bar(df,     save_path=_p("fig3_grouped_bar.png"))

    print("\nTamamlandı.")


if __name__ == "__main__":
    main()
