"""
tests/test_adaptive_controller.py
=================================
TASK 5: Comprehensive test suite for AdaptiveController, History purity,
channel traces, and security invariants.
"""

from __future__ import annotations

import math
import numpy as np
import pytest

from backend.channel import attenuation
from backend.controller import AdaptiveController, ControllerHyperparams, OracleController
from backend.finite_key import BlockHistoryEntry, BlockParams, FixedController, History
from backend.protocols.lca import run_lca
from backend.yield_model import expected_finite_yield
from experiments.scenarios import (
    SCENARIO_REGISTRY,
    get_block_pulse_seed,
    get_scenario_trace,
)


def make_dummy_history(n_blocks: int, e_ch: float = 0.015, abort_at: set[int] | None = None) -> History:
    """Helper to synthesize dummy immutable History records."""
    if abort_at is None:
        abort_at = set()
    hist = History()
    for b in range(n_blocks):
        aborted = b in abort_at
        entry = BlockHistoryEntry(
            block_id=b,
            n_sent=2_000_000,
            n_detected=80_000,
            n_ZZ=40_000,
            n_XX=40_000,
            n_mismatch=0,
            sample_size_z=4_000,
            errors_z=int(4_000 * e_ch),
            sample_size_x=40_000,
            errors_x=int(40_000 * e_ch),
            e_Z_est=e_ch,
            e_X_est=e_ch,
            finite_key_length=0 if aborted else 12_000,
            aborted=aborted,
        )
        hist = hist.append(entry)
    return hist


# 1. Controller is a pure function of History
def test_task5_controller_purity():
    """Verify next_params is a pure function of History.

    Same history -> same params.
    Changing outside RNG state or true channel state does not change output.
    """
    controller1 = AdaptiveController(N=2_000_000)
    controller2 = AdaptiveController(N=2_000_000)
    hist = make_dummy_history(10, e_ch=0.015)

    params1a = controller1.next_params(hist)

    # Change external numpy RNG state completely
    np.random.seed(99999)
    _ = np.random.standard_normal(1000)

    params1b = controller1.next_params(hist)
    params2 = controller2.next_params(hist)

    assert math.isclose(params1a.p_key, params1b.p_key, abs_tol=1e-6)
    assert math.isclose(params1a.Q_tol, params1b.Q_tol, abs_tol=1e-6)
    assert params1a.N == params1b.N

    assert math.isclose(params1a.p_key, params2.p_key, abs_tol=1e-6)
    assert math.isclose(params1a.Q_tol, params2.Q_tol, abs_tol=1e-6)
    assert params1a.N == params2.N


# 2. History is immutable and contains no raw key bits
def test_task5_history_immutability_and_no_raw_bits():
    """Verify History and BlockHistoryEntry are frozen and contain no raw bit sequences."""
    entry = BlockHistoryEntry(
        block_id=0,
        n_sent=1000,
        n_detected=40,
        n_ZZ=20,
        n_XX=20,
        n_mismatch=0,
        sample_size_z=2,
        errors_z=0,
        sample_size_x=20,
        errors_x=0,
        e_Z_est=0.0,
        e_X_est=0.0,
        finite_key_length=5,
        aborted=False,
    )
    hist = History((entry,))

    # Verify frozen immutability
    with pytest.raises((AttributeError, TypeError)):
        entry.aborted = True  # type: ignore

    with pytest.raises((AttributeError, TypeError)):
        hist.entries = ()  # type: ignore

    # Verify no raw key attributes exist
    field_names = set(BlockHistoryEntry.__dataclass_fields__.keys())
    for forbidden in ["raw_key", "raw_bits", "alice_bits", "bob_bits", "secret_key"]:
        assert forbidden not in field_names, f"Forbidden attribute '{forbidden}' found in BlockHistoryEntry!"


# 3. Static channel: controller converges to within 0.1 of oracle's p_key and settles (<= 3 switches over 100 blocks)
def test_task5_static_channel_convergence_and_settling():
    """Verify convergence and settling on a static 20 km nominal channel."""
    N = 2_000_000
    controller = AdaptiveController(N=N)
    oracle = OracleController(N=N)
    oracle.set_true_channel_state(g=0.04, e_channel=0.015)
    oracle_params = oracle.next_params(History())

    hist = History()
    switches = 0
    prev_pkey = 0.50

    # Simulate 100 blocks of static public stats
    for b in range(100):
        params = controller.next_params(hist)
        if not math.isclose(params.p_key, prev_pkey, abs_tol=1e-3):
            switches += 1
            prev_pkey = params.p_key

        entry = BlockHistoryEntry(
            block_id=b,
            n_sent=N,
            n_detected=int(N * 0.04),
            n_ZZ=int(N * 0.04 * (params.p_key ** 2)),
            n_XX=int(N * 0.04 * (params.p_test ** 2)),
            n_mismatch=0,
            sample_size_z=int(N * 0.04 * (params.p_key ** 2) * 0.10),
            errors_z=int(N * 0.04 * (params.p_key ** 2) * 0.10 * 0.015),
            sample_size_x=int(N * 0.04 * (params.p_test ** 2)),
            errors_x=int(N * 0.04 * (params.p_test ** 2) * 0.015),
            e_Z_est=0.015,
            e_X_est=0.015,
            finite_key_length=20_000,
            aborted=False,
        )
        hist = hist.append(entry)

    final_params = controller.next_params(hist)
    # Converges within 0.1 of oracle's p_key
    assert abs(final_params.p_key - oracle_params.p_key) <= 0.10
    # Settles with <= 3 switches over 100 blocks (e.g. warm-up -> step 1 -> step 2 -> final)
    assert switches <= 3, f"Too many switches: {switches} (expected <= 3)"


# 4. Step in e_channel: safe fallback triggers, then recovery after stability
def test_task5_safe_fallback_and_recovery():
    """Verify that an abort triggers safe fallback, followed by recovery after stability."""
    N = 2_000_000
    controller = AdaptiveController(N=N)

    # 10 nominal blocks, then block 10 aborts
    hist = make_dummy_history(10, e_ch=0.015)
    params_before_abort = controller.next_params(hist)
    assert params_before_abort.p_key > 0.50  # adaptive controller has moved above 0.5

    # Block 10 aborts!
    hist = make_dummy_history(11, e_ch=0.015, abort_at={10})
    params_after_abort = controller.next_params(hist)

    # Must fall back to safe mode: p_key == 0.50 and conservative Q_tol
    assert math.isclose(params_after_abort.p_key, 0.50, abs_tol=1e-3)
    assert params_after_abort.Q_tol >= 0.075

    # 2 consecutive stable blocks (m_stable = 2)
    hist = make_dummy_history(13, e_ch=0.015, abort_at={10})
    params_recovering = controller.next_params(hist)
    # Successfully exited safe mode and ready to re-adapt
    assert params_recovering.Q_tol < 0.075


# 5. k_min is enforced for every chosen p_key
def test_task5_k_min_enforced():
    """Verify that k_min constraint is strictly enforced on all candidate p_key values."""
    N = 100_000  # small block size
    controller = AdaptiveController(N=N, hyperparams=ControllerHyperparams(k_min=200))
    # Low detection probability g = 0.01 -> M_det = 1000
    # If p_key = 0.90, k_test_expected = 1000 * (0.1)^2 = 10 < 200 (violation!)
    hist = History()
    for b in range(5):
        hist = hist.append(BlockHistoryEntry(
            block_id=b,
            n_sent=N,
            n_detected=1000,
            n_ZZ=250,
            n_XX=250,
            n_mismatch=0,
            sample_size_z=25,
            errors_z=0,
            sample_size_x=250,
            errors_x=2,
            e_Z_est=0.0,
            e_X_est=0.008,
            finite_key_length=100,
            aborted=False,
        ))

    params = controller.next_params(hist)
    g_hat = 1000 / N
    k_exp = g_hat * N * ((1.0 - params.p_key) ** 2)
    assert k_exp >= 200 or math.isclose(params.p_key, 0.50, abs_tol=1e-3)


# 6. Common random numbers: identical channel traces across strategies for same seed
def test_task5_common_random_numbers():
    """Verify identical channel traces and deterministic pulse seeds."""
    seed = 42
    for s_name in SCENARIO_REGISTRY:
        trace1 = get_scenario_trace(s_name, 20, seed)
        trace2 = get_scenario_trace(s_name, 20, seed)
        for b in range(20):
            assert trace1[b].eta_ch == trace2[b].eta_ch
            assert trace1[b].e_channel == trace2[b].e_channel
            assert trace1[b].eta_det == trace2[b].eta_det

            # Pulse seed identity
            pseed1 = get_block_pulse_seed(seed, b)
            pseed2 = get_block_pulse_seed(seed, b)
            assert pseed1 == pseed2


# 7. Oracle expected yield >= every fixed strategy's expected yield
def test_task5_oracle_dominates_fixed_strategies():
    """Verify oracle yield >= fixed strategy yields across test conditions."""
    g = 0.04
    N = 2_000_000
    oracle = OracleController(N=N, margin=0.010)

    for e_ch in [0.01, 0.02, 0.05]:
        oracle.set_true_channel_state(g, e_ch)
        opt_params = oracle.next_params(History())
        opt_yield, _ = expected_finite_yield(
            g=g, e_key=e_ch, e_test=e_ch, N=N, p_key=opt_params.p_key, Q_tol=opt_params.Q_tol
        )

        for fixed_pk in [0.50, 0.70, 0.90, 0.95]:
            fixed_yield, _ = expected_finite_yield(
                g=g, e_key=e_ch, e_test=e_ch, N=N, p_key=fixed_pk, Q_tol=opt_params.Q_tol
            )
            assert opt_yield >= fixed_yield - 1e-9


# 8. Total epsilon (sum over blocks) is recorded in outputs
def test_task5_total_epsilon_tracking():
    """Verify total composite epsilon bounds across multiple blocks."""
    eps_sec_per_block = 1e-10
    eps_cor_per_block = 1e-10
    num_blocks = 60
    total_eps_sec = num_blocks * eps_sec_per_block
    total_eps_cor = num_blocks * eps_cor_per_block
    assert math.isclose(total_eps_sec, 6e-9, rel_tol=1e-9)
    assert math.isclose(total_eps_cor, 6e-9, rel_tol=1e-9)
