"""
tests/test_sarg04.py
====================
Exhaustive verification of SARG04 state-exclusion physics and outcome-flip
error model against first-principles analytic derivations.
"""

import math
import numpy as np
import pytest

from backend.protocols.sarg04 import run_sarg04


# ---------------------------------------------------------------------------
# Helper: Analytic Enumeration
# ---------------------------------------------------------------------------
def analytic_sarg04_probabilities(e: float) -> tuple[float, float]:
    """Exhaustive analytic enumeration over all 4 Alice states, 2 Bob bases,
    ideal quantum measurement projections, and outcome-flip noise e.

    Computes:
        P(conclusive | detected)
        QBER = P(error | conclusive)

    Directly derived by summing over the 32 discrete probability branches.
    """
    total_p_conclusive = 0.0
    total_p_error = 0.0

    for b_A in (0, 1):
        for bit_A in (0, 1):
            sigma = (b_A, bit_A)
            tau   = (1 - b_A, 1 - bit_A)
            p_alice = 0.25

            for b_B in (0, 1):
                p_basis = 0.5

                if b_B == b_A:
                    ideal_dist = {bit_A: 1.0, 1 - bit_A: 0.0}
                else:
                    ideal_dist = {0: 0.5, 1: 0.5}

                for ideal_out, p_ideal in ideal_dist.items():
                    if p_ideal == 0:
                        continue

                    # Noise flips outcome with probability e
                    for actual_out, p_flip in ((ideal_out, 1.0 - e), (1 - ideal_out, e)):
                        p_branch = p_alice * p_basis * p_ideal * p_flip

                        perp_sigma = (b_B == sigma[0] and actual_out != sigma[1])
                        perp_tau   = (b_B == tau[0]   and actual_out != tau[1])

                        if perp_tau and not perp_sigma:
                            # Bob excludes tau -> infers sigma -> bit_A (CORRECT)
                            total_p_conclusive += p_branch
                        elif perp_sigma and not perp_tau:
                            # Bob excludes sigma -> infers tau -> 1 - bit_A (ERROR)
                            total_p_conclusive += p_branch
                            total_p_error += p_branch

    qber = (total_p_error / total_p_conclusive) if total_p_conclusive > 0 else 0.0
    return total_p_conclusive, qber


# ---------------------------------------------------------------------------
# Test a: Exhaustive Analytic Enumeration vs Theory Formulas
# ---------------------------------------------------------------------------
class TestAnalyticEnumeration:
    @pytest.mark.parametrize("e", [0.0, 0.02, 0.05, 0.11, 0.15])
    def test_enumeration_matches_formula(self, e):
        """Verify that exhaustive tree enumeration equals 1/4 + e/2 and 2e/(1+2e)."""
        p_concl, qber = analytic_sarg04_probabilities(e)
        expected_p_concl = 0.25 + 0.5 * e
        expected_qber = (2.0 * e) / (1.0 + 2.0 * e)

        assert p_concl == pytest.approx(expected_p_concl, abs=1e-12)
        assert qber == pytest.approx(expected_qber, abs=1e-12)


# ---------------------------------------------------------------------------
# Test b: Monte Carlo Agreement with Analytic Enumeration within 4-sigma
# ---------------------------------------------------------------------------
class TestMonteCarloAgreement:
    @pytest.mark.parametrize("e", [0.0, 0.02, 0.05, 0.11, 0.15])
    def test_mc_agrees_with_analytic(self, e):
        """Monte Carlo with large n (no dark counts) agrees with enumeration within 4σ."""
        n = 600_000
        rng = np.random.default_rng(2024 + int(e * 1000))
        res = run_sarg04(
            n, rng,
            eta_ch=1.0, eta_det=1.0,
            e_channel=e, dc=0.0,
            sample_fraction=0.10, sample_min=100,
        )

        p_concl_expected, qber_expected = analytic_sarg04_probabilities(e)

        # 1. Check P(conclusive | detected) = n_sifted / n_detected
        n_det = res["n_detected"]
        p_concl_meas = res["sifted_over_detected"]
        std_p = math.sqrt(p_concl_expected * (1.0 - p_concl_expected) / n_det)
        tol_p = 4.0 * std_p
        assert abs(p_concl_meas - p_concl_expected) <= tol_p, (
            f"e={e}: P(concl) measured {p_concl_meas:.5f} vs expected {p_concl_expected:.5f} "
            f"(4σ tol = {tol_p:.5f})"
        )

        # 2. Check QBER_est from PE sample
        # Expected QBER is qber_expected
        qber_meas = res["qber_est"]
        n_sample = res["n_sampled"]
        std_q = math.sqrt(qber_expected * (1.0 - qber_expected) / max(n_sample, 1))
        tol_q = 4.0 * std_q
        assert abs(qber_meas - qber_expected) <= tol_q, (
            f"e={e}: QBER measured {qber_meas:.5f} vs expected {qber_expected:.5f} "
            f"(4σ tol = {tol_q:.5f}, n_sample={n_sample})"
        )


# ---------------------------------------------------------------------------
# Test c: Zero Noise, No Dark Counts (QBER == 0, Sifted/Detected == 0.25)
# ---------------------------------------------------------------------------
class TestZeroNoiseIdeal:
    def test_zero_noise(self):
        n = 400_000
        rng = np.random.default_rng(42)
        res = run_sarg04(
            n, rng,
            eta_ch=1.0, eta_det=1.0,
            e_channel=0.0, dc=0.0,
        )
        assert res["qber_est"] == pytest.approx(0.0, abs=1e-9)
        assert res["final_key_length_asymptotic"] > 0
        assert not res["aborted"]

        ratio = res["sifted_over_detected"]
        std = math.sqrt(0.25 * 0.75 / n)
        tol = 4.0 * std
        assert abs(ratio - 0.25) <= tol, f"sifted/detected = {ratio:.5f}, expected 0.25 ± {tol:.5f}"


# ---------------------------------------------------------------------------
# Test d: Dark-Count-Only Regime (QBER Approaches 0.5)
# ---------------------------------------------------------------------------
class TestDarkCountOnlyRegime:
    def test_dark_count_qber_near_half(self):
        """In dark-count-only regime (eta_ch=0), QBER on conclusive events ≈ 0.50."""
        n = 500_000
        rng = np.random.default_rng(1234)
        # eta_ch = 0 means no photons, only dark counts trigger
        res = run_sarg04(
            n, rng,
            eta_ch=0.0, eta_det=1.0,
            e_channel=0.0, dc=1e6, dt=1e-4,  # p_dark = 100 -> clamped by random < 1.0 (all dark counts)
            sample_fraction=0.20, sample_min=100,
        )
        assert res["n_detected"] > 0
        qber = res["qber_est"]
        n_sample = res["n_sampled"]
        std = math.sqrt(0.5 * 0.5 / max(n_sample, 1))
        tol = 4.0 * std
        assert abs(qber - 0.5) <= tol, f"Dark-count QBER = {qber:.4f}, expected 0.50 ± {tol:.4f}"
        assert res["aborted"] is True


# ---------------------------------------------------------------------------
# Test: Reproducibility with RNG seed
# ---------------------------------------------------------------------------
class TestDeterminism:
    def test_same_seed(self):
        r1 = run_sarg04(5000, np.random.default_rng(99), e_channel=0.02)
        r2 = run_sarg04(5000, np.random.default_rng(99), e_channel=0.02)
        assert r1["n_sifted"] == r2["n_sifted"]
        assert r1["final_key_length_asymptotic"] == r2["final_key_length_asymptotic"]
        assert r1["qber_est"] == r2["qber_est"]
