"""
outputs/run_matris.py
=====================
Bildiri özetindeki parametre matrisini üretir:
    bölge (NTS/NAc/İnsula/CA3) x dalga şekli (DC, pulse) x genlik x frekans

Tümü kütüphane API'si üzerinden çalışır; hiçbir monkeypatch yoktur.

Kullanım:
    .venv/bin/python outputs/run_matris.py outputs/matris.csv
"""

import os
import sys
import time

# Script proje kökünün alt dizininde durduğu için kökü yola ekliyoruz.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd

from src.pipeline.orchestrator import run_frequency_sweep

FREQS = [1.0, 10.0, 100.0, 1000.0, 10000.0]      # Hz
AMPS = [1000.0, 2000.0, 3000.0]                   # µA  (= 1, 2, 3 mA)
WAVEFORMS = ["dc", "rectangular"]
WINDOW_MS = 1000.0                                # sabit analiz penceresi
N_REPEATS = 5


def main() -> None:
    out_path = sys.argv[1] if len(sys.argv) > 1 else "outputs/matris.csv"
    rows = []
    started = time.time()

    for waveform in WAVEFORMS:
        for amp in AMPS:
            print(f"\n=== {waveform} | {amp / 1000:.0f} mA ===", flush=True)
            records = run_frequency_sweep(
                frequencies=FREQS,
                amp=amp,
                waveform=waveform,
                analysis_window_ms=WINDOW_MS,
                n_repeats=N_REPEATS,
                verbose=True,
            )
            for record in records:
                record["waveform"] = waveform
                record["amp_mA"] = amp / 1000.0
                rows.append(record)
            print(f"    ({time.time() - started:.0f} s)", flush=True)

    df = pd.DataFrame(rows)
    lead = ["waveform", "amp_mA", "freq_hz", "duration_ms",
            "n_pulses", "n_axon_spikes", "follow_ratio"]
    df = df[lead + [c for c in df.columns if c not in lead]]
    df.to_csv(out_path, index=False)
    print(f"\nYAZILDI: {out_path}  ({len(df)} satır)", flush=True)


if __name__ == "__main__":
    main()
