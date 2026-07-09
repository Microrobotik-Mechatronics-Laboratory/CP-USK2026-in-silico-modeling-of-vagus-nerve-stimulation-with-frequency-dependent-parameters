"""
src/analysis/threshold_finder.py
==================================
Aktivasyon veya iletim bloğu eşiğini bulan bisection (ikiye bölme) algoritması.

İki mod:
    1. Aktivasyon eşiği (düşük frekans): Minimum akım → spike oluşur mu?
    2. Blok eşiği / KHFAC (yüksek frekans): Minimum akım → iletim bloke olur mu?

Kaynak: nerve_frequency_study_colab.ipynb — Cell 14
"""


def find_threshold(run_trial_fn, amp_low, amp_high, tol=1e-4, max_iter=30):
    """
    Bisection yöntemiyle aktivasyon veya blok eşiğini bulur.

    Algoritma (monoton fonksiyon için):
        1. lo ve hi arasında orta nokta seç: mid = (lo + hi) / 2
        2. mid ile deneme yap (run_trial_fn çağır)
        3. Yanıt True ise: hi = mid (eşik daha düşükte olabilir)
        4. Yanıt False ise: lo = mid (eşik daha yüksekte)
        5. |hi - lo| < tol olana dek tekrarla

    Parametreler
    ------------
    run_trial_fn : callable
        f(amp) → bool şeklinde çağrılabilir bir fonksiyon.
        Aktivasyon modunda: True = spike oluştu.
        Blok modunda: True = iletim bloke edildi.
    amp_low : float
        Aralığın alt sınırı (µA). Bu değerde run_trial_fn False döndürmeli.
    amp_high : float
        Aralığın üst sınırı (µA). Bu değerde run_trial_fn True döndürmeli.
    tol : float, optional
        Yakınsama toleransı (µA). Varsayılan 1e-4 µA.
        30 iterasyonda 2^30 ≈ 10^9 kat daralma sağlanır.
    max_iter : int, optional
        Maksimum iterasyon sayısı. Varsayılan 30.

    Döndürür
    --------
    float or None
        Bulunan eşik değeri (µA).
        None: hi değerinde dahi yanıt alınamadıysa (geçersiz aralık).

    Notlar
    ------
    - Bisection garantili yakınsama sağlar (monoton fonksiyonda).
    - Alternatifler: Newton-Raphson (türev gerektirir, daha hızlı),
      Brent's method (bisection + secant hibrit).
    - verify_bracket() bu fonksiyondan önce çağrılmalıdır.
    """
    lo, hi = amp_low, amp_high

    # Üst sınır kontrolü — hi'da True alınamıyorsa None döndür
    if not run_trial_fn(hi):
        return None
    # Alt sınır kontrolü — lo'da zaten True dönüyorsa lo eşiktir
    if run_trial_fn(lo):
        return lo

    for _ in range(max_iter):
        mid = 0.5 * (lo + hi)
        if run_trial_fn(mid):
            hi = mid
        else:
            lo = mid
        if (hi - lo) < tol:
            break

    return 0.5 * (lo + hi)


def verify_bracket(run_trial_fn, amp_low, amp_high,
                   expand_factor=2.0, max_expansions=10):
    """
    Bisection için geçerli bir aralık doğrular veya oluşturur.

    Bisection'ın çalışması için aralığın bir ucunun True, diğerinin False
    döndürmesi gerekir. Bu fonksiyon, üst sınırı geometrik olarak büyüterek
    uygun aralık arar.

    Parametreler
    ------------
    run_trial_fn : callable
        find_threshold() ile aynı imzalı fonksiyon.
    amp_low : float
        Başlangıç alt sınırı (µA).
    amp_high : float
        Başlangıç üst sınırı (µA).
    expand_factor : float, optional
        Her adımda üst sınırın çarpanı. Varsayılan 2.0 (ikiyle kat).
    max_expansions : int, optional
        Maksimum genişleme adımı. Varsayılan 10 → 2^10 = 1024x genişleme.

    Döndürür
    --------
    tuple(float, float) or None
        (yeni_amp_low, yeni_amp_high): Geçerli bisection aralığı.
        None: max_expansions sonunda geçerli aralık bulunamadı.

    Örnek
    -----
    >>> bracket = verify_bracket(trial_fn, amp_low=0.0, amp_high=1.0)
    >>> if bracket:
    ...     lo, hi = bracket
    ...     threshold = find_threshold(trial_fn, lo, hi)
    """
    lo, hi = amp_low, amp_high

    # Alt sınır kontrolü: lo'da False olmalı
    if run_trial_fn(lo):
        # lo zaten eşiğin üstünde; daha düşük alt sınır gerekiyor
        return None

    # Üst sınır kontrolü: hi'da True alana kadar genişlet
    for _ in range(max_expansions):
        if run_trial_fn(hi):
            return lo, hi
        hi *= expand_factor

    return None  # Aralık bulunamadı
