# Faz 1 — Notebook'tan Modüler Python Proje Yapısına Geçiş

## Amaç

`nerve_frequency_study_colab.ipynb` dosyasındaki tüm kod hücreleri, **mantıksal ve biyolojik** sınırlarına göre ayrı Python modüllerine bölünecek. Notebook'taki markdown hücrelerinin (section başlıkları ve açıklamalar) zaten *hangi dosyaya gitmeleri gerektiğini* söylediğine dikkat edin — dosya isimleri notebook yorumlarında da geçiyor (`stim/extracellular_field.py`, `models/mrg_axon.py` vb.).

Bu aşamada **kaynak koda dokunulmaz** — sadece kopyalanır ve düzenlenir. Faz 2'de entegrasyon, Faz 3-4'te iyileştirme yapılacak.

---

## Önerilen Dizin Yapısı

```
ulusal-sinirbilim-kongresi/
├── nerve_frequency_study_colab.ipynb   ← mevcut (dokunulmaz)
├── eski_kod_tutorial.md                ← mevcut (dokunulmaz)
├── README.md                           ← mevcut (güncellenecek)
│
├── src/                                ← tüm modüller burada
│   ├── __init__.py
│   │
│   ├── stim/                           ← Uyarım (stimülasyon) katmanı
│   │   ├── __init__.py
│   │   └── extracellular_field.py      ← point_source_potential, biphasic_waveform, apply_extracellular_field
│   │
│   ├── models/                         ← Nöron/akson modelleri
│   │   ├── __init__.py
│   │   ├── mrg_axon.py                 ← MRG_PARAMS, MRGAxon sınıfı
│   │   └── sundt_cfiber.py             ← CFiber sınıfı
│   │
│   ├── analysis/                       ← Analiz araçları
│   │   ├── __init__.py
│   │   └── threshold_finder.py         ← find_threshold, verify_bracket
│   │
│   ├── sweep/                          ← Frekans tarama protokolü
│   │   ├── __init__.py
│   │   └── frequency_sweep.py          ← ELECTRODE_POS, sweep_fiber, default_frequency_range, ...
│   │
│   ├── network/                        ← Brian2 ağ katmanı
│   │   ├── __init__.py
│   │   ├── bridge.py                   ← neuron_spikes_to_brian_group, merge_fiber_populations, bundle_from_single_fiber
│   │   ├── nts_relay.py                ← NTS_EQS, TM_SYN_EQS, TM_ON_PRE, build_nts_relay, make_tm_conn
│   │   └── brain_regions.py            ← LIF_EQS, build_lif_population, build_nac, build_insula, build_ca3
│   │
│   └── pipeline/                       ← Uçtan uca pipeline fonksiyonları
│       ├── __init__.py
│       ├── level1.py                   ← run_level1
│       ├── level23.py                  ← run_levels_2_3, run_full_network
│       └── orchestrator.py             ← run_one_frequency, cycles_to_duration_ms
│
├── visualization/                      ← Görselleştirme
│   ├── __init__.py
│   └── plots.py                        ← plot_region_curves, plot_heatmap, plot_grouped_bar, plot_dissociation
│
├── config/                             ← Sabit parametreler (Faz 1'de oluşturulur, Faz 2-4'te kullanılır)
│   └── defaults.py                     ← ELECTRODE_POS, MRG_PARAMS, TM parametreleri, vb.
│
└── main.py                             ← Faz 1 sonu: argparse ile CLI arayüzü
```

---

## Dosya → Notebook Hücre Eşlemesi

| Hedef Dosya | Notebook Cell | İçerik |
|:---|:---:|:---|
| `src/stim/extracellular_field.py` | Cell 8 | `point_source_potential`, `biphasic_waveform`, `apply_extracellular_field` |
| `src/models/mrg_axon.py` | Cell 10 | `MRG_PARAMS`, `_has_mrg_mechanism`, `MRGAxon` |
| `src/models/sundt_cfiber.py` | Cell 12 | `_has_sundt_mechanism`, `CFiber` |
| `src/analysis/threshold_finder.py` | Cell 14 | `find_threshold`, `verify_bracket` |
| `src/sweep/frequency_sweep.py` | Cell 16 | `ELECTRODE_POS`, `_run_activation_trial`, `_run_block_trial`, `default_frequency_range`, `sweep_fiber` |
| `src/network/bridge.py` | Cell 20, 26 (kısmen) | `neuron_spikes_to_brian_group`, `merge_fiber_populations`, `bundle_from_single_fiber` |
| `src/network/nts_relay.py` | Cell 21 | `NTS_EQS`, `TM_SYN_EQS`, `TM_ON_PRE`, `build_nts_relay`, `make_tm_conn` |
| `src/network/brain_regions.py` | Cell 22, 26 (kısmen) | `LIF_EQS`, `_build_lif_population`, `build_pop`, `build_ca3_r`, bölge builder'ları |
| `src/pipeline/level1.py` | Cell 24 | `run_level1` |
| `src/pipeline/level23.py` | Cell 24 (devam), 27 | `run_levels_2_3`, `run_full_network` |
| `src/pipeline/orchestrator.py` | Cell 28, 30 | `cycles_to_duration_ms`, `run_one_frequency` |
| `visualization/plots.py` | Cell 32, 34, 36, 38 | tüm plot fonksiyonları |
| `config/defaults.py` | Hepsinden toplanan | sabitler ve varsayılan parametreler |
| `main.py` | — | argparse CLI |

---

## `main.py` Tasarımı (Faz 1 Hedefi)

`main.py` şu parametreleri CLI'dan alabilecek:

```
python main.py \
  --frequencies 1 5 10 20 50 100 200 500 \   # hangi frekanslar taransın
  --amp 3.0 \                                 # uyarım genliği (μA)
  --n_fibers 20 \                             # fiber demeti büyüklüğü
  --fiber_diam 8.7 \                          # MRG akson çapı (μm)
  --n_nodes 15 \                              # MRG düğüm sayısı
  --elec_dist 500.0 \                         # elektrот mesafesi (μm)
  --active_threshold 0.5 \                    # "aktif" sayılma eşiği (Hz/neuron)
  --output results.csv \                      # CSV çıktı dosyası
  --plot                                      # grafik göster
```

---

## Önemli Notlar

> [!IMPORTANT]
> **Faz 1'de kod değiştirilmiyor.** Tek yapılan iş: notebook hücrelerini doğru import'larla uygun dosyalara kopyalamak. `from neuron import h, np` gibi import'lar üstte toplanır; fonksiyon gövdeleri birebir aynı kalır.

> [!NOTE]
> Cell 1-6 setup hücreleri (`pip install`, `nrnivmodl` derleme, `h.load_file("stdrun.hoc")`) `main.py`'nin başına veya ayrı bir `setup.py`/`environment` dosyasına alınacak — bunlar notebook'a özgü bootstrap kodu.

> [!NOTE]
> Cell 26, hem `LIF_EQS_R`/`build_pop`/`build_ca3_r` tanımları **hem de** `bundle_from_single_fiber`/`make_tm_conn` tanımlarını içeriyor. Bu hücre **iki farklı modüle** bölünecek: `brain_regions.py` ve `bridge.py`.

> [!WARNING]
> Cell 21'deki `build_nts_relay` fonksiyonu `connect_region` adlı bir yardımcıya referans veriyor ama bu fonksiyon Cell 24'teki `run_levels_2_3` içinde `relay_to_ca3 = connect_region(nts, ca3_pop, p=0.25)` şeklinde kullanılıyor. `connect_region` fonksiyonu notebook'ta **tanımlanmamış** — Faz 3'te tespit edilecek eksik fonksiyonlardan biri.

---

## Doğrulama Planı

Faz 1 tamamlandığında:
- `python -c "from src.stim.extracellular_field import point_source_potential; print('OK')"` çalışmalı
- `python -c "from src.models.mrg_axon import MRGAxon; print('OK')"` çalışmalı
- `python main.py --help` çalışmalı ve tüm argümanları listemeli
- Hiçbir `SyntaxError` veya `ImportError` olmamalı (runtime hatalar — NEURON kurulmamış olabilir — Faz 2-3 için bekleniyor)
