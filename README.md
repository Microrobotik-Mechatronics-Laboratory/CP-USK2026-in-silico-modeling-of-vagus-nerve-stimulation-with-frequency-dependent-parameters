# Nerve Frequency Study — Periferik Sinir Stimülasyonu Frekans Çalışması

Periferik sinir stimülasyonunun frekansa bağlı beyin bölgesi yanıtlarını
çok ölçekli (multi-scale) simülasyon ile inceleyen hesaplamalı sinirbilim projesi.

> Bu proje, `nerve_frequency_study_colab.ipynb` notebook'unu modüler Python yapısına
> dönüştürerek yeniden kullanılabilir, parametreli ve CLI destekli hale getirir.

---

## 🧠 Projenin Amacı

> *"Vagus sinirini 5 Hz ile mi, 50 Hz ile mi, 200 Hz ile mi uyarırsam,
> NAc, İnsula ve CA3 gibi farklı beyin bölgelerindeki aktivite nasıl değişir?"*

Bu soru klinik olarak kritiktir: VNS (Vagus Sinir Stimülasyonu) epilepsi ve
depresyon tedavisinde kullanılmakta; hangi frekansın hangi bölgeyi aktive
ettiğini bilmek tedaviyi optimize etmek demektir.

---

## 🏗️ Çok Ölçekli Mimari

```
Level 1 (NEURON)           Level 2 (Brian2)              Level 3 (Brian2)
periferik akson       →    NTS relay sinapsı        →    NAc / İnsula / CA3
(MRG veya Sundt modeli)    (Tsodyks-Markram STP)         (popülasyon dinamiği)
```

---

## 📁 Proje Yapısı

```
ulusal-sinirbilim-kongresi/
│
├── main.py                          ← CLI giriş noktası (argparse)
├── pyproject.toml                   ← Bağımlılık yönetimi (uv)
├── nerve_frequency_study_colab.ipynb ← Orijinal notebook (referans)
├── eski_kod_tutorial.md             ← Kavram sözlüğü ve derin analiz
│
├── src/                             ← Kaynak modüller
│   ├── stim/
│   │   └── extracellular_field.py   ← Ekstrasellüler alan + dalga formu
│   ├── models/
│   │   ├── mrg_axon.py              ← MRG miyelinli akson modeli
│   │   └── sundt_cfiber.py          ← Sundt C-fiber modeli
│   ├── analysis/
│   │   └── threshold_finder.py      ← Bisection eşik bulucu
│   ├── sweep/
│   │   └── frequency_sweep.py       ← Frekans tarama protokolü
│   ├── network/
│   │   ├── bridge.py                ← NEURON → Brian2 köprüsü
│   │   ├── nts_relay.py             ← NTS + TM plastisiti
│   │   └── brain_regions.py         ← NAc / İnsula / CA3 popülasyonları
│   └── pipeline/
│       ├── level1.py                ← NEURON uyarım pipeline
│       ├── level23.py               ← Brian2 ağ pipeline
│       └── orchestrator.py          ← Uçtan uca koordinasyon
│
├── visualization/
│   └── plots.py                     ← 3 grafik tipi + dissociation tablosu
│
└── config/
    └── defaults.py                  ← Tüm parametreler tek yerde
```

---

## 🚀 Kurulum

```bash
# 1. uv ile sanal ortam oluştur
uv venv .venv --python 3.11

# 2. Sanal ortamı aktive et
source .venv/bin/activate

# 3. Bağımlılıkları yükle
uv pip install numpy pandas matplotlib brian2 neuron

# 4. (İsteğe bağlı) MRG / Sundt mekanizmalarını derle
# .mod dosyalarını proje dizinine kopyaladıktan sonra:
# nrnivmodl .
```

---

## 💻 Kullanım

```bash
# Varsayılan parametrelerle hızlı test
python main.py

# Özel frekans listesi
python main.py --frequencies 1 10 50 100 500

# Farklı genlik ve fiber çapı
python main.py --frequencies 20 100 200 --amp 5.0 --fiber-diam 12.8

# Sonuçları CSV'ye kaydet
python main.py --output results.csv

# Grafikleri dosyaya kaydet (ekranda göstermeden)
python main.py --save-plots outputs/ --no-plot

# Tam frekans aralığı (yavaş — ~15-30 dakika)
python main.py --full-range --amp 3.0

# Tüm seçenekler
python main.py --help
```

### CLI Argümanları

| Argüman | Varsayılan | Açıklama |
|:---|:---:|:---|
| `--frequencies` | `[1,5,10,20,50,100,200,500]` | Taranacak frekanslar (Hz) |
| `--full-range` | `False` | 1 Hz – 50 kHz tam aralık |
| `--amp` | `3.0` | Uyarım genliği (µA) |
| `--pulse-width` | `0.1` | Puls genişliği (ms) |
| `--fiber-diam` | `8.7` | MRG fiber çapı (µm) |
| `--n-nodes` | `15` | MRG Ranvier düğümü sayısı |
| `--elec-dist` | `500.0` | Elektrot-akson mesafesi (µm) |
| `--n-fibers` | `20` | Fiber demet büyüklüğü |
| `--active-threshold` | `0.5` | Aktiflik eşiği (Hz/nöron) |
| `--output` | `None` | CSV çıktı dosyası |
| `--save-plots` | `None` | Grafiklerin kaydedileceği dizin |
| `--no-plot` | `False` | Grafik oluşturma |
| `--quiet` | `False` | Sessiz mod |

---

## 🔬 Biyolojik Bağlam

### Beyin Bölgeleri ve Pathway Tasarımı

| Bölge | TM Tipi | U | tau_f | Davranış |
|:---|:---:|:---:|:---:|:---|
| **NAc** | Güçlü fasilitasyon | 0.05 | 500 ms | Düşük frekansta sessiz, yüksek frekansta aktif |
| **İnsula** | Hafif depresyon | 0.40 | 10 ms | Tüm frekanslarda yanıt — direkt röle |
| **CA3** | Orta fasilitasyon | 0.20 | 150 ms | Karma + rekürrent amplifikasyon |

### Temel Referanslar

| Referans | Yıl | Katkı |
|:---|:---:|:---|
| Hodgkin & Huxley | 1952 | Aksiyon potansiyeli modeli |
| McNeal | 1976 | Ekstrasellüler stimülasyon |
| Tsodyks & Markram | 1997 | Kısa süreli sinaptik plastisiti |
| McIntyre, Richardson, Grill | 2002 | MRG akson modeli |
| Sundt, Gamper, Jaffe | 2015 | C-fiber iyon kanal modeli |

---

## ⚠️ Önemli Uyarılar

1. **El ayarı parametreler**: TM parametreleri gerçek elektrofizyoloji verisine fit edilmemiş.
2. **Tek stokastik deneme**: Güvenilir sonuç için 5-10 tekrar ortalaması alın.
3. **20 fiber sınırlaması**: Gerçek vagus siniri ~80,000 fiber içerir.
4. **İnhibisyon eksik**: CA3'te GABAerjik internöron yok (Faz 4 hedefi).
5. **HH fallback**: MRG mekanizması derlenmezse HH kullanılır — eşikler farklı çıkar.

---

## 🗺️ Geliştirme Fazları

- ✅ **Faz 1**: Notebook → modüler Python yapısı + CLI (tamamlandı)
- ⬜ **Faz 2**: Modülleri birleştirip `main.py` ile çalıştırma
- ⬜ **Faz 3**: Sorunlu kısımların tespiti ve düzeltilmesi
- ⬜ **Faz 4**: Kod kalitesi, dokümantasyon ve verimlilik iyileştirmeleri
