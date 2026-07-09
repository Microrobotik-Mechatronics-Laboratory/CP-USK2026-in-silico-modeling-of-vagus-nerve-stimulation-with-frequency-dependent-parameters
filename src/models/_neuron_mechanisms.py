"""
src/models/_neuron_mechanisms.py
==================================
`mechanisms/` dizininde `nrnivmodl` ile derlenmiş MRG ve Sundt C-fiber
kütüphanesini (libnrnmech) NEURON sürecine yükler.

Derlenmiş kütüphane olmadan `hasattr(h, "axnode")` / `hasattr(h, "nahh")`
her zaman False döner ve modeller sessizce HH fallback'e düşer — bu modül
o sessiz düşüşü önlemek için mekanizmaları açıkça yükler.
"""

import glob
import os

from neuron import h

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_MECHANISMS_DIR = os.path.join(_PROJECT_ROOT, "mechanisms")

_loaded = False


def ensure_mechanisms_loaded():
    """
    Derlenmiş mekanizma kütüphanesini bir kez yükler.

    `mechanisms/<arch>/libnrnmech.*` dosyasını arar (nrnivmodl'un platforma
    göre oluşturduğu alt dizin: arm64, x86_64, vb.). Bulamazsa sessizce
    çıkar — modeller HH fallback kullanır.

    NEURON aynı mekanizmayı iki kez yüklemeyi reddettiği için (süreç başına
    bir defa), bu fonksiyon `_loaded` bayrağıyla tekrar denemeyi engeller.
    """
    global _loaded
    if _loaded:
        return
    _loaded = True

    candidates = glob.glob(os.path.join(_MECHANISMS_DIR, "*", "libnrnmech.*"))
    if not candidates:
        return
    h.nrn_load_dll(candidates[0])
