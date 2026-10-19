"""
tests/test_sarg04.py
====================
Tests for the rewritten SARG04 protocol (backend/protocols/sarg04.py).

Key physics to verify:
1. Sifted / detected ≈ 0.50 in the ideal (eta=1, no noise) case.
   Explanation: SARG04 sifting rule keeps events where Bob's basis matches
   Alice's.  Since both draw independently from {Z, X}, the probability
   of a match is 0.5.  Expected sifted/detected = 0.5 ± binomial tolerance.

2. Zero-noise case: QBER_est == 0 (no errors, no dark counts).

3. Seed determinism.
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
    """With eta_ch=eta_det=1, e_channel=0, dc=0:
    - sifted/detected ≈ 0.50 (basis-match sifting)
    - QBER_est == 0
    """

    def setup_method(self):
        self.n = 300_000
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

    def test_sifted_over_detected_near_half(self):
        """sifted/detected ≈ 0.50 ± 4σ for SARG04 (same as BB84 sifting)."""
        ratio = self.result["sifted_over_detected"]
        n_det = self.result["n_detected"]
        std = math.sqrt(0.5 * 0.5 / n_det)
        tol = 4 * std
        assert abs(ratio - 0.50) <= tol, (
            f"sifted/detected = {ratio:.4f}, expected 0.50 ± {tol:.4f}"
        )

    def test_not_aborted(self):
        assert self.result["aborted"] is False

    def test_formula_note_present(self):
        """SARG04 output must always carry the simplified formula note."""
        assert self.result.get("formula_note") == "simplified_BB84_formula"


# ---------------------------------------------------------------------------
# SARG04 abort when QBER >= 0.11
# ---------------------------------------------------------------------------
class TestSARG04Abort:
    def test_abort_at_high_qber(self):
        """e_channel=0.15 → measured QBER > 0.11 → aborted, key = 0."""
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
