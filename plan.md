# Proje Planı — Periferik Sinir Stimülasyonu Frekans Çalışması

Bu plan, `nerve_frequency_study_colab.ipynb` notebook'unu modüler, çalıştırılabilir
ve sürdürülebilir bir Python projesine dönüştürme yol haritasını içerir.

---

## Faz 1 — Notebook'u Modüler Yapıya Bölme ✅

**Amaç:** Notebook hücrelerini mantıksal sınırlarına göre ayrı Python dosyalarına
taşımak. Bu aşamada kaynak koda **dokunulmaz**; yalnızca kopyalanır ve organize edilir.

**Yapılacaklar:**
- Her notebook hücresini uygun modüle taşı (`src/stim/`, `src/models/`, vb.)
- Tüm dağınık sabit parametreleri `config/defaults.py` altında topla
- Modüller arası `import` bağlantılarını kur
- `main.py` dosyası oluştur: argparse ile CLI arayüzü
  - Kullanılan parametreler hızlıca komut satırından verilebilsin:
    frekanslar, genlik, fiber çapı, düğüm sayısı, fiber demeti büyüklüğü, çıktı dosyası vb.
- `README.md` dosyası oluştur: kurulum, kullanım, dizin yapısı

**Durum:** ✅ Tamamlandı (9 commit, push edildi)

---

## Faz 2 — Birleştirme ve Çalıştırma Denemesi ⬜

**Amaç:** Faz 1'de ayrıştırılan modülleri `main.py` üzerinden birleştirip
gerçek bir simülasyon çalıştırmak.

**Yapılacaklar:**
- `python main.py --frequencies 20 --amp 1.0` komutunu başarıyla çalıştır
- MRG ve Sundt `.mod` mekanizma dosyalarını `nrnivmodl` ile derle
  - `mechanisms/` dizininde 9 `.mod` dosyası mevcut (indirildi, derlenmedi)
  - Engel: `.venv` yolundaki boşluk `make`'i bozuyor → boşluksuz dizinde venv oluştur
- Level 1 → Level 2 → Level 3 zincirini uçtan uca çalıştır
- Çıktıların mantıklı olup olmadığını kontrol et (spike sayıları, ateşleme hızları)

**Beklenen çıktı:**
```
Frekans: 20 Hz → axon spikes: N
NTS=X.XX  NAc=X.XX  Insula=X.XX  CA3=X.XX  Hz/nöron
```

**Engeller (bilinen):**
- MRG mekanizması derlenmezse HH fallback aktif (sonuçlar kalitatif)

---

## Faz 3 — Sorunlu Kısımları Tespit Et ve Düzelt ⬜

**Amaç:** Faz 2'de çalışmayan veya yanlış sonuç veren kısımları bul ve düzelt.

**Yapılacaklar:**
- Hata mesajlarını analiz et, kök nedeni belirle
- Bilinen eksik/hatalı noktaları incele:
  - `connect_region` fonksiyonu notebook'ta tanımsız (şu an `_connect_region` ile geçici çözüm)
  - `borgkdr` mekanizması eksik → Sundt CFiber HH fallback'e düşüyor
  - Brian2'nin `start_scope()` ile global state yönetimi
- Faz 2'den gelen yeni hataları da buraya ekle
- Her düzeltme ayrı commit ile kayıt altına alın

---

## Faz 4 — Kod Kalitesi, Verimlilik ve Dokümantasyon ⬜

**Amaç:** Çalışan kodu daha okunabilir, verimli ve akademik standartlara uygun hale getir.

**Yapılacaklar:**

### Kod Kalitesi
- Tekrarlanan kod bloklarını tek bir fonksiyona topla (DRY prensibi)
- Tip ipuçları (`type hints`) ekle — `mypy` ile doğrula
- Magic number'ları `config/defaults.py`'e taşı (kalan varsa)
- Hata yönetimini güçlendir (`try/except`, açıklayıcı hata mesajları)

### Verimlilik
- Çoklu frekans çalıştırmasını paralel hale getir (`multiprocessing` veya `joblib`)
- Brian2 simülasyonlarında gereksiz `start_scope()` çağrılarını optimize et
- Sonuçları önbellekle (aynı parametrelerle tekrar simülasyon yapılmasın)

### Dokümantasyon
- Her modüle Türkçe/İngilizce detaylı docstring ekle
- `eski_kod_tutorial.md`'yi kaynak olarak kullanarak her algoritmanın biyolojik
  arka planını açıklayan yorumlar ekle
- Jupyter notebook'a bağlantı veren çapraz referanslar koy
- `CHANGELOG.md` oluştur (Faz 1-4 değişiklik geçmişi)
- Akademik referansları `REFERENCES.md` dosyasında topla

### Test
- Temel birim testleri yaz (`pytest`):
  - `point_source_potential` için sayısal doğrulama
  - `find_threshold` için bilinen giriş/çıkış çiftleri
  - `cycles_to_duration_ms` için sınır değerleri

---

## Genel Notlar

> [!NOTE]
> Her faz kendi commit grubuyla Git'e eklenir. Bu sayede herhangi bir faza
> geri dönmek veya değişiklikleri geri almak mümkündür.

> [!IMPORTANT]
> Faz 2 ve 3, `nrnivmodl` derleme sorununun çözülmesine bağlıdır.
> MRG mekanizması olmadan HH fallback ile kalitatif sonuçlar alınabilir,
> ama kantitatif doğruluk için gerçek MRG mekanizması gereklidir.

> [!TIP]
> Faz 4'e geçmeden önce Faz 3'ün tamamen bitmesi önerilir.
> Çalışmayan kod üzerine dokümantasyon eklemek zaman kaybıdır.

---

## Özet Tablo

| Faz | Amaç | Durum |
|:---:|:---|:---:|
| **1** | Notebook → modüler Python yapısı + CLI (`main.py`) | ✅ Tamamlandı |
| **2** | Modülleri birleştirip `main.py` ile çalıştırma | ⬜ Bekliyor |
| **3** | Sorunlu kısımları tespit et ve düzelt | ⬜ Bekliyor |
| **4** | Kod kalitesi, verimlilik, dokümantasyon | ⬜ Bekliyor |
