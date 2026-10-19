"""
tests/test_channel.py
=====================
Tests for backend/channel.py — specifically the attenuation function.

The attenuation model is:
    eta_ch(L) = 10^(-alpha * L / 10)
with alpha = 0.2 dB/km (telecom fiber standard).

Test distances: 5, 20, 35, 50 km.
"""

import math
import pytest

from backend.channel import attenuation


ALPHA = 0.2  # dB/km


@pytest.mark.parametrize("L_km", [5, 20, 35, 50])
def test_attenuation_formula(L_km: float):
    """eta_ch(L) == 10^(-0.2 * L / 10) for the standard distances."""
    expected = 10 ** (-ALPHA * L_km / 10)
    result   = attenuation(L_km, alpha_db_per_km=ALPHA)
    assert result == pytest.approx(expected, rel=1e-10), (
        f"L={L_km} km: got {result}, expected {expected}"
    )


def test_attenuation_zero_distance():
    assert attenuation(0.0) == pytest.approx(1.0, rel=1e-10)


def test_attenuation_decreases_with_distance():
    vals = [attenuation(L) for L in [0, 5, 10, 20, 35, 50]]
    for i in range(len(vals) - 1):
        assert vals[i] > vals[i + 1], "Attenuation must decrease with distance"


def test_attenuation_positive():
    for L in [0, 1, 10, 100]:
        assert attenuation(L) > 0
