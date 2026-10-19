"""
tests/test_sarg04.py
====================
Tests for the rewritten SARG04 protocol (backend/protocols/sarg04.py).

Physics background (Scarani–Acín–Ribordy–Gisin 2004)
------------------------------------------------------
In SARG04 the sifting rule is CONCLUSIVE when:
  (a) Bob measures in the OPPOSITE basis from Alice  (cross-basis), AND
  (b) Bob's outcome is the one that EXCLUDES the "other" state in the
      announced pair.

Worked example: Alice sends |0⟩_Z, announces S0 = {|0⟩_Z, |+⟩_X}.
  - Bob in Z: gets |0⟩ — consistent with both states → INCONCLUSIVE.
  - Bob in X, gets |+⟩: consistent with |+⟩_X → INCONCLUSIVE.
  - Bob in X, gets |−⟩: |+⟩_X gives |−⟩ with prob 0 (orthogonal) →
    excludes |+⟩_X → CONCLUSIVE.  Bob infers alice_bit = 0.

P(conclusive | detected) = P(opposite basis) × P(excluding outcome)
                         = 1/2 × 1/2 = 1/4

Expected sifted/detected ≈ 0.25  (NOT 0.50 as for BB84).

Bob's key bit for conclusive events is alice_bit (from the pair label,
S0→bit 0, S1→bit 1), NOT his raw measurement outcome.
"""

import math
import pytest
import numpy as np

from backend.protocols.sarg04 import run_sarg04
from conftest import make_rng


# ---------------------------------------------------------------------------
# Seed determinism
# ---------------------------------------------------------------------------
class TestDeterminism:
    def test_same_seed(self):
        r1 = run_sarg04(10000, make_rng(55), eta_ch=0.5, e_channel=0.02)
        r2 = run_sarg04(10000, make_rng(55), eta_ch=0.5, e_channel=0.02)
        assert r1["n_sifted"] == r2["n_sifted"]
        assert r1["qber_est"] == r2["qber_est"]

    def test_different_seeds_differ(self):
        r1 = run_sarg04(10000, make_rng(55),  eta_ch=0.5, e_channel=0.02)
        r2 = run_sarg04(10000, make_rng(555), eta_ch=0.5, e_channel=0.02)
        assert r1["n_sifted"] != r2["n_sifted"]


# ---------------------------------------------------------------------------
# Ideal case: eta=1, zero noise, zero dark counts
# ---------------------------------------------------------------------------
class TestIdealSARG04:
    """
    With eta_ch = eta_det = 1, e_channel = 0, dc = 0:
      - Every pulse produces a detection.
      - sifted/detected = P(opposite basis) × P(excluding outcome) ≈ 0.25
      - QBER_est == 0  (no errors)
    """

    TARGET_RATIO = 0.25

    def setup_method(self):
        self.n = 400_000          # large enough for tight 4σ bounds
        self.rng = make_rng(7)
        self.result = run_sarg04(
            self.n, self.rng,
            eta_ch=1.0, eta_det=1.0,
            e_channel=0.0, dc=0.0,
            sample_fraction=0.10, sample_min=100,
        )

    def test_qber_zero(self):
        """Zero noise → QBER_est must be 0."""
        assert self.result["qber_est"] == pytest.approx(0.0, abs=1e-9)

    def test_sifted_over_detected_near_quarter(self):
        """
        sifted/detected ≈ 0.25 ± 4σ.

        n_detected = n_sent (eta=1, no loss).  The conclusive events are
        those where bases differ (Binomial n, 1/2) AND the cross-basis
        outcome is the excluding one (Binomial n_cross, 1/2), which
        jointly give Binomial(n, 1/4).  The 4σ tolerance on the fraction
        is 4 × sqrt(p*(1-p)/n) with p = 0.25.
        """
        ratio   = self.result["sifted_over_detected"]
        n_det   = self.result["n_detected"]
        p       = self.TARGET_RATIO
        std     = math.sqrt(p * (1 - p) / n_det)
        tol     = 4 * std
        assert abs(ratio - p) <= tol, (
            f"sifted/detected = {ratio:.5f}, expected {p} ± {tol:.5f}\n"
            f"n_detected = {n_det}"
        )

    def test_not_aborted(self):
        assert self.result["aborted"] is False

    def test_formula_note_present(self):
        """SARG04 output must always carry the simplified formula note."""
        assert self.result.get("formula_note") == "simplified_BB84_formula"

    def test_sifted_over_detected_not_near_half(self):
        """
        Regression test: the old BB84-style sifting gave ~0.50.
        Confirm the ratio is nowhere near 0.50 (>10σ away).
        """
        ratio = self.result["sifted_over_detected"]
        n_det = self.result["n_detected"]
        p_bb84 = 0.50
        std_bb84 = math.sqrt(p_bb84 * (1 - p_bb84) / n_det)
        distance_sigma = abs(ratio - p_bb84) / std_bb84
        assert distance_sigma > 10, (
            f"sifted/detected = {ratio:.5f} is too close to 0.50 "
            f"({distance_sigma:.1f}σ away, must be >10σ).\n"
            f"The code is reverting to BB84-style sifting."
        )


# ---------------------------------------------------------------------------
# With e_channel = 0.05 (channel errors, no dark counts)
# ---------------------------------------------------------------------------
class TestChannelError:
    """QBER_est ≈ e_channel = 0.05 with large n, no dark counts."""

    def test_qber_near_e_channel(self):
        n = 800_000          # large: n_sifted ≈ n/4 = 200k, n_sampled ≈ 20k
        e = 0.05
        rng = make_rng(12)
        result = run_sarg04(
            n, rng,
            eta_ch=1.0, eta_det=1.0,
            e_channel=e, dc=0.0,
            sample_fraction=0.10, sample_min=200,
        )
        qber_est  = result["qber_est"]
        n_sampled = result["n_sampled"]
        std = math.sqrt(e * (1 - e) / max(n_sampled, 1))
        tol = 4 * std
        assert abs(qber_est - e) <= tol, (
            f"qber_est = {qber_est:.5f}, e_channel = {e}, "
            f"4σ tol = {tol:.5f}, n_sampled = {n_sampled}"
        )


# ---------------------------------------------------------------------------
# SARG04 aborts when QBER >= 0.11
# ---------------------------------------------------------------------------
class TestSARG04Abort:
    def test_abort_at_high_qber(self):
        """e_channel = 0.15 → QBER_est > 0.11 → aborted, key = 0."""
        n = 200_000
        rng = make_rng(8)
        result = run_sarg04(
            n, rng,
            eta_ch=1.0, eta_det=1.0,
            e_channel=0.15, dc=0.0,
            sample_fraction=0.10, sample_min=200,
        )
        assert result["aborted"] is True
        assert result["final_key_length_asymptotic"] == 0
        assert result["final_key_length_finite"] == 0
