"""
tests/test_postprocessing.py
============================
Tests for backend/postprocessing.py
"""

import math
import pytest
import numpy as np

from backend.postprocessing import (
    h2,
    run_postprocessing,
    finite_key_length,
    QBER_ABORT_THRESHOLD,
)
from conftest import make_rng


# ---------------------------------------------------------------------------
# h2 tests
# ---------------------------------------------------------------------------
class TestH2:
    def test_edge_zero(self):
        assert h2(0.0) == 0.0

    def test_edge_one(self):
        assert h2(1.0) == 0.0

    def test_half(self):
        assert abs(h2(0.5) - 1.0) < 1e-12

    def test_symmetric(self):
        for x in [0.1, 0.2, 0.3, 0.4]:
            assert abs(h2(x) - h2(1 - x)) < 1e-12

    def test_out_of_range(self):
        with pytest.raises(ValueError):
            h2(-0.01)
        with pytest.raises(ValueError):
            h2(1.01)


# ---------------------------------------------------------------------------
# Abort rule tests
# ---------------------------------------------------------------------------
class TestAbortRule:
    def _pp(self, qber_est_approx: float, n: int = 50000):
        """Run PP with a synthetic key where QBER matches qber_est_approx."""
        rng = make_rng(0)
        n_errors = int(round(qber_est_approx * n))
        alice = [0] * n
        bob = [1] * n_errors + [0] * (n - n_errors)
        return run_postprocessing(alice, bob, rng, n_raw=n,
                                  sample_fraction=0.10, sample_min=100)

    def test_abort_at_threshold(self):
        """QBER at exactly threshold → aborted, key length 0."""
        result = self._pp(QBER_ABORT_THRESHOLD)
        assert result["aborted"] is True
        assert result["final_key_length_asymptotic"] == 0
        assert result["final_key_length_finite"] == 0

    def test_abort_above_threshold(self):
        """QBER > threshold → aborted, key exactly 0."""
        result = self._pp(0.15)
        assert result["aborted"] is True
        assert result["final_key_length_asymptotic"] == 0

    def test_no_abort_below_threshold(self):
        """QBER well below threshold → not aborted, positive key."""
        result = self._pp(0.02)
        assert result["aborted"] is False
        assert result["final_key_length_asymptotic"] > 0

    def test_key_monotone_in_qber(self):
        """Final key length must be non-increasing as QBER increases."""
        lengths = []
        for q in [0.01, 0.03, 0.05, 0.08, 0.10, 0.11]:
            r = self._pp(q)
            lengths.append(r["final_key_length_asymptotic"])
        for i in range(len(lengths) - 1):
            assert lengths[i] >= lengths[i + 1], (
                f"Key length not monotone: {lengths}"
            )

    def test_aborted_key_exactly_zero(self):
        """When aborted, both key fields must be exactly 0."""
        result = self._pp(0.20)
        assert result["final_key_length_asymptotic"] == 0
        assert result["final_key_length_finite"] == 0
        assert result["aborted"] is True

    def test_no_sifted_bits(self):
        """Empty sifted list → aborted, abort_reason set."""
        rng = make_rng(0)
        result = run_postprocessing([], [], rng, n_raw=1000)
        assert result["aborted"] is True
        assert result["final_key_length_asymptotic"] == 0
        assert result["abort_reason"] == "no_sifted_bits"


# ---------------------------------------------------------------------------
# Same formula for BB84 and SARG04 at identical (n, QBER)
# ---------------------------------------------------------------------------
class TestProtocolFormulaEquality:
    def test_same_formula_bb84_sarg04(self):
        """BB84 and SARG04 with identical sifted data must produce
        identical postprocessing output (except protocol tag and formula_note).
        """
        rng_bb84  = make_rng(77)
        rng_sarg  = make_rng(77)  # same seed → same PE sample

        n = 10000
        qber = 0.05
        n_err = int(round(qber * n))
        alice = [0] * n
        bob   = [1] * n_err + [0] * (n - n_err)

        r_bb84 = run_postprocessing(alice, bob, rng_bb84, protocol="bb84",
                                    n_raw=n, sample_fraction=0.10, sample_min=100)
        r_sarg = run_postprocessing(list(alice), list(bob), rng_sarg,
                                    protocol="sarg04",
                                    n_raw=n, sample_fraction=0.10, sample_min=100)

        # Same seed → same PE sample → same qber_est → same key lengths
        assert r_bb84["final_key_length_asymptotic"] == r_sarg["final_key_length_asymptotic"]
        assert r_bb84["final_key_length_finite"]     == r_sarg["final_key_length_finite"]
        assert r_bb84["qber_est"] == pytest.approx(r_sarg["qber_est"], abs=1e-9)
        # SARG04 must carry the formula note
        assert r_sarg.get("formula_note") == "simplified_BB84_formula"
