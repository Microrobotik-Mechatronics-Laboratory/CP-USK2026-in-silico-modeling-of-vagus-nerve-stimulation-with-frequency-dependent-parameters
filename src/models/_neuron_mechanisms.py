"""
src/models/_neuron_mechanisms.py
==================================
`mechanisms/` dizininde `nrnivmodl` ile derlenmiş MRG ve Sundt C-fiber
kütüphanesini (libnrnmech) NEURON sürecine yükler.

Derlenmiş kütüphane olmadan `hasattr(h, "axnode")` / `hasattr(h, "nahh")`
her zaman False döner ve modeller sessizce HH fallback'e düşer — bu modül
o sessiz düşüşü önlemek için mekanizmaları açıkça yükler. Kütüphane
bulunamazsa `RuntimeWarning` verir (fd5abff'te düzeltilen sessiz-fallback
hatasının tekrarını önlemek için — bkz. SDLC/TEKNIK_NOTLAR.md).

ASCII olmayan yol sorunu
------------------------
NEURON'un `h.nrn_load_dll()` çağrısı yolu HOC yorumlayıcısına aktarır; HOC
katmanı yalnızca ASCII kabul eder. Proje yolunda Türkçe karakter varsa
(örn. ".../Frekansa Bağlı .../Uygulama") mutlak yolla yükleme
`RuntimeError: 'ascii' codec can't encode character ...` ile başarısız
olur. `_ascii_safe_path()` bu durumda önce göreli yola, o da ASCII değilse
geçici bir ASCII dizindeki sembolik bağlantıya düşer.
"""

import atexit
import glob
import os
import shutil
import tempfile
import warnings

from neuron import h

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_MECHANISMS_DIR = os.path.join(_PROJECT_ROOT, "mechanisms")

_loaded = False


def _ascii_safe_path(path: str) -> str:
    """
    NEURON'un HOC katmanına verilebilecek ASCII bir yol döndürür.

    Sırayla üç yol denenir:
        1. Yol zaten ASCII ise doğrudan döndürülür (tipik kurulum).
        2. Çalışma dizinine göre göreli yol ASCII ise o döndürülür
           (proje kökünden çalıştırıldığında "mechanisms/arm64/libnrnmech.dylib").
        3. Geçici bir ASCII dizinde sembolik bağlantı oluşturulup o döndürülür
           (çalışma dizininden bağımsız son çare; süreç sonunda silinir).

    Parametreler
    ------------
    path : str
        Yüklenecek kütüphanenin mutlak yolu.

    Döndürür
    --------
    str
        ASCII bir yol; sembolik bağlantı da oluşturulamazsa `path`'in kendisi
        (bu durumda NEURON'un kendi hata mesajı görünür olsun diye).

    Notlar
    ------
    Sembolik bağlantının dosya adı `glob` deseninden (`libnrnmech.*`) geldiği
    için her zaman ASCII'dir; yalnızca dizin kısmının ASCII olması yeterlidir.
    """
    if path.isascii():
        return path

    try:
        relative = os.path.relpath(path)
    except ValueError:
        # Farklı sürücü (Windows) — göreli yol kurulamaz.
        relative = None
    if relative is not None and relative.isascii():
        return relative

    try:
        link_dir = tempfile.mkdtemp(prefix="nrnmech_")
        atexit.register(shutil.rmtree, link_dir, True)
        link_path = os.path.join(link_dir, os.path.basename(path))
        os.symlink(path, link_path)
    except OSError as exc:
        warnings.warn(
            f"ASCII olmayan mekanizma yolu için sembolik bağlantı kurulamadı: {exc}. "
            "NEURON yüklemeyi mutlak yolla deneyecek; başarısız olursa projeyi "
            "yalnızca ASCII karakter içeren bir dizine taşıyın.",
            RuntimeWarning,
            stacklevel=3,
        )
        return path
    return link_path


def ensure_mechanisms_loaded() -> None:
    """
    Derlenmiş mekanizma kütüphanesini bir kez yükler.

    `mechanisms/<arch>/libnrnmech.*` dosyasını arar (nrnivmodl'un platforma
    göre oluşturduğu alt dizin: arm64, x86_64, vb.). Bulamazsa açık bir
    `RuntimeWarning` verir — modeller yine de HH fallback ile çalışmaya
    devam eder (bu tasarım gereği geçerli bir yol), ama kullanıcı artık
    sessizce fizyolojik olmayan bir sonuç almaz.

    Yol ASCII olmayan karakter içeriyorsa `_ascii_safe_path()` üzerinden
    HOC'un kabul edeceği bir yola çevrilir.

    NEURON aynı mekanizmayı iki kez yüklemeyi reddettiği için (süreç başına
    bir defa), bu fonksiyon `_loaded` bayrağıyla tekrar denemeyi engeller.
    """
    global _loaded
    if _loaded:
        return
    _loaded = True

    candidates = glob.glob(os.path.join(_MECHANISMS_DIR, "*", "libnrnmech.*"))
    if not candidates:
        warnings.warn(
            "Derlenmiş NEURON mekanizma kütüphanesi bulunamadı "
            f"({_MECHANISMS_DIR}/*/libnrnmech.*). MRGAxon ve CFiber HH "
            "fallback'e düşecek — eşikler ve ileti hızları fizyolojik değil. "
            "Çözüm: `cd mechanisms && nrnivmodl` çalıştırın.",
            RuntimeWarning,
            stacklevel=2,
        )
        return
    h.nrn_load_dll(_ascii_safe_path(candidates[0]))
