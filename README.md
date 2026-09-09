# Nerve Frequency Study — Periferik Sinir Stimülasyonu Frekans Çalışması

Periferik sinir stimülasyonunun frekansa bağlı beyin bölgesi yanıtlarını
çok ölçekli (multi-scale) simülasyon ile inceleyen hesaplamalı sinirbilim projesi.

> Bu proje, `nerve_frequency_study_colab.ipynb` notebook'unu modüler Python yapısına
> dönüştürerek yeniden kullanılabilir, parametreli ve CLI destekli hale getirir.

---

## Projenin Amacı

> *"Vagus sinirini 5 Hz ile mi, 50 Hz ile mi, 200 Hz ile mi uyarırsam,
> NAc, İnsula ve CA3 gibi farklı beyin bölgelerindeki aktivite nasıl değişir?"*

Bu soru klinik olarak kritiktir: VNS (Vagus Sinir Stimülasyonu) epilepsi ve
depresyon tedavisinde kullanılmakta; hangi frekansın hangi bölgeyi aktive
ettiğini bilmek tedaviyi optimize etmek demektir.

---

## Çok Ölçekli Mimari

```
Level 1 (NEURON)           Level 2 (Brian2)              Level 3 (Brian2)
periferik akson       →    NTS relay sinapsı        →    NAc / İnsula / CA3
(MRG veya Sundt modeli)    (Tsodyks-Markram STP)         (popülasyon dinamiği)
```

---

## Proje Yapısı

```
ulusal-sinirbilim-kongresi/
│
├── main.py                          ← CLI giriş noktası (argparse)
├── pyproject.toml                   ← Bağımlılık yönetimi (uv) + mypy/pytest config
├── REFERENCES.md                    ← Akademik referanslar (tam atıflar)
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
├── tests/                           ← pytest birim testleri
│
└── config/
    └── defaults.py                  ← Tüm parametreler tek yerde
```

---

## Kurulum

## uv Kurulumu

Bu proje bağımlılık ve sanal ortam yönetimi için [uv](https://docs.astral.sh/uv/)
kullanır. Aşağıdaki adımlarla işletim sisteminize göre kurabilirsiniz
(detaylar: [uv kurulum dokümantasyonu](https://docs.astral.sh/uv/getting-started/installation/)).

**macOS / Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows (PowerShell):**
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Kurulumdan sonra terminali yeniden başlatın ve doğrulayın:
```bash
uv --version
```

---

## Proje Bağımlılıkları

```bash
# 1. uv ile sanal ortam oluştur
uv venv --python 3.11

# 2. Bağımlılıkları yükle (numpy<2.0 kısıtı kritik — NEURON numpy 2.x ile uyumsuz)
uv pip install --python .venv/bin/python "numpy>=1.24,<2.0" pandas matplotlib brian2 neuron

# 3. Geliştirme bağımlılıkları (test + tip kontrolü, isteğe bağlı)
uv pip install --python .venv/bin/python "pytest>=7.0" "mypy>=1.8"

# 4. MRG / Sundt NEURON mekanizmalarını derle
cd mechanisms && ../.venv/bin/nrnivmodl && cd ..
```

### Test ve Tip Kontrolü

```bash
.venv/bin/python -m pytest tests/ -v
.venv/bin/python -m mypy config src visualization main.py tests
```

---

## Kullanım

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

## Biyolojik Bağlam

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

Tam atıflar ve ModelDB accession numaraları için: [REFERENCES.md](REFERENCES.md)

---

## Önemli Uyarılar

1. **El ayarı parametreler**: TM parametreleri gerçek elektrofizyoloji verisine fit edilmemiş.
2. **Tek stokastik deneme**: Güvenilir sonuç için 5-10 tekrar ortalaması alın.
3. **20 fiber sınırlaması**: Gerçek vagus siniri ~80,000 fiber içerir.
4. **İnhibisyon eksik**: CA3'te GABAerjik internöron yok — biyolojik model
   kalibrasyonu gerektirdiği için literatür incelemesi bekleniyor (bkz. aşağıdaki
   Teorik Kısıt bölümü, TK-003).
5. **HH fallback**: MRG mekanizması derlenmezse HH kullanılır — eşikler farklı çıkar.

---

## Çözülen Kod Sorunları (2026-09-09)

2026-07-15 kod incelemesinde tespit edilen beş yazılım sorunu (BUG-001..005)
düzeltildi. Bulguların tam metni `SDLC/KOD_INCELEMESI_2026-07-15.md`'de,
düzeltme kayıtları `SDLC/MEVCUT_DURUM.md`'de.

| ID | Öncelik | Sorun | Durum |
|:---|:---:|:---|:---|
| BUG-001 | Kritik | `--fiber-diam`, `--n-nodes`, `--elec-dist`, `--pulse-width` parse ediliyor ama simülasyona iletilmiyordu | Zincir bağlandı: `main.py` → `run_frequency_sweep()` → `run_one_frequency()` → `run_level1()`. Regresyon testleriyle korunuyor. |
| BUG-002 | Orta | `n_neurons` sözlüğü elle kopyalanmış sabitlerden geliyordu | Artık `NTS_PARAMS` / `*_PATHWAY_PARAMS`'tan türetiliyor |
| BUG-003 | Orta | `args.x or DEFAULT_X` — `--amp 0` sessizce varsayılana dönüyordu | `is not None` kontrolüne geçildi |
| BUG-004 | Düşük | `section_coords(elec_z=...)` tanımlı ama kullanılmıyordu | Ölü parametre kaldırıldı, elektrot hizalama sorumluluğu docstring'de netleştirildi |
| BUG-005 | Düşük | `build_nts_relay()` TM parametreleri config'ten kopuk; `run_frequency_sweep` export edilmiyor; `bridge.py`'de kullanılmayan API | TM parametreleri `NTS_PARAMS` / `NTS_FACILITATING_PARAMS`'tan; export eklendi; `bridge.py` API'sinin bağımsız araç statüsü belgelendi |

Ayrıca bu oturumda, proje yolunda ASCII olmayan karakter varken NEURON
mekanizma kütüphanesinin yüklenememesi sorunu giderildi (aşağıya bakınız).

### Yol Kısıtı — ASCII Olmayan Karakterler

NEURON'un `h.nrn_load_dll()` çağrısı yolu HOC yorumlayıcısına aktarır ve HOC
yalnızca ASCII kabul eder. Proje yolunda Türkçe karakter varsa mekanizma
yüklemesi `'ascii' codec can't encode character` hatasıyla başarısız olurdu.
`src/models/_neuron_mechanisms.py` artık böyle bir durumda önce göreli yola,
o da yeterli değilse geçici bir ASCII dizindeki sembolik bağlantıya düşüyor.

> **Not:** Bu düzeltme yalnızca *yüklemeyi* kapsar. `nrnivmodl` ile
> **derleme** hâlâ boşluksuz ve ASCII bir yol gerektirir (`make` boşluklu
> yolları parçalar). Mekanizmaları yeniden derlemeniz gerekirse projeyi
> geçici olarak böyle bir dizine kopyalayın.


## Commit Formatı

```
tip(kapsam): kısa açıklama

Örnekler:
  fix(models): fizyolojik sıcaklık ayarı — h.celsius = 37°C
  feat(pipeline): paralel frekans sweep — multiprocessing
  docs(readme): kurulum adımları güncellendi
  refactor(config): magic number'lar defaults.py'e taşındı
  test(analysis): point_source_potential sayısal doğrulama
  chore(gitignore): derleme çıktıları eklendi
```

| Tip | Kullanım |
|:---|:---|
| `fix` | Hata düzeltme |
| `feat` | Yeni özellik |
| `docs` | Yalnızca dokümantasyon |
| `refactor` | Davranış değiştirmeyen yeniden yapılandırma |
| `test` | Test ekleme/güncelleme |
| `chore` | Araç/yapılandırma değişiklikleri |

---

## Python Kodlama Standartları

### Stil
- **PEP 8** — 4 boşluk girinti, maks 100 karakter satır
- Değişken/fonksiyon: `snake_case` | Sınıf: `PascalCase` | Sabit: `UPPER_SNAKE_CASE`
- Magic number yok — tüm sabitler `config/defaults.py`'de

### Docstring Formatı

```python
def fonksiyon(param: float, opsiyonel: int = 10) -> list:
    """
    Tek cümle özet.

    Parametreler
    ------------
    param : float
        Açıklama.
    opsiyonel : int, optional
        Açıklama. Varsayılan 10.

    Döndürür
    --------
    list
        Açıklama.
    """
```

- Türkçe docstring tercih edilir (biyolojik terimler İngilizce kalabilir)
- Her public fonksiyon ve sınıf docstring'e sahip olmalı


## Yapılacaklar - Teorik Kısıt

> Bu bölüm, chatbot'un tek başına çözemeyeceği, literatür araştırması ve
> editör (kullanıcı) yönlendirmesi gerektiren biyolojik/teorik sorunları biriktirir.
> Chatbot bu sorunlar için kendi başına parametre değiştirmez veya "çözüm" uygulamaz;
> önce bu bölüme ekler, ardından editörle tartışır.

### TK-001 — NAc Frekansa Bağımlı İletim Bloku ve Dissociation Mekanizması

**Tarih:** 2026-07-11
**Sorun:** MRG modelinde 100+ Hz'de frekansa bağımlı iletim bloku gözlemleniyor.
200 Hz'de ~40 puls uygulanmasına karşın distal düğümde yalnızca 2 spike kaydediliyor.
Bu durum NAc'ın tasarım gereği gerektirdiği yüksek frekanslı spike akışını engelliyor;
sonuç olarak NAc tüm frekanslarda 0.00 Hz/nöron'da kalıyor.

**Teorik sorular (literatür araştırması gerekiyor):**
- Gerçek VNS deneyleri 20-500 Hz aralığında aksonal iletim bloku gözlemliyor mu?
- MRG modelinin maksimum takip frekansı ne kadar? (orijinal McIntyre 2002 makalesinde belirtilmiş mi?)
- Distal düğüm yerine proximal düğüm (elektrot yakını) spike sayısı kullanmak
  biyolojik olarak daha mı doğru olur?
- NAc aktivasyonu için gerçekten yüksek frekanslı spike akışı mı gerekiyor, yoksa
  başka bir mekanizma mı (volüm iletimi, nöromodülatör salınımı vb.) söz konusu?

**Chatbot'un bekleyeceği yönlendirme:**
Editör literatür tarayıp hangi axon kanalının hangi frekansta blok yaşadığını,
ve NAc dissociation için hangi parametrenin değiştirilmesi gerektiğini belirleyecek.
Ondan sonra chatbot kod tarafını uygular.

### TK-002 — celsius/Q10 Kalibrasyonu (37°C Fizyolojik Sıcaklık)

**Tarih:** 2026-07-11
**Sorun:** `AXNODE.mod` parametreleri (Q10 faktörleri, satır 119-121) NEURON'un
varsayılan sıcaklığı olan 6.3°C için kalibre edilmiş. `h.celsius = 37.0`
set edildiğinde eşik ~50 µA'ya çıkıyor (fizyolojik olarak beklenen ~1-2 µA
yerine) — çünkü 37°C'de Na+ inaktivasyon kapısı (h kapısı) aktivasyon
kapısından (m kapısı) 1.7× daha hızlı kapanıyor (bkz. `TEKNIK_NOTLAR.md`).
`DEFAULT_CELSIUS = 37.0` config'te tanımlı ama kullanılmıyor.

**Teorik sorular (literatür araştırması gerekiyor):**
- McIntyre, Richardson, Grill (2002) orijinal makalesinde 37°C için ayrı
  Q10 referans değerleri veriliyor mu, yoksa yalnızca 6.3°C mi kalibre edilmiş?
- ModelDB 3810 kaynak dosyalarında (varsa) 37°C'ye uyarlanmış bir `.mod`
  varyantı mevcut mu?
- Q10 üslerini (2.2, 2.9, 3.0) veya referans sıcaklıkları (20°C, 36°C)
  yeniden fit etmek mi, yoksa yalnızca eşik ölçeklemesi mi doğru yaklaşım?
- 6.3°C'de çalışmanın sonuçların niteliksel (kalitatif) yorumunu ne kadar
  etkilediği bilinmeli — frekans-yanıt dissociation paternleri sıcaklıktan
  bağımsız mı kalıyor?

**Chatbot'un bekleyeceği yönlendirme:**
Editör ModelDB 3810 kaynağını ve ilgili literatürü inceleyip Q10
parametrelerinin nasıl yeniden fit edileceğini belirleyecek. Bu, biyofizik
kanal modelinin (.mod dosyası) doğrudan değiştirilmesini gerektirdiği için
chatbot kendi başına tahmin etmeyecek.

### TK-003 — CA3 GABAerjik İnhibitör İnternöron Popülasyonu

**Tarih:** 2026-07-11
**Sorun:** `src/network/brain_regions.py::build_ca3_r()` yalnızca eksitatör
rekürrent kolateraller içeriyor (`recurrent_p=0.12`, `recurrent_w=1.0 nS`).
İnhibisyon olmadığı için bu ağırlık kasıtlı olarak düşük tutulmuş —
fonksiyonun docstring'i ve `level23.py::run_full_network()`'ün uyarısı
"Gelecek iyileştirme: GABAerjik inhibitör internöron eklemek" diyor.

**Teorik sorular (literatür araştırması gerekiyor):**
- CA3'te gerçek GABAerjik internöron oranı/bağlantı yoğunluğu nedir
  (örn. PV+ basket hücreleri, hipokampal CA3 mikroçevresi literatürü)?
- İnhibitör popülasyon büyüklüğü, zaman sabiti (tau_m, tau_syn) ve
  sinaptik ağırlık nasıl parametrize edilmeli — feedback mi feedforward mu
  inhibisyon modellenecek?
- İnhibisyon eklendiğinde mevcut `recurrent_w_nS=1.0` değeri artırılabilir mi
  (runaway excitation riski olmadan), yoksa mevcut düşük değer korunup
  yalnızca inhibisyon mu eklenmeli?
- Bu değişiklik CA3'ün frekans-yanıt profilini (orta fasilitasyon +
  rekürrent amplifikasyon) nasıl etkiler — dissociation paternleri bozulur mu?

**Chatbot'un bekleyeceği yönlendirme:**
Editör CA3 inhibisyon literatürünü tarayıp internöron popülasyonu için
biyolojik olarak makul parametre aralıklarını belirleyecek. Bu, yeni bir
biyolojik bileşen (internöron tipi + bağlantı şeması) eklemeyi gerektirdiği
için chatbot kendi başına parametre uydurmayacak.

### TK-004 — Akson–Elektrot Geometri Hizalaması

**Tarih:** 2026-09-09
**Sorun:** Akson koordinatları her zaman z=0'dan başlıyor; elektrotun z konumu
ise sabit bir sayı (`run_level1` varsayılanı z=3000 µm, `config.ELECTRODE_POS`
ise z=5000 µm) ve akson uzunluğuna göre ölçeklenmiyor. Varsayılan 15 düğümde
akson ~10.5 mm olduğu için ikisi de aralık içinde kalıyor; ancak `--n-nodes`
küçültülürse (örn. 5 düğüm → ~3 mm) sabit elektrot konumu aksonun dışına
düşebiliyor ve eşik sessizce tamamen değişiyor.

BUG-004 düzeltilirken ölü `elec_z` parametresi kaldırıldı, ama "aksonu
elektrota göre ortala" seçeneği uygulanmadı — simülasyon sonuçlarını
değiştiren bir geometri kararı olduğu için editör onayı bekliyor.

**Teorik sorular (literatür araştırması gerekiyor):**
- Elektrot aksonun ortasına mı hizalanmalı (akson uzunluğuna göre otomatik),
  yoksa sabit bir anatomik mesafe mi korunmalı (vagus'ta manşet elektrot
  belirli bir noktaya yerleştirilir)?
- `run_level1` (z=3000) ile `config.ELECTRODE_POS` (z=5000) arasındaki fark
  kasıtlı mı, yoksa iki ayrı yerde bağımsız yazılmış bir tutarsızlık mı?
- Elektrot akson aralığının dışına düştüğünde kod uyarı vermeli mi?

**Chatbot'un bekleyeceği yönlendirme:**
Editör hangi hizalama modelinin biyolojik olarak doğru olduğunu belirleyecek;
ondan sonra chatbot kod tarafını uygular.
