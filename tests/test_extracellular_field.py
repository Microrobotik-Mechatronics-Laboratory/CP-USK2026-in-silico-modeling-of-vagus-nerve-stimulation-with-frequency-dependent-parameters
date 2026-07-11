"""
tests/test_extracellular_field.py
===================================
src/stim/extracellular_field.py için sayısal doğrulama testleri.

NEURON/Brian2 bağımlılığı yok — point_source_potential ve biphasic_waveform
saf numpy fonksiyonlarıdır.
"""

import numpy as np
import pytest

from src.stim.extracellular_field import point_source_potential, biphasic_waveform


def test_point_source_potential_known_value():
    # V = rho*I / (4*pi*r); r=1cm, rho=300 ohm*cm, I=1 uA
    # elektrot orijinde, ölçüm noktası (10000, 0, 0) um = 1 cm
    v = point_source_potential(10000.0, 0.0, 0.0, elec_pos=(0.0, 0.0, 0.0), current=1.0, rho=300.0)
    expected = (300.0 * 1.0) / (4 * np.pi * 1.0)
    assert v == pytest.approx(expected, rel=1e-9)


def test_point_source_potential_singularity_guard():
    # r=0 (nokta elektrotla çakışıyor) — inf değil, 1e-6 cm ile sınırlanmış olmalı
    v = point_source_potential(0.0, 0.0, 5000.0, elec_pos=(0.0, 0.0, 5000.0), current=1.0)
    assert np.isfinite(v)


def test_point_source_potential_scales_linearly_with_current():
    v1 = point_source_potential(100, 0, 0, elec_pos=(0, 0, 0), current=1.0)
    v2 = point_source_potential(100, 0, 0, elec_pos=(0, 0, 0), current=2.0)
    assert v2 == pytest.approx(2 * v1)


def test_point_source_potential_inverse_distance():
    v_near = point_source_potential(100, 0, 0, elec_pos=(0, 0, 0), current=1.0)
    v_far = point_source_potential(200, 0, 0, elec_pos=(0, 0, 0), current=1.0)
    assert v_far == pytest.approx(v_near / 2, rel=1e-9)


def test_biphasic_waveform_shape():
    t_vec, i_vec = biphasic_waveform(freq_hz=10, amp=2.0, duration_ms=100, dt=0.01)
    assert len(t_vec) == len(i_vec)
    assert t_vec[0] == 0.0


def test_biphasic_waveform_charge_approximately_balanced():
    # Biphasic tasarım: pozitif + negatif faz net yükü ~0'a yakın olmalı.
    # Not: np.arange tabanlı maskeleme kayan nokta sınır etkisi nedeniyle
    # fazlar arasında ±1 örnek farkı üretebilir (100 vs 99 örnek gibi) —
    # bu ayrıklaştırma artefaktıdır, dalga formu hatası değil. Tolerans bu
    # tek-örnek farkını (amp * dt) hesaba katacak şekilde seçildi.
    amp, dt = 2.0, 0.001
    t_vec, i_vec = biphasic_waveform(
        freq_hz=10, amp=amp, duration_ms=100, dt=dt,
        pulse_width_ms=0.1, interphase_gap_ms=0.05,
    )
    total_charge = np.sum(i_vec) * dt
    assert abs(total_charge) <= 2 * amp * dt


def test_biphasic_waveform_sinusoidal_mode():
    t_vec, i_vec = biphasic_waveform(
        freq_hz=1000, amp=1.0, duration_ms=10, dt=0.001, waveform="sinusoidal",
    )
    assert np.max(i_vec) <= 1.0 + 1e-9
    assert np.min(i_vec) >= -1.0 - 1e-9
