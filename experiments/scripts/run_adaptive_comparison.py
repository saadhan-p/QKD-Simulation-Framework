"""
experiments/scripts/run_adaptive_comparison.py
=============================================
TASK 4 & TASK 6: Adaptive Controller Comparison Harness and Pilot Evaluation.

Strategies:
 - S0: p_key = 0.50 (tuned Q_tol and conservative Q_tol 8%)
 - S1_0.7: p_key = 0.70 (tuned and conservative)
 - S1_0.9: p_key = 0.90 (tuned and conservative)
 - S2: Adaptive controller (model-based, hysteresis, safe fallback)
 - S3: Oracle (knows true channel state per block; same yield model)
 - S4: Best fixed (in hindsight per scenario)

Assumptions:
 - R_rep = 100 MHz (1e8 pulses/second). Assumed repetition rate for key/second reporting.
 - Total epsilon: eps_sec = 1e-10, eps_cor = 1e-10 per block. Total epsilon recorded in outputs.
"""

from __future__ import annotations

import csv
import json
import math
import multiprocessing
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

from backend.channel import attenuation
from backend.controller import AdaptiveController, ControllerHyperparams, FixedController, OracleController
from backend.finite_key import BlockHistoryEntry, History
from backend.protocols.lca import run_lca
from experiments.scenarios import ChannelBlockState, get_block_pulse_seed, get_scenario_trace


def compute_bootstrap_ci(data: list[float], n_boot: int = 2000, alpha: float = 0.05) -> tuple[float, float, float]:
    """Compute bootstrap mean and (1 - alpha) percentile confidence interval."""
    if not data:
        return 0.0, 0.0, 0.0
    arr = np.array(data, dtype=float)
    mean_val = float(np.mean(arr))
    if len(arr) <= 1 or np.all(arr == arr[0]):
        return mean_val, mean_val, mean_val

    rng = np.random.default_rng(12345)
    boot_means = np.zeros(n_boot)
    n = len(arr)
    for i in range(n_boot):
        sample = rng.choice(arr, size=n, replace=True)
        boot_means[i] = np.mean(sample)

    low = float(np.percentile(boot_means, 100.0 * (alpha / 2.0)))
    high = float(np.percentile(boot_means, 100.0 * (1.0 - alpha / 2.0)))
    return mean_val, low, high


def run_single_simulation(
    scenario_name: str,
    seed: int,
    strategy_id: str,
    num_blocks: int,
    N: int,
    R_rep: float = 1e8,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Execute a single (scenario, seed, strategy) run across num_blocks."""
    trace = get_scenario_trace(scenario_name, num_blocks, seed)
    hist = History()

    # Determine nominal channel error for tuned Q_tol baseline
    nominal_e = float(np.mean([st.e_channel for st in trace]))

    # Instantiate controller
    controller: Any
    qtol_policy = "adaptive"
    if strategy_id == "S0_tuned":
        controller = FixedController(p_key=0.50, Q_tol=min(0.12, nominal_e + 0.010), N=N)
        qtol_policy = "tuned"
    elif strategy_id == "S0_conservative":
        controller = FixedController(p_key=0.50, Q_tol=0.080, N=N)
        qtol_policy = "conservative"
    elif strategy_id == "S1_0.7_tuned":
        controller = FixedController(p_key=0.70, Q_tol=min(0.12, nominal_e + 0.010), N=N)
        qtol_policy = "tuned"
    elif strategy_id == "S1_0.7_conservative":
        controller = FixedController(p_key=0.70, Q_tol=0.080, N=N)
        qtol_policy = "conservative"
    elif strategy_id == "S1_0.9_tuned":
        controller = FixedController(p_key=0.90, Q_tol=min(0.12, nominal_e + 0.010), N=N)
        qtol_policy = "tuned"
    elif strategy_id == "S1_0.9_conservative":
        controller = FixedController(p_key=0.90, Q_tol=0.080, N=N)
        qtol_policy = "conservative"
    elif strategy_id == "S2_adaptive":
        controller = AdaptiveController(N=N)
        qtol_policy = "adaptive"
    elif strategy_id == "S3_oracle":
        controller = OracleController(N=N, margin=0.010)
        qtol_policy = "oracle_matched"
    else:
        raise ValueError(f"Unknown strategy_id: {strategy_id}")

    block_records = []
    total_key_bits = 0
    total_aborts = 0
    total_switches = 0
    total_safe_mode_blocks = 0
    prev_pkey = 0.50

    total_sim_time = 0.0
    total_finite_key_time = 0.0
    total_controller_time = 0.0

    p_key_trajectory = []

    for b in range(num_blocks):
        st = trace[b]

        # 1. Controller step
        t_ctrl0 = time.perf_counter()
        if strategy_id == "S3_oracle":
            controller.set_true_channel_state(g=st.g, e_channel=st.e_channel)
        params = controller.next_params(hist)
        t_ctrl1 = time.perf_counter()
        ctrl_time = t_ctrl1 - t_ctrl0
        total_controller_time += ctrl_time

        # Decision reasoning
        reason = "fixed"
        pred_yield = 0.0
        if strategy_id == "S2_adaptive" and controller.decision_log:
            last_dec = controller.decision_log[-1]
            reason = last_dec.reason
            pred_yield = last_dec.predicted_yield
            if reason == "safe":
                total_safe_mode_blocks += 1

        if not math.isclose(params.p_key, prev_pkey, abs_tol=1e-3):
            total_switches += 1
            prev_pkey = params.p_key

        p_key_trajectory.append(params.p_key)

        # 2. Simulation step (Common Random Numbers)
        pulse_seed = get_block_pulse_seed(seed, b)
        rng = np.random.default_rng(pulse_seed)

        t_sim0 = time.perf_counter()
        sim_res = run_lca(
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
        t_sim1 = time.perf_counter()
        sim_time = t_sim1 - t_sim0
        total_sim_time += sim_time

        # History entry update
        entry = BlockHistoryEntry(
            block_id=b,
            n_sent=params.N,
            n_detected=sim_res["n_detected"],
            n_ZZ=sim_res["n_ZZ"],
            n_XX=sim_res["n_XX"],
            n_mismatch=sim_res["n_mismatch"],
            sample_size_z=sim_res["sample_size_z"],
            errors_z=sim_res["errors_z"],
            sample_size_x=sim_res["sample_size_x"],
            errors_x=sim_res["errors_x"],
            e_Z_est=sim_res["e_Z_est"],
            e_X_est=sim_res["e_X_est"],
            finite_key_length=sim_res["finite_key_length"],
            aborted=sim_res["aborted"],
        )
        hist = hist.append(entry)

        key_len = sim_res["finite_key_length"]
        total_key_bits += key_len
        if sim_res["aborted"]:
            total_aborts += 1

        b_rec = {
            "scenario": scenario_name,
            "seed": seed,
            "strategy": strategy_id,
            "qtol_policy": qtol_policy,
            "block_idx": b,
            "p_key": params.p_key,
            "p_test": params.p_test,
            "Q_tol": params.Q_tol,
            "N": params.N,
            "n_detected": sim_res["n_detected"],
            "n_ZZ": sim_res["n_ZZ"],
            "n_XX": sim_res["n_XX"],
            "sample_size_z": sim_res["sample_size_z"],
            "errors_z": sim_res["errors_z"],
            "sample_size_x": sim_res["sample_size_x"],
            "errors_x": sim_res["errors_x"],
            "e_Z_est": sim_res["e_Z_est"],
            "e_X_est": sim_res["e_X_est"],
            "finite_key_length": key_len,
            "aborted": sim_res["aborted"],
            "finite_key_bits_per_pulse": sim_res["finite_key_bits_per_pulse"],
            "true_L_km": st.L_km,
            "true_eta_ch": st.eta_ch,
            "true_eta_det": st.eta_det,
            "true_e_channel": st.e_channel,
            "true_g": st.g,
            "controller_reason": reason,
            "predicted_yield": pred_yield,
            "sim_time_s": sim_time,
            "controller_time_s": ctrl_time,
            "total_eps_sec": (b + 1) * 1e-10,
            "total_eps_cor": (b + 1) * 1e-10,
        }
        block_records.append(b_rec)

    total_pulses = num_blocks * N
    key_per_pulse = total_key_bits / total_pulses
    key_per_sec = key_per_pulse * R_rep

    run_summary = {
        "scenario": scenario_name,
        "seed": seed,
        "strategy": strategy_id,
        "qtol_policy": qtol_policy,
        "total_pulses_sent": total_pulses,
        "total_key_bits": total_key_bits,
        "key_per_pulse": key_per_pulse,
        "key_rate_bps_100MHz": key_per_sec,
        "abort_rate": total_aborts / num_blocks,
        "num_switches": total_switches,
        "safe_mode_blocks": total_safe_mode_blocks,
        "sifting_eff_mean": float(np.mean([r["n_ZZ"] + r["n_XX"] for r in block_records])) / float(np.mean([r["n_detected"] for r in block_records]) or 1.0),
        "mean_e_test_est": float(np.mean([r["e_X_est"] for r in block_records])),
        "mean_true_e": float(np.mean([r["true_e_channel"] for r in block_records])),
        "sim_time_total_s": total_sim_time,
        "ctrl_time_total_s": total_controller_time,
        "p_key_trajectory": p_key_trajectory,
        "total_eps_sec": num_blocks * 1e-10,
        "total_eps_cor": num_blocks * 1e-10,
    }

    return run_summary, block_records


def _run_worker(args):
    return run_single_simulation(*args)


def run_pilot():
    start_total_time = time.time()
    num_seeds = 20
    eval_seeds = list(range(num_seeds))
    num_blocks = 60
    N = 2_000_000
    R_rep = 1e8  # 100 MHz repetition rate assumption

    scenarios = [
        "static_nominal",
        "step_e_channel",
        "step_loss",
        "linear_ramp_loss",
        "bursty_noise",
        "eve_episode",
    ]

    strategies = [
        "S0_tuned",
        "S0_conservative",
        "S1_0.7_tuned",
        "S1_0.7_conservative",
        "S1_0.9_tuned",
        "S1_0.9_conservative",
        "S2_adaptive",
        "S3_oracle",
    ]

    tasks = []
    for sc in scenarios:
        for seed in eval_seeds:
            for strat in strategies:
                tasks.append((sc, seed, strat, num_blocks, N))

    total_tasks = len(tasks)
    print(f"Launching Task 6 Pilot Evaluation:")
    print(f"  Scenarios ({len(scenarios)}): {scenarios}")
    print(f"  Evaluation Seeds ({num_seeds}): 0..{num_seeds-1}")
    print(f"  Blocks per run: {num_blocks}, N: {N:.0e} pulses")
    print(f"  Total strategy runs: {total_tasks}")

    num_workers = min(7, os.cpu_count() or 4)
    print(f"Parallelizing with {num_workers} worker processes...")

    all_run_summaries = []
    all_block_records = []

    with multiprocessing.Pool(processes=num_workers) as pool:
        for idx, (run_sum, b_recs) in enumerate(pool.imap_unordered(_run_worker, tasks), 1):
            all_run_summaries.append(run_sum)
            all_block_records.extend(b_recs)
            if idx % 50 == 0 or idx == total_tasks:
                print(f"[{idx:03d}/{total_tasks}] Completed runs...")

    elapsed_total = time.time() - start_total_time
    print(f"Pilot execution finished in {elapsed_total:.2f} seconds ({elapsed_total/60.0:.2f} minutes).")

    # Reaction Time and Cumulative Regret Calculation
    # Need oracle baseline per (scenario, seed)
    oracle_map: dict[tuple[str, int], dict[str, Any]] = {}
    for r in all_run_summaries:
        if r["strategy"] == "S3_oracle":
            oracle_map[(r["scenario"], r["seed"])] = r

    for r in all_run_summaries:
        sc = r["scenario"]
        sd = r["seed"]
        orc = oracle_map.get((sc, sd))
        if orc:
            # Regret = Oracle Yield - Strategy Yield
            r["regret_vs_oracle"] = max(0.0, orc["key_per_pulse"] - r["key_per_pulse"])
            # Reaction time in step_e_channel (step occurs at block 20)
            if sc == "step_e_channel":
                orc_traj = orc["p_key_trajectory"]
                strat_traj = r["p_key_trajectory"]
                reaction = -1
                for step_b in range(20, num_blocks - 2):
                    # within 0.05 of oracle for 3 consecutive blocks
                    if (abs(strat_traj[step_b] - orc_traj[step_b]) <= 0.05 and
                        abs(strat_traj[step_b+1] - orc_traj[step_b+1]) <= 0.05 and
                        abs(strat_traj[step_b+2] - orc_traj[step_b+2]) <= 0.05):
                        reaction = step_b - 20
                        break
                r["reaction_time_blocks"] = reaction
            else:
                r["reaction_time_blocks"] = 0
        else:
            r["regret_vs_oracle"] = 0.0
            r["reaction_time_blocks"] = 0

    # Save per-block raw data (experiments/results/raw_data and experiments/results_final)
    os.makedirs(os.path.join(_REPO_ROOT, "experiments/results_final"), exist_ok=True)
    os.makedirs(os.path.join(_REPO_ROOT, "experiments/results/raw_data"), exist_ok=True)

    block_csv = os.path.join(_REPO_ROOT, "experiments/results/raw_data/pilot_per_block.csv")
    with open(block_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(all_block_records[0].keys()))
        writer.writeheader()
        for row in all_block_records:
            writer.writerow(row)
    print(f"Saved per-block data to {block_csv}")

    # Save per-run data
    run_csv = os.path.join(_REPO_ROOT, "experiments/results_final/pilot_per_run.csv")
    run_fieldnames = [k for k in all_run_summaries[0].keys() if k != "p_key_trajectory"]
    with open(run_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=run_fieldnames)
        writer.writeheader()
        for r in all_run_summaries:
            row = {k: v for k, v in r.items() if k != "p_key_trajectory"}
            writer.writerow(row)
    print(f"Saved per-run data to {run_csv}")

    # Compute Statistics across Seeds
    # Identify best fixed (S4) in hindsight per scenario
    fixed_strategy_ids = [
        "S0_tuned", "S0_conservative",
        "S1_0.7_tuned", "S1_0.7_conservative",
        "S1_0.9_tuned", "S1_0.9_conservative",
    ]

    summary_rows = []
    for sc in scenarios:
        # Find best fixed strategy in hindsight for this scenario
        best_fixed_strat = ""
        best_fixed_mean_yield = -1.0
        for fstrat in fixed_strategy_ids:
            yields = [r["key_per_pulse"] for r in all_run_summaries if r["scenario"] == sc and r["strategy"] == fstrat]
            m_y = float(np.mean(yields))
            if m_y > best_fixed_mean_yield:
                best_fixed_mean_yield = m_y
                best_fixed_strat = fstrat

        # Map seeds to best fixed run
        best_fixed_by_seed = {
            r["seed"]: r["key_per_pulse"]
            for r in all_run_summaries if r["scenario"] == sc and r["strategy"] == best_fixed_strat
        }
        # S0 baseline by seed
        s0_tuned_by_seed = {
            r["seed"]: r["key_per_pulse"]
            for r in all_run_summaries if r["scenario"] == sc and r["strategy"] == "S0_tuned"
        }

        for strat in strategies:
            strat_runs = [r for r in all_run_summaries if r["scenario"] == sc and r["strategy"] == strat]
            strat_runs.sort(key=lambda x: x["seed"])

            yields = [r["key_per_pulse"] for r in strat_runs]
            mean_y, ci_low_y, ci_high_y = compute_bootstrap_ci(yields)

            # Paired differences vs S0 tuned
            diff_vs_s0 = [r["key_per_pulse"] - s0_tuned_by_seed[r["seed"]] for r in strat_runs]
            mean_diff_s0, ci_low_s0, ci_high_s0 = compute_bootstrap_ci(diff_vs_s0)

            # Paired differences vs best fixed S4
            diff_vs_best_fixed = [r["key_per_pulse"] - best_fixed_by_seed[r["seed"]] for r in strat_runs]
            mean_diff_bf, ci_low_bf, ci_high_bf = compute_bootstrap_ci(diff_vs_best_fixed)

            abort_rate = float(np.mean([r["abort_rate"] for r in strat_runs]))
            switches = float(np.mean([r["num_switches"] for r in strat_runs]))
            regret = float(np.mean([r["regret_vs_oracle"] for r in strat_runs]))
            reaction = float(np.mean([r["reaction_time_blocks"] for r in strat_runs]))

            s_row = {
                "scenario": sc,
                "strategy": strat,
                "best_fixed_hindsight": best_fixed_strat,
                "mean_yield_per_pulse": mean_y,
                "ci_low_yield": ci_low_y,
                "ci_high_yield": ci_high_y,
                "mean_diff_vs_S0": mean_diff_s0,
                "ci_low_diff_S0": ci_low_s0,
                "ci_high_diff_S0": ci_high_s0,
                "mean_diff_vs_best_fixed": mean_diff_bf,
                "ci_low_diff_best_fixed": ci_low_bf,
                "ci_high_diff_best_fixed": ci_high_bf,
                "abort_rate": abort_rate,
                "switches_mean": switches,
                "regret_vs_oracle": regret,
                "reaction_time_blocks": reaction,
            }
            summary_rows.append(s_row)

    # Save summary CSV
    summary_csv = os.path.join(_REPO_ROOT, "experiments/results_final/pilot_summary.csv")
    with open(summary_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()))
        writer.writeheader()
        for row in summary_rows:
            writer.writerow(row)
    print(f"Saved pilot summary to {summary_csv}")

    # Save metadata JSON
    try:
        git_hash = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=_REPO_ROOT, text=True).strip()
    except Exception:
        git_hash = "unknown"

    metadata = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "git_hash": git_hash,
        "python_interpreter": sys.executable,
        "python_version": sys.version,
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
        },
        "pilot_parameters": {
            "num_seeds": num_seeds,
            "seeds": eval_seeds,
            "num_blocks": num_blocks,
            "N": N,
            "R_rep_Hz": R_rep,
            "scenarios": scenarios,
            "strategies": strategies,
            "fixed_strategy_qtol_policies": ["tuned", "conservative_0.08"],
            "total_epsilon_per_block": {"eps_sec": 1e-10, "eps_cor": 1e-10},
            "total_composite_epsilon_60_blocks": {"eps_sec": 6e-9, "eps_cor": 6e-9},
        },
        "execution_time_seconds": elapsed_total,
        "num_workers": num_workers,
        "output_files": {
            "per_block_csv": "experiments/results/raw_data/pilot_per_block.csv",
            "per_run_csv": "experiments/results_final/pilot_per_run.csv",
            "summary_csv": "experiments/results_final/pilot_summary.csv",
        },
    }

    meta_file = os.path.join(_REPO_ROOT, "experiments/results_final/pilot_comparison.metadata.json")
    with open(meta_file, "w") as f:
        json.dump(metadata, f, indent=2)
    print(f"Saved pilot metadata to {meta_file}")

    return summary_rows, elapsed_total


def print_pilot_table(summary_rows: list[dict[str, Any]]):
    print("\n### TASK 6: Pilot Comparison Results Across Scenarios (20 Seeds, 60 Blocks, N = 2e6)\n")
    print("| Scenario | Strategy | Yield / pulse (95% CI) | Paired Diff vs S0 (95% CI) | Paired Diff vs Best Fixed (95% CI) | Abort Rate | Switches | Regret vs Oracle |")
    print("|---|---|---|---|---|---|---|---|")
    for r in summary_rows:
        strat = r["strategy"]
        y_str = f"{r['mean_yield_per_pulse']:.4e} [{r['ci_low_yield']:.4e}, {r['ci_high_yield']:.4e}]"
        diff_s0_str = f"{r['mean_diff_vs_S0']:+.4e} [{r['ci_low_diff_S0']:+.4e}, {r['ci_high_diff_S0']:+.4e}]"
        diff_bf_str = f"{r['mean_diff_vs_best_fixed']:+.4e} [{r['ci_low_diff_best_fixed']:+.4e}, {r['ci_high_diff_best_fixed']:+.4e}]"
        print(
            f"| {r['scenario']} | {strat} | {y_str} | {diff_s0_str} | {diff_bf_str} | "
            f"{r['abort_rate']:.2f} | {r['switches_mean']:.1f} | {r['regret_vs_oracle']:.4e} |"
        )


if __name__ == "__main__":
    summary, elapsed = run_pilot()
    print_pilot_table(summary)
