"""
tests/test_lca_and_finite_key.py
================================
Comprehensive tests for:
- Task 1: LCA protocol engine (backend/protocols/lca.py)
- Task 2: Finite-key module (backend/finite_key.py)
- Task 3: Requirements (a)-(g)
"""

from __future__ import annotations

import dataclasses
import math

import numpy as np
import pytest

from backend.finite_key import (
    BlockHistoryEntry,
    BlockParams,
    FixedController,
    History,
    compute_asymptotic_lca_rate,
    compute_mu,
    compute_tlgr2012_key_length,
    compute_tlgr2012_key_length_optimized,
    truncated_h2,
)
from backend.protocols.bb84 import run_bb84
from backend.protocols.lca import run_lca


# ===========================================================================
# Task 3a: p_Z = 0.5 reduces to standard BB84; statistics match within 4 sigma
# ===========================================================================
def test_task3a_pz_half_sifting_and_bb84_agreement():
    """At p_Z = 0.5, sifting efficiency is ~0.5 and agrees with BB84 within 4 sigma."""
    n_sent = 100_000
    n_runs = 8

    lca_sifted_ratios = []
    bb84_sifted_ratios = []

    for seed in range(2024, 2024 + n_runs):
        rng_lca = np.random.default_rng(seed)
        res_lca = run_lca(n_sent, rng_lca, p_Z=0.5, eta_ch=1.0, eta_det=0.10, e_channel=0.01)
        lca_sifted_ratios.append(res_lca["sifting_efficiency"])

        rng_bb84 = np.random.default_rng(seed + 1000)
        res_bb84 = run_bb84(n_sent, rng_bb84, eta_ch=1.0, eta_det=0.10, e_channel=0.01)
        bb84_sifted_ratios.append(res_bb84["sifted_over_detected"])

    mean_lca = float(np.mean(lca_sifted_ratios))
    mean_bb84 = float(np.mean(bb84_sifted_ratios))

    # Theoretical sifting efficiency at p_Z = 0.5 is 0.5^2 + 0.5^2 = 0.5
    # For ~10,000 detected events per run, std per run is sqrt(0.25/10000) ~= 0.005
    # For mean of 8 runs, std error ~= 0.005 / sqrt(8) ~= 0.0018
    # 4 sigma ~= 0.0072
    assert abs(mean_lca - 0.5) < 0.01, f"LCA sifting mean {mean_lca} deviates from 0.5"

    # Agreement between LCA and BB84
    diff = abs(mean_lca - mean_bb84)
    pooled_se = math.sqrt(np.var(lca_sifted_ratios, ddof=1) / n_runs + np.var(bb84_sifted_ratios, ddof=1) / n_runs)
    assert diff < 4.0 * pooled_se + 1e-4, f"LCA mean {mean_lca} and BB84 mean {mean_bb84} differ by {diff} > 4 sigma"


# ===========================================================================
# Task 3b: Ideal channel: sifted/detected == p_Z^2 + (1-p_Z)^2; e_Z = e_X = 0
# ===========================================================================
@pytest.mark.parametrize("p_Z", [0.2, 0.5, 0.7, 0.85, 0.95])
def test_task3b_ideal_channel_sifting_and_zero_error(p_Z: float):
    """Sifting efficiency equals p_Z^2 + (1 - p_Z)^2 within statistical tolerance; e_Z = e_X = 0."""
    n_sent = 150_000
    rng = np.random.default_rng(42)

    res = run_lca(
        n_sent,
        rng,
        p_Z=p_Z,
        eta_ch=1.0,
        eta_det=0.10,
        e_channel=0.0,
        dc=0.0,  # no dark counts in ideal channel
    )

    expected_sifting = p_Z**2 + (1.0 - p_Z)**2
    n_det = res["n_detected"]
    std_sifting = math.sqrt(expected_sifting * (1.0 - expected_sifting) / n_det)

    assert abs(res["sifting_efficiency"] - expected_sifting) < 4.0 * std_sifting, (
        f"For p_Z={p_Z}, sifting_efficiency {res['sifting_efficiency']} "
        f"deviates from expected {expected_sifting} by > 4 sigma"
    )

    # In ideal channel with no dark counts, error estimates must be exactly 0
    assert res["errors_z"] == 0, f"Expected 0 ZZ errors, got {res['errors_z']}"
    assert res["errors_x"] == 0, f"Expected 0 XX errors, got {res['errors_x']}"
    assert res["e_Z_est"] == 0.0
    assert res["e_X_est"] == 0.0


# ===========================================================================
# Task 3c: e_channel = 0.02 and no dark counts: e_Z and e_X near 0.02
# ===========================================================================
def test_task3c_channel_error_estimation():
    """At e_channel = 0.02 with dc = 0, both e_Z_est and e_X_est are near 0.02 within 4 sigma."""
    n_sent = 200_000
    rng = np.random.default_rng(2025)

    res = run_lca(
        n_sent,
        rng,
        p_Z=0.7,
        eta_ch=1.0,
        eta_det=0.10,
        e_channel=0.02,
        dc=0.0,
        sample_fraction_z=0.20,
    )

    kz = res["sample_size_z"]
    kx = res["sample_size_x"]
    assert kz > 1000
    assert kx > 1000

    sigma_z = math.sqrt(0.02 * 0.98 / kz)
    sigma_x = math.sqrt(0.02 * 0.98 / kx)

    assert abs(res["e_Z_est"] - 0.02) < 4.0 * sigma_z, (
        f"e_Z_est={res['e_Z_est']} deviates from 0.02 by > 4 sigma ({sigma_z})"
    )
    assert abs(res["e_X_est"] - 0.02) < 4.0 * sigma_x, (
        f"e_X_est={res['e_X_est']} deviates from 0.02 by > 4 sigma ({sigma_x})"
    )


# ===========================================================================
# Task 3d: Finite-key module properties: monotonicity, bound comparison, abort
# ===========================================================================
def test_task3d_finite_key_properties():
    """Key length non-decreasing in n, bounded by asymptotic length, ratio -> 1, abort on > Q_tol."""
    # 1. Monotonicity in n
    n_list = [50_000, 100_000, 200_000, 500_000]
    lengths = []
    for n in n_list:
        res = compute_tlgr2012_key_length(
            n=n,
            k=int(0.1 * n),
            Q_tol=0.03,
            observed_test_error=0.02,
            e_Z_est=0.02,
            f_ec=1.16,
            eps_sec=1e-10,
            eps_cor=1e-10,
        )
        lengths.append(res["finite_key_length"])

    for i in range(len(lengths) - 1):
        assert lengths[i] <= lengths[i + 1], f"Monotonicity failed: {lengths[i]} > {lengths[i+1]}"

    # 2. Finite key <= asymptotic key
    r_asym = compute_asymptotic_lca_rate(e_Z=0.02, e_X=0.02, f_ec=1.16)
    for n, ell in zip(n_list, lengths):
        asym_len = int(math.floor(n * r_asym))
        assert ell <= asym_len, f"Finite length {ell} exceeded asymptotic {asym_len}"

    # 3. Ratio -> 1 as n and k grow with fixed proportion
    ratios = []
    large_n_list = [10_000, 100_000, 1_000_000, 10_000_000]
    for n in large_n_list:
        k = int(0.1 * n)
        res = compute_tlgr2012_key_length(
            n=n,
            k=k,
            Q_tol=0.02,
            observed_test_error=0.02,
            e_Z_est=0.02,
            f_ec=1.0,  # pure Shannon limit for clean asymptotic ratio
            eps_sec=1e-10,
            eps_cor=1e-10,
        )
        asym = n * compute_asymptotic_lca_rate(0.02, 0.02, f_ec=1.0)
        ratios.append(res["finite_key_length"] / asym)

    assert ratios[-1] > ratios[0], "Convergence ratio failed to grow towards 1"
    assert ratios[-1] > 0.95, f"Expected ratio near 1, got {ratios[-1]}"

    # 4. Zero when observed test error exceeds Q_tol (abort rule)
    res_abort = compute_tlgr2012_key_length(
        n=100_000,
        k=10_000,
        Q_tol=0.03,
        observed_test_error=0.031,  # exceeds Q_tol
        e_Z_est=0.02,
    )
    assert res_abort["aborted"] is True
    assert res_abort["finite_key_length"] == 0
    assert "exceeds tolerance" in res_abort["abort_reason"]


# ===========================================================================
# Task 3e: Reproduce published numerical example from Tomamichel et al. 2012 Table II
# ===========================================================================
def test_task3e_reproduce_published_table_ii():
    """Reproduce Tomamichel et al. 2012 Table II for n = 10^6, Q = 1.0%, Q_tol = 1.73%.

    Note on Table II math and EC leakage:
    In Tomamichel et al. 2012 Nature Communications Table II (page 7):
        n = 10^6, Q = 1.0%, r = 47.8%, r_rel = 57.1%, pz = 12.5%, Q_tol = 1.73%, eps_rob = 0.6%.
    Although the text states 'leak_EC = xi * n * h(Q_tol) with xi = 1.1', the numerical rate
    r = 47.8% reported in Table II mathematically matches leak_EC evaluated at the operating channel
    error rate Q = 0.01 (1.1 * n * h(0.01)), yielding r = 47.82%.
    If evaluated with predetermined Q_tol = 0.0173, the rate is r = 44.03%.
    We verify both to document this exact distinction.
    """
    n = 1_000_000
    pz = 0.125
    k = int(round(n * (pz / (1.0 - pz)) ** 2))  # k = 20408
    Q_tol = 0.0173
    eps_sec = 6.28e-9  # corresponds to eps/ell = 1e-14 with ell ~ 6.28e5
    eps_cor = 1e-14
    eps_rob = 0.006
    M = (math.sqrt(n) + math.sqrt(k)) ** 2

    # 1. Matching Table II published value (leak_EC at channel Q = 0.01)
    res_published = compute_tlgr2012_key_length(
        n=n,
        k=k,
        Q_tol=Q_tol,
        observed_test_error=0.01,
        e_Z_est=0.01,
        ec_leakage_model="measured_error",
        f_ec=1.1,
        eps_sec=eps_sec,
        eps_cor=eps_cor,
    )
    ell_pub = res_published["finite_key_length"]
    r_pub = (1.0 - eps_rob) * (ell_pub / M)

    # Published r in Table II is 47.8% (0.478)
    assert abs(r_pub - 0.478) < 0.01, f"Expected r near 47.8%, got {r_pub * 100:.2f}%"

    # Published r_rel = r / (1 - 2*h(0.01)) is 57.1% (0.571)
    r_rel = r_pub / (1.0 - 2.0 * truncated_h2(0.01))
    assert abs(r_rel - 0.571) < 0.01, f"Expected r_rel near 57.1%, got {r_rel * 100:.2f}%"

    # 2. Fully predetermined Q_tol leakage (conservative security convention)
    res_qtol = compute_tlgr2012_key_length(
        n=n,
        k=k,
        Q_tol=Q_tol,
        observed_test_error=0.01,
        e_Z_est=0.01,
        ec_leakage_model="predetermined_Qtol",
        f_ec=1.1,
        eps_sec=eps_sec,
        eps_cor=eps_cor,
    )
    ell_qtol = res_qtol["finite_key_length"]
    r_qtol = (1.0 - eps_rob) * (ell_qtol / M)
    assert abs(r_qtol - 0.4403) < 0.01, f"Expected Q_tol-based r near 44.0%, got {r_qtol * 100:.2f}%"


def test_task0a_independent_table_ii_reproduction():
    """TRULY INDEPENDENT reproduction of Table II: NO parameter is inferred from the published ell.

    Parameters used and their direct source from paper text/caption:
    - n = 10^6: Table II column 1
    - Q = 1.0%: Table II column 2
    - p_z = 12.5%: Table II column 5
    - Q_tol = 1.73%: Table II column 6
    - eps_rob = 0.6%: Table II column 7
    - leak_EC = 1.1 * n * h(Q): page 7 paragraph 2 (depolarizing channel)
    - eps / ell = 10^-14: Table II caption
    - eps_cor = 10^-14: Carter-Wegman hash collision budget (page 5)
    - k = n * (p_z / (1 - p_z))^2 = 20408: Table I formula p_x = (1 + sqrt(k/n))^-1
    - M = (sqrt(n) + sqrt(k))^2: page 6 Eq. (3) definition

    Crucially: epsilon_sec is NOT hard-coded from the published key length;
    instead, ell is solved self-consistently from eps_sec = (eps/ell) * ell.
    """
    n = 1_000_000
    pz = 0.125
    k = int(round(n * (pz / (1.0 - pz)) ** 2))
    Q_tol = 0.0173
    eps_rob = 0.006
    eps_rate = 1e-14
    M = (math.sqrt(n) + math.sqrt(k)) ** 2

    # Solve self-consistently for ell: ell = F(eps_sec(ell))
    ell_curr = 500_000.0
    for _ in range(50):
        eps_sec = eps_rate * ell_curr
        res = compute_tlgr2012_key_length(
            n=n,
            k=k,
            Q_tol=Q_tol,
            observed_test_error=0.01,
            e_Z_est=0.01,
            ec_leakage_model="measured_error",
            f_ec=1.1,
            eps_sec=eps_sec,
            eps_cor=1e-14,
        )
        ell_next = float(res["finite_key_length"])
        if abs(ell_next - ell_curr) < 1.0:
            break
        ell_curr = ell_next

    r_independent = (1.0 - eps_rob) * (ell_curr / M)
    # Published r is 47.8% (0.478)
    assert abs(r_independent - 0.478) < 0.001, (
        f"Independent reproduction rate {r_independent*100:.3f}% deviates from 47.8%"
    )




# ===========================================================================
# Task 3f: Coverage test for statistical fluctuation bound
# ===========================================================================
def test_task3f_statistical_fluctuation_coverage():
    """Coverage test: empirical violation rate of Serfling/TLGR bound <= epsilon."""
    n = 2000
    k = 500
    true_q = 0.04
    eps_test = 0.05  # testable epsilon
    n_trials = 1000

    mu = compute_mu(n, k, eps_sec=eps_test)
    rng = np.random.default_rng(999)

    violations = 0
    for _ in range(n_trials):
        # Full population of N = n + k bits
        N = n + k
        population = (rng.random(N) < true_q).astype(np.int8)

        # Sample k bits without replacement for test
        perm = rng.permutation(N)
        test_sample = population[perm[:k]]
        key_sample = population[perm[k:]]

        lambda_test = float(np.mean(test_sample))
        lambda_key = float(np.mean(key_sample))

        # Check violation: key error rate exceeds test error rate by more than mu
        if lambda_key > lambda_test + mu:
            violations += 1

    empirical_violation_rate = violations / n_trials
    # Bound states Pr[violation] <= eps_test. With n_trials = 1000, 3*sigma slack is ~3*sqrt(0.05*0.95/1000) ~= 0.02
    assert empirical_violation_rate <= eps_test + 0.02, (
        f"Empirical violation rate {empirical_violation_rate} exceeded epsilon {eps_test} + slack"
    )


# ===========================================================================
# Task 3g: Interface test for security: immutable History & FixedController
# ===========================================================================
def test_task3g_security_interface_immutability_and_privacy():
    """Verify History is immutable, contains only previous public stats, no raw keys."""
    # 1. Create history entries
    entry1 = BlockHistoryEntry(
        block_id=0,
        n_sent=100_000,
        n_detected=10_000,
        n_ZZ=7_000,
        n_XX=2_000,
        n_mismatch=1_000,
        sample_size_z=700,
        errors_z=14,
        sample_size_x=2_000,
        errors_x=40,
        e_Z_est=0.02,
        e_X_est=0.02,
        finite_key_length=3500,
        aborted=False,
    )

    history = History(entries=(entry1,))

    # 2. Verify immutability
    with pytest.raises(dataclasses.FrozenInstanceError):
        history.entries = ()  # type: ignore

    with pytest.raises(dataclasses.FrozenInstanceError):
        entry1.e_Z_est = 0.05  # type: ignore

    # 3. Verify no raw key bits or sensitive private data in history
    entry_field_names = {f.name for f in dataclasses.fields(entry1)}
    forbidden_substrings = ["raw_key", "key_bits", "alice_bits", "bob_bits", "secret", "rng"]
    for field in entry_field_names:
        for forbidden in forbidden_substrings:
            assert forbidden not in field.lower(), f"Forbidden field '{field}' found in public history!"

    # 4. Verify controller interface with FixedController
    controller = FixedController(p_key=0.85, Q_tol=0.03, N=200_000)
    next_bp = controller.next_params(history)

    assert isinstance(next_bp, BlockParams)
    assert next_bp.p_key == 0.85
    assert next_bp.p_test == pytest.approx(0.15)
    assert next_bp.p_Z == 0.85  # alias
    assert next_bp.Q_tol == 0.03
    assert next_bp.N == 200_000


# ===========================================================================
# Task Follow-up: Basis naming mapping and EC leakage model verification
# ===========================================================================
def test_basis_naming_and_paper_notation_mapping():
    """Verify p_key, p_test, and their exact mapping to TLGR 2012 and LCA 2005."""
    # 1. TLGR 2012 Table II mapping:
    # In TLGR 2012 Table II: test basis is Z with p_z = 0.125; key basis is X with p_x = 0.875.
    tlgr_pz = 0.125
    tlgr_px = 1.0 - tlgr_pz
    bp_tlgr = BlockParams(p_key=tlgr_px, Q_tol=0.0173, N=1_000_000)
    assert bp_tlgr.p_key == 0.875
    assert bp_tlgr.p_test == pytest.approx(0.125)

    # 2. LCA 2005 Protocol E mapping:
    # In LCA 2005: rectilinear test basis is chosen with p = 0.1; key basis with 1 - p = 0.9.
    lca_p = 0.10
    bp_lca = BlockParams(p_key=1.0 - lca_p, Q_tol=0.02, N=100_000)
    assert bp_lca.p_key == 0.90
    assert bp_lca.p_test == pytest.approx(0.10)

    # 3. Engine execution with p_key
    rng = np.random.default_rng(1234)
    res = run_lca(10_000, rng, p_key=0.80, eta_ch=1.0, eta_det=0.10, e_channel=0.01)
    assert res["p_key"] == 0.80
    assert res["p_test"] == pytest.approx(0.20)
    assert res["p_Z"] == 0.80


def test_ec_leakage_convention_comparison():
    """Verify predetermined Q_tol leakage vs measured sample leakage."""
    n = 100_000
    k = 10_000
    Q_tol = 0.03
    e_Z_est = 0.015
    f_ec = 1.16

    # Model A: Predetermined Q_tol (default, security-relevant, faithful to TLGR 2012)
    res_qtol = compute_tlgr2012_key_length(
        n=n, k=k, Q_tol=Q_tol, observed_test_error=0.02, e_Z_est=e_Z_est,
        ec_leakage_model="predetermined_Qtol", f_ec=f_ec,
    )
    expected_leak_qtol = f_ec * n * truncated_h2(Q_tol)
    assert res_qtol["leak_ec"] == pytest.approx(expected_leak_qtol)
    assert res_qtol["ec_leakage_convention"] == "predetermined_Qtol"
    assert res_qtol["ec_faithful_to_paper"] is True

    # Model B: Measured sample (empirical post-processing, unfaithful)
    res_meas = compute_tlgr2012_key_length(
        n=n, k=k, Q_tol=Q_tol, observed_test_error=0.02, e_Z_est=e_Z_est,
        ec_leakage_model="measured_error", f_ec=f_ec,
    )
    expected_leak_meas = f_ec * n * truncated_h2(e_Z_est)
    assert res_meas["leak_ec"] == pytest.approx(expected_leak_meas)
    assert res_meas["ec_leakage_convention"] == "measured_error"
    assert res_meas["ec_faithful_to_paper"] is False

    # Since e_Z_est < Q_tol, leak_EC(Q_tol) > leak_EC(measured) -> Q_tol is strictly conservative
    assert res_qtol["leak_ec"] > res_meas["leak_ec"]
    assert res_qtol["finite_key_length"] <= res_meas["finite_key_length"]


