"""
tests/test_threshold_finder.py
================================
src/analysis/threshold_finder.py için bilinen giriş/çıkış testleri.

NEURON/Brian2 bağımlılığı yok — find_threshold ve verify_bracket saf
Python fonksiyonlarıdır (run_trial_fn callable olarak enjekte edilir).
"""

import pytest

from src.analysis.threshold_finder import find_threshold, verify_bracket


def _step_trial(threshold=1.0):
    """True eğer amp >= threshold ise (basit monotonik test fonksiyonu)."""
    def trial(amp):
        return amp >= threshold
    return trial


def test_find_threshold_known_value():
    trial = _step_trial(threshold=1.5)
    result = find_threshold(trial, amp_low=0.0, amp_high=5.0, tol=1e-4)
    assert result == pytest.approx(1.5, abs=1e-3)


def test_find_threshold_returns_none_if_hi_never_true():
    trial = _step_trial(threshold=100.0)
    result = find_threshold(trial, amp_low=0.0, amp_high=5.0)
    assert result is None


def test_find_threshold_lo_already_true_returns_lo():
    trial = _step_trial(threshold=0.0)
    result = find_threshold(trial, amp_low=1.0, amp_high=5.0)
    assert result == 1.0


def test_verify_bracket_expands_until_true():
    trial = _step_trial(threshold=3.0)
    bracket = verify_bracket(trial, amp_low=0.0, amp_high=0.5, expand_factor=2.0, max_expansions=10)
    assert bracket is not None
    lo, hi = bracket
    assert not trial(lo)
    assert trial(hi)


def test_verify_bracket_returns_none_if_lo_already_true():
    trial = _step_trial(threshold=0.0)
    bracket = verify_bracket(trial, amp_low=1.0, amp_high=5.0)
    assert bracket is None


def test_verify_bracket_returns_none_if_expansion_insufficient():
    trial = _step_trial(threshold=1e6)
    bracket = verify_bracket(trial, amp_low=0.0, amp_high=1.0, max_expansions=3)
    assert bracket is None
