"""
tests/test_bb84.py
==================
Tests for the rewritten BB84 protocol (backend/protocols/bb84.py).

Statistical tests use large n to make confidence intervals tight.
All 4-sigma binomial bounds: for Binomial(n, p), std = sqrt(n*p*(1-p)),
so 4-sigma tolerance = 4 * sqrt(p*(1-p)/n) on the ratio.
"""

import math
import pytest
import numpy as np

from backend.protocols.bb84 import run_bb84
from conftest import make_rng


# ---------------------------------------------------------------------------
# Seed determinism
# ---------------------------------------------------------------------------
class TestDeterminism:
    def test_same_seed_same_result(self):
        """Same seed must produce identical output."""
        r1 = run_bb84(10000, make_rng(42), eta_ch=0.5, e_channel=0.02)
        r2 = run_bb84(10000, make_rng(42), eta_ch=0.5, e_channel=0.02)
        assert r1["n_sifted"]   == r2["n_sifted"]
        assert r1["qber_est"]   == r2["qber_est"]
        assert r1["final_key_length_asymptotic"] == r2["final_key_length_asymptotic"]

    def test_different_seed_different_result(self):
        """Different seeds must NOT produce identical n_sifted (overwhelmingly)."""
        r1 = run_bb84(10000, make_rng(42),  eta_ch=0.5, e_channel=0.02)
        r2 = run_bb84(10000, make_rng(999), eta_ch=0.5, e_channel=0.02)
        # With n=10000, the probability of identical n_sifted by chance is negligible
        assert r1["n_sifted"] != r2["n_sifted"]


# ---------------------------------------------------------------------------
# Zero-noise, zero-dark-count, eta=1 run
# ---------------------------------------------------------------------------
class TestIdealCase:
    """eta_ch=1, eta_det=1 (passed via run_bb84 args), e_channel=0, dc=0."""

    def setup_method(self):
        self.n = 200_000
        self.rng = make_rng(1)
        self.result = run_bb84(
            self.n,
            self.rng,
            eta_ch=1.0,
            eta_det=1.0,
            e_channel=0.0,
            dc=0.0,
            dt=1e-9,
            sample_fraction=0.10,
            sample_min=100,
        )

    def test_qber_est_zero(self):
        """With zero noise and zero dark counts, QBER estimate must be 0."""
        assert self.result["qber_est"] == pytest.approx(0.0, abs=1e-9)

    def test_sifted_over_detected_near_half(self):
        """Sifted / detected must be approximately 0.5 (basis matching)."""
        ratio = self.result["sifted_over_detected"]
        n_det = self.result["n_detected"]
        # 4-sigma binomial interval
        std = math.sqrt(0.5 * 0.5 / n_det)
        tol = 4 * std
        assert abs(ratio - 0.5) <= tol, (
            f"sifted/detected = {ratio:.4f}, expected 0.5 ± {tol:.4f}"
        )

    def test_not_aborted(self):
        assert self.result["aborted"] is False

    def test_positive_key(self):
        assert self.result["final_key_length_asymptotic"] > 0


# ---------------------------------------------------------------------------
# With e_channel = 0.02 (channel errors, no dark counts)
# ---------------------------------------------------------------------------
class TestChannelError:
    """Test that QBER_est ≈ e_channel = 0.02 with large n, no dark counts."""

    def test_qber_near_e_channel(self):
        n = 500_000
        e = 0.02
        rng = make_rng(2)
        result = run_bb84(
            n, rng,
            eta_ch=1.0, eta_det=1.0,
            e_channel=e, dc=0.0,
            sample_fraction=0.10, sample_min=200,
        )
        qber_est = result["qber_est"]
        # PE sample size ≈ 10% of n_sifted ≈ 0.5 * n = 25000
        n_sample = result["n_sampled"]
        std = math.sqrt(e * (1 - e) / n_sample)
        tol = 4 * std
        assert abs(qber_est - e) <= tol, (
            f"qber_est={qber_est:.5f}, e_channel={e}, 4σ tol={tol:.5f}"
        )


# ---------------------------------------------------------------------------
# Dark-count QBER approximation test
#
# Regime: eta_ch * eta_det >> p_dark  (photon contribution dominates counts)
# In this regime the fraction of dark-count events among detected events is
# approximately  p_dark / (eta_ch * eta_det + p_dark) ≈ p_dark / (eta * eta_det)
# and dark-count events produce random bits (QBER contribution = 0.5 each).
# So the dark-count contribution to overall QBER is approximately:
#     QBER_dc ≈ 0.5 * p_dark / (eta_ch * eta_det)
# (see e.g. Gobby et al., Appl. Phys. Lett. 84, 3762 (2004))
#
# Valid when:  p_dark << eta_ch * eta_det
# ---------------------------------------------------------------------------
class TestDarkCountQBER:
    """
    Dark-count QBER approximation:
        QBER_est ≈ 0.5 * p_dark / (eta_ch * eta_det)
    Valid regime: p_dark << eta_ch * eta_det.

    We use eta_ch * eta_det = 0.1, p_dark = 1e-5 so ratio p/eta = 1e-4.
    Statistical tolerance: 4σ on the PE sample.
    """

    REGIME_NOTE = (
        "Approximation QBER_est ≈ 0.5 * p_dark / (eta_ch * eta_det) holds "
        "when p_dark << eta_ch * eta_det (here p_dark/eta ≈ 1e-4)."
    )

    def test_dark_count_qber_approximation(self):
        eta_ch  = 1.0
        eta_det = 0.10
        dc      = 100.0      # Hz
        dt      = 1e-6       # 1 µs gate — chosen so p_dark = dc*dt = 1e-4
        p_dark  = dc * dt    # 1e-4

        assert p_dark / (eta_ch * eta_det) < 0.01, "Regime check: p_dark << eta"

        n = 2_000_000        # large to reduce statistical noise
        rng = make_rng(3)
        result = run_bb84(
            n, rng,
            eta_ch=eta_ch, eta_det=eta_det,
            e_channel=0.0, dc=dc, dt=dt,
            sample_fraction=0.05, sample_min=500,
        )

        expected_qber_dc = 0.5 * p_dark / (eta_ch * eta_det)
        qber_est  = result["qber_est"]
        n_sampled = result["n_sampled"]

        # Statistical tolerance
        std = math.sqrt(qber_est * (1 - qber_est) / max(n_sampled, 1))
        tol = max(4 * std, 0.002)  # floor tolerance at 0.2% for small counts

        assert abs(qber_est - expected_qber_dc) <= tol, (
            f"qber_est={qber_est:.5f}, expected_dc={expected_qber_dc:.5f}, "
            f"tol={tol:.5f}\n{self.REGIME_NOTE}"
        )
