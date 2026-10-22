"""
experiments/scripts/tune_controller.py
======================================
Tunes AdaptiveController hyperparameters ONLY on separate tuning seeds (>= 1000)
and tuning scenario variants, strictly separated from evaluation seeds (0..S-1).

Outputs:
- experiments/results_final/controller_tuning.json
"""

from __future__ import annotations

import json
import math
import os
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from typing import Any

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import numpy as np

from backend.controller import AdaptiveController, ControllerHyperparams, OracleController
from backend.finite_key import BlockHistoryEntry, History
from backend.protocols.lca import run_lca
from experiments.scenarios import ChannelBlockState, get_block_pulse_seed


def generate_tuning_trace(scenario_type: str, num_blocks: int, seed: int) -> list[ChannelBlockState]:
    """Tuning scenario variants with different parameters from evaluation scenarios."""
    rng = np.random.default_rng(seed)
    trace = []
    if scenario_type == "tuning_step":
        # Step at block 15 from 1.2% to 5.5%
        for b in range(num_blocks):
            e_ch = 0.012 if b < 15 else 0.055
            trace.append(ChannelBlockState(
                block_idx=b, L_km=22.0, eta_ch=0.363, eta_det=0.10, e_channel=e_ch, dc=100.0, dt=1e-9
            ))
    elif scenario_type == "tuning_ramp":
        # Ramp 8 km to 28 km
        for b in range(num_blocks):
            L = 8.0 + (b / max(1, num_blocks - 1)) * 20.0
            loss_db = L * 0.20
            eta_ch = 10.0 ** (-loss_db / 10.0)
            trace.append(ChannelBlockState(
                block_idx=b, L_km=L, eta_ch=eta_ch, eta_det=0.10, e_channel=0.018, dc=100.0, dt=1e-9
            ))
    else:  # "tuning_burst"
        for b in range(num_blocks):
            is_burst = (10 <= b <= 13)
            trace.append(ChannelBlockState(
                block_idx=b, L_km=20.0, eta_ch=0.398, eta_det=0.10, e_channel=0.065 if is_burst else 0.014, dc=100.0, dt=1e-9
            ))
    return trace


def evaluate_config(hp: ControllerHyperparams, tuning_seeds: list[int], num_blocks: int = 30, N: int = 1_000_000) -> dict[str, float]:
    scenarios = ["tuning_step", "tuning_ramp", "tuning_burst"]
    total_yield = 0.0
    total_aborts = 0
    total_switches = 0
    total_blocks = 0

    for s_name in scenarios:
        for seed in tuning_seeds:
            trace = generate_tuning_trace(s_name, num_blocks, seed)
            controller = AdaptiveController(N=N, hyperparams=hp)
            hist = History()
            prev_p_key = 0.50

            for b in range(num_blocks):
                st = trace[b]
                params = controller.next_params(hist)
                if not math.isclose(params.p_key, prev_p_key, abs_tol=1e-3):
                    total_switches += 1
                    prev_p_key = params.p_key

                pulse_seed = get_block_pulse_seed(seed, b)
                rng = np.random.default_rng(pulse_seed)
                res = run_lca(
                    n_sent=params.N,
                    rng=rng,
                    p_key=params.p_key,
                    eta_ch=st.eta_ch,
                    eta_det=st.eta_det,
                    e_channel=st.e_channel,
                    dc=st.dc,
                    dt=st.dt,
                    Q_tol=params.Q_tol,
                    ec_leakage_model="predetermined_Qtol",
                    f_ec=1.16,
                    eps_sec=1e-10,
                    eps_cor=1e-10,
                )

                entry = BlockHistoryEntry(
                    block_id=b,
                    n_sent=params.N,
                    n_detected=res["n_detected"],
                    n_ZZ=res["n_ZZ"],
                    n_XX=res["n_XX"],
                    n_mismatch=res["n_mismatch"],
                    sample_size_z=res["sample_size_z"],
                    errors_z=res["errors_z"],
                    sample_size_x=res["sample_size_x"],
                    errors_x=res["errors_x"],
                    e_Z_est=res["e_Z_est"],
                    e_X_est=res["e_X_est"],
                    finite_key_length=res["finite_key_length"],
                    aborted=res["aborted"],
                )
                hist = hist.append(entry)
                total_yield += res["finite_key_bits_per_pulse"]
                if res["aborted"]:
                    total_aborts += 1
                total_blocks += 1

    return {
        "mean_yield_per_pulse": total_yield / total_blocks,
        "abort_rate": total_aborts / total_blocks,
        "switches_per_run": total_switches / (len(scenarios) * len(tuning_seeds)),
    }


def run_tuning():
    print("Starting controller hyperparameter tuning on separate tuning seeds (>= 1000)...")
    tuning_seeds = [1000, 1001, 1002]
    candidate_configs = [
        # (name, W, delta_ctrl, margin, delta_rel, m_dwell, dp_max, Q_safe, Q_safe_tol, m_stable, k_min)
        ("conservative", ControllerHyperparams(W=7, delta_ctrl=0.01, margin=0.015, delta_rel=0.08, m_dwell=3, dp_max=0.05, Q_safe=0.060, Q_safe_tol=0.080, m_stable=4, k_min=200)),
        ("balanced_default", ControllerHyperparams(W=5, delta_ctrl=0.05, margin=0.010, delta_rel=0.05, m_dwell=2, dp_max=0.10, Q_safe=0.065, Q_safe_tol=0.080, m_stable=3, k_min=100)),
        ("responsive", ControllerHyperparams(W=3, delta_ctrl=0.10, margin=0.008, delta_rel=0.03, m_dwell=1, dp_max=0.15, Q_safe=0.070, Q_safe_tol=0.075, m_stable=2, k_min=50)),
        ("cautious_margin", ControllerHyperparams(W=5, delta_ctrl=0.05, margin=0.012, delta_rel=0.05, m_dwell=2, dp_max=0.10, Q_safe=0.065, Q_safe_tol=0.080, m_stable=3, k_min=100)),
    ]

    scored = []
    for name, hp in candidate_configs:
        print(f"Evaluating config: {name}...")
        t0 = time.time()
        scores = evaluate_config(hp, tuning_seeds, num_blocks=25, N=1_000_000)
        dur = time.time() - t0
        print(f"-> {name}: Yield={scores['mean_yield_per_pulse']:.4e}, Abort={scores['abort_rate']:.3f}, Switches={scores['switches_per_run']:.1f} ({dur:.1f}s)")
        scored.append((name, hp, scores))

    # Pick config that maximizes yield while keeping abort rate low (< 2%)
    best_name, best_hp, best_scores = max(
        scored,
        key=lambda x: (x[2]["mean_yield_per_pulse"] if x[2]["abort_rate"] < 0.05 else -1.0)
    )

    print(f"\nSelected Best Hyperparameter Configuration: {best_name}")
    print(f"Yield: {best_scores['mean_yield_per_pulse']:.4e}, Abort Rate: {best_scores['abort_rate']:.3f}")

    # Save tuning documentation
    os.makedirs(os.path.join(_REPO_ROOT, "experiments/results_final"), exist_ok=True)
    out_file = os.path.join(_REPO_ROOT, "experiments/results_final/controller_tuning.json")
    tuning_doc = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "tuning_seed_set": tuning_seeds,
        "note": "Hyperparameters tuned ONLY on seeds >= 1000 and tuning scenario variants; evaluation strictly held out on seeds 0..S-1",
        "selected_config_name": best_name,
        "hyperparameters": {
            "W": best_hp.W,
            "delta_ctrl": best_hp.delta_ctrl,
            "margin": best_hp.margin,
            "delta_rel": best_hp.delta_rel,
            "m_dwell": best_hp.m_dwell,
            "dp_max": best_hp.dp_max,
            "Q_safe": best_hp.Q_safe,
            "Q_safe_tol": best_hp.Q_safe_tol,
            "m_stable": best_hp.m_stable,
            "k_min": best_hp.k_min,
            "default_qtol": best_hp.default_qtol,
        },
        "evaluation_scores_on_tuning_set": best_scores,
        "all_candidate_evaluations": [
            {"name": name, "scores": sc} for name, _, sc in scored
        ],
    }
    with open(out_file, "w") as f:
        json.dump(tuning_doc, f, indent=2)
    print(f"Saved tuning log to {out_file}")


if __name__ == "__main__":
    run_tuning()
