"""
backend/controller.py
=====================
Adaptive controller, Fixed controller, and Oracle controller for BB84-LCA QKD.

Interface:
    controller.next_params(history: History) -> BlockParams(p_key, Q_tol, N)

Constraints & Invariants:
1. Pure function of History: identical history produces identical BlockParams.
2. Receives ONLY immutable History of PREVIOUS blocks' PUBLIC statistics.
3. Never receives raw key bits, current-block data, or true channel state.
4. Model-based optimization using TLGR 2012 expected-yield predictor.
5. Hysteresis (dwell time m_dwell, minimum relative gain delta_rel, step limit dp_max).
6. Safe fallback upon block abort or high noise (p_key = 0.5, conservative Q_tol).
7. Warm-up period (first W blocks use p_key = 0.5).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from backend.finite_key import BlockHistoryEntry, BlockParams, Controller, FixedController, History
from backend.yield_model import expected_finite_yield


@dataclass(frozen=True)
class ControllerHyperparams:
    """Hyperparameters for AdaptiveController.

    Tuned strictly on tuning seeds (>= 1000). Evaluation uses seeds 0..S-1.
    """
    W: int = 3  # estimation window in blocks
    delta_ctrl: float = 0.10  # confidence parameter for Hoeffding UCB
    margin: float = 0.008  # Q_tol margin above upper confidence bound (0.8%)
    delta_rel: float = 0.03  # minimum 3% relative yield gain to switch p_key
    m_dwell: int = 1  # consecutive blocks required before switching
    dp_max: float = 0.15  # maximum |Delta p_key| per single block switch
    Q_safe: float = 0.070  # noise threshold above which safe mode is triggered
    Q_safe_tol: float = 0.075  # conservative Q_tol during safe mode
    m_stable: int = 2  # consecutive stable blocks required to exit safe mode
    k_min: int = 50  # minimum expected test bits required for candidate p_key
    default_qtol: float = 0.040  # initial default Q_tol during warm-up


@dataclass
class DecisionRecord:
    """Record of controller internal reasoning for a specific block."""
    block_idx: int
    p_key: float
    Q_tol: float
    N: int
    predicted_yield: float
    reason: str  # 'warm-up', 'safe', 'hysteresis_hold', 'switch', 'stable_hold'
    g_hat: float
    e_test_est: float
    e_test_upper: float
    target_p_key: float


class AdaptiveController(Controller):
    """Model-based adaptive controller with confidence bounds, hysteresis, and safe fallback.

    Purity guarantee:
    State transitions are reconstructed deterministically from the public History,
    guaranteeing that next_params(history) is a pure function of History.
    """

    def __init__(
        self,
        N: int = 2_000_000,
        hyperparams: ControllerHyperparams | None = None,
        grid_step: float = 0.02,
        grid_min: float = 0.50,
        grid_max: float = 0.98,
        protocol_params: Mapping[str, Any] | None = None,
    ):
        self.N = N
        self.hp = hyperparams or ControllerHyperparams()
        self.grid_step = grid_step
        self.grid_min = grid_min
        self.grid_max = grid_max
        self.protocol_params = dict(protocol_params or {})
        self.decision_log: list[DecisionRecord] = []

    def _estimate_channel(self, window_entries: Sequence[BlockHistoryEntry]) -> tuple[float, float, float, float]:
        """Estimate g, e_test, and e_test_upper over a window of public block history.

        Returns: (g_hat, e_key_est, e_test_est, e_test_upper)
        """
        if not window_entries:
            return 0.04, 0.02, 0.02, 0.035

        tot_sent = sum(e.n_sent for e in window_entries)
        tot_det = sum(e.n_detected for e in window_entries)
        g_hat = (tot_det / tot_sent) if tot_sent > 0 else 0.04

        tot_kx = sum(e.sample_size_x for e in window_entries)
        tot_err_x = sum(e.errors_x for e in window_entries)
        e_test_est = (tot_err_x / tot_kx) if tot_kx > 0 else 0.02

        tot_kz = sum(e.sample_size_z for e in window_entries)
        tot_err_z = sum(e.errors_z for e in window_entries)
        e_key_est = (tot_err_z / tot_kz) if tot_kz > 0 else 0.02

        # Hoeffding upper confidence bound for control
        if tot_kx > 0:
            rad = math.sqrt(math.log(1.0 / self.hp.delta_ctrl) / (2.0 * tot_kx))
            e_test_upper = min(0.50, e_test_est + rad)
        else:
            e_test_upper = 0.05

        return g_hat, e_key_est, e_test_est, e_test_upper

    def next_params(self, history: History) -> BlockParams:
        """Compute BlockParams purely from immutable History."""
        current_block = len(history)

        # Replay decision trajectory across history to ensure purity and record decisions
        active_pkey = 0.50
        active_qtol = self.hp.default_qtol
        in_safe_mode = False
        stable_count = 0
        dwell_count = 0
        pending_target_pkey = 0.50
        history_decisions: list[DecisionRecord] = []

        # Iterate from block 0 up to current_block
        for b in range(current_block + 1):
            sub_hist = history[:b]
            if b < self.hp.W:
                # 6. Warm-up
                rec = DecisionRecord(
                    block_idx=b,
                    p_key=0.50,
                    Q_tol=self.hp.default_qtol,
                    N=self.N,
                    predicted_yield=0.0,
                    reason="warm-up",
                    g_hat=0.04,
                    e_test_est=0.02,
                    e_test_upper=0.035,
                    target_p_key=0.50,
                )
                active_pkey = 0.50
                active_qtol = self.hp.default_qtol
                history_decisions.append(rec)
                continue

            # We have at least W blocks
            win = sub_hist[-self.hp.W:]
            g_hat, e_key_est, e_test_est, e_test_upper = self._estimate_channel(win)
            last_entry = sub_hist[-1]

            # 5. Safe Fallback Check
            last_aborted = last_entry.aborted
            high_error = e_test_upper > self.hp.Q_safe

            if in_safe_mode:
                if (not last_aborted) and (not high_error):
                    stable_count += 1
                else:
                    stable_count = 0

                if stable_count >= self.hp.m_stable:
                    # Recovery from safe mode
                    in_safe_mode = False
                    stable_count = 0
                    active_pkey = 0.50
                else:
                    # Remain in safe mode
                    active_pkey = 0.50
                    active_qtol = self.hp.Q_safe_tol
                    history_decisions.append(DecisionRecord(
                        block_idx=b,
                        p_key=0.50,
                        Q_tol=self.hp.Q_safe_tol,
                        N=self.N,
                        predicted_yield=0.0,
                        reason="safe",
                        g_hat=g_hat,
                        e_test_est=e_test_est,
                        e_test_upper=e_test_upper,
                        target_p_key=0.50,
                    ))
                    continue
            else:
                if last_aborted or high_error:
                    # Trigger safe mode!
                    in_safe_mode = True
                    stable_count = 0
                    active_pkey = 0.50
                    active_qtol = self.hp.Q_safe_tol
                    history_decisions.append(DecisionRecord(
                        block_idx=b,
                        p_key=0.50,
                        Q_tol=self.hp.Q_safe_tol,
                        N=self.N,
                        predicted_yield=0.0,
                        reason="safe",
                        g_hat=g_hat,
                        e_test_est=e_test_est,
                        e_test_upper=e_test_upper,
                        target_p_key=0.50,
                    ))
                    continue

            # 2. Candidate Grid & k_min check
            candidate_qtol = min(0.15, e_test_upper + self.hp.margin)
            m_det = g_hat * self.N

            # Grid generation
            num_steps = int(round((self.grid_max - self.grid_min) / self.grid_step)) + 1
            raw_grid = [round(self.grid_min + i * self.grid_step, 2) for i in range(num_steps)]

            # Candidate filtering: subject to k_min expected test count
            candidates = []
            for pk in raw_grid:
                k_test_exp = m_det * ((1.0 - pk) ** 2)
                if k_test_exp >= self.hp.k_min or math.isclose(pk, 0.50, abs_tol=1e-4):
                    candidates.append(pk)

            if not candidates:
                candidates = [0.50]

            # 3. Argmax over expected_finite_yield
            best_target_pk = 0.50
            best_target_yield = -1.0
            yield_map: dict[float, float] = {}

            for pk in candidates:
                y, _ = expected_finite_yield(
                    g=g_hat,
                    e_key=e_key_est,
                    e_test=e_test_upper,
                    N=self.N,
                    p_key=pk,
                    Q_tol=candidate_qtol,
                    params=self.protocol_params,
                )
                yield_map[pk] = y
                if y > best_target_yield:
                    best_target_yield = y
                    best_target_pk = pk

            # Evaluate yield of currently active p_key under same channel conditions
            current_yield, _ = expected_finite_yield(
                g=g_hat,
                e_key=e_key_est,
                e_test=e_test_upper,
                N=self.N,
                p_key=active_pkey,
                Q_tol=candidate_qtol,
                params=self.protocol_params,
            )

            # 4. Hysteresis
            denom = max(current_yield, 1e-7)
            rel_gain = (best_target_yield - current_yield) / denom

            reason = "hysteresis_hold"
            if rel_gain > self.hp.delta_rel and not math.isclose(best_target_pk, active_pkey, abs_tol=1e-3):
                if math.isclose(best_target_pk, pending_target_pkey, abs_tol=1e-3):
                    dwell_count += 1
                else:
                    pending_target_pkey = best_target_pk
                    dwell_count = 1

                if dwell_count >= self.hp.m_dwell:
                    # Execute switch with maximum step clamp dp_max
                    delta_p = best_target_pk - active_pkey
                    if abs(delta_p) > self.hp.dp_max:
                        active_pkey = round(active_pkey + math.copysign(self.hp.dp_max, delta_p), 2)
                    else:
                        active_pkey = best_target_pk
                    active_qtol = candidate_qtol
                    reason = "switch"
                    dwell_count = 0
                else:
                    reason = "hysteresis_hold"
                    active_qtol = candidate_qtol
            else:
                dwell_count = 0
                active_qtol = candidate_qtol
                reason = "stable_hold" if rel_gain <= self.hp.delta_rel else "hysteresis_hold"

            history_decisions.append(DecisionRecord(
                block_idx=b,
                p_key=active_pkey,
                Q_tol=active_qtol,
                N=self.N,
                predicted_yield=yield_map.get(active_pkey, current_yield),
                reason=reason,
                g_hat=g_hat,
                e_test_est=e_test_est,
                e_test_upper=e_test_upper,
                target_p_key=best_target_pk,
            ))

        self.decision_log = history_decisions
        last_decision = history_decisions[-1]
        return BlockParams(p_key=last_decision.p_key, Q_tol=last_decision.Q_tol, N=self.N)


class OracleController(Controller):
    """Oracle controller that knows the true channel parameters for each block.

    Calculates optimal p_key and Q_tol using the same expected-yield predictor,
    without warm-up or estimation uncertainty.
    """

    def __init__(
        self,
        N: int = 2_000_000,
        margin: float = 0.010,
        grid_step: float = 0.02,
        grid_min: float = 0.50,
        grid_max: float = 0.98,
        protocol_params: Mapping[str, Any] | None = None,
    ):
        self.N = N
        self.margin = margin
        self.grid_step = grid_step
        self.grid_min = grid_min
        self.grid_max = grid_max
        self.protocol_params = dict(protocol_params or {})
        self._current_true_g: float = 0.04
        self._current_true_e: float = 0.02

    def set_true_channel_state(self, g: float, e_channel: float):
        """Set the true channel state for the upcoming block."""
        self._current_true_g = g
        self._current_true_e = e_channel

    def next_params(self, history: History) -> BlockParams:
        """Find the optimal p_key for the known true channel state."""
        g = self._current_true_g
        e_ch = self._current_true_e
        Q_tol = e_ch + self.margin

        num_steps = int(round((self.grid_max - self.grid_min) / self.grid_step)) + 1
        raw_grid = [round(self.grid_min + i * self.grid_step, 2) for i in range(num_steps)]

        best_pk = 0.50
        best_yield = -1.0

        for pk in raw_grid:
            y, p_pass = expected_finite_yield(
                g=g,
                e_key=e_ch,
                e_test=e_ch,
                N=self.N,
                p_key=pk,
                Q_tol=Q_tol,
                params=self.protocol_params,
            )
            if y > best_yield:
                best_yield = y
                best_pk = pk

        return BlockParams(p_key=best_pk, Q_tol=Q_tol, N=self.N)
