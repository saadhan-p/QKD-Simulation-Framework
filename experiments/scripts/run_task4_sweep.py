"""
experiments/run_task4_sweep.py
==============================
Executes the TASK 4 sanity sweep for BB84-LCA:
- Distance L = 20 km (fiber attenuation 0.2 dB/km)
- Detector efficiency eta_det = 0.1
- Default dark counts: dc = 100 Hz, dt = 1 ns
- 20 runs per cell (seed 2024 + run_idx)
- e_channel in {0.01, 0.02, 0.05}
- N in {1e5, 1e6, 1e7}
- p_key in {0.5, 0.7, 0.9, 0.95, 0.98}
- EC leakage: predetermined Q_tol convention (leak_EC = f_EC * n * h2(Q_tol))
- Baseline fairness:
    (1) Tuned Oracle Q_tol: Q_tol = e_channel + 0.01
    (2) Fixed Conservative Q_tol: Q_tol = 0.06 (fixed across all channel conditions)
"""

from __future__ import annotations

import csv
import json
import math
import os
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from typing import Any

# Make script runnable from any directory without PYTHONPATH hacks
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import numpy as np

from backend.channel import attenuation
from backend.finite_key import compute_mu, truncated_h2
from backend.protocols.lca import run_lca



def compute_analytic_optimal_pkey(
    M_det: float,
    Q_tol: float,
    *,
    f_ec: float = 1.16,
    eps_sec: float = 1e-10,
    grid_size: int = 1000,
) -> tuple[float, float]:
    """Find continuous optimal p_key that maximizes finite key rate given detected count M_det.

    Theoretical model:
        N_key = M_det * p_key^2
        k_test = M_det * (1 - p_key)^2
        mu = sqrt( (N_key + k_test) / (N_key * k_test) * (k_test + 1) / k_test * ln(4 / eps_sec) )
        yield = N_key * (1 - h2(Q_tol + mu) - f_ec * h2(Q_tol))
    """
    best_pkey = 0.5
    best_rate = 0.0

    # Grid search over p_key in [0.50, 0.99]
    for i in range(500, 995):
        p_k = i / 1000.0
        p_t = 1.0 - p_k
        n_k = M_det * (p_k ** 2)
        k_t = M_det * (p_t ** 2)
        if k_t < 4.0:
            continue
        try:
            mu = compute_mu(int(n_k), int(k_t), eps_sec)
            eff_phase = Q_tol + mu
            if eff_phase >= 0.5:
                continue
            h_phase = truncated_h2(eff_phase)
            h_ec = truncated_h2(Q_tol)
            rate_per_det = (p_k ** 2) * (1.0 - h_phase - f_ec * h_ec)
            if rate_per_det > best_rate:
                best_rate = rate_per_det
                best_pkey = p_k
        except (ValueError, ZeroDivisionError):
            continue

    return best_pkey, best_rate


def run_sweep() -> list[dict[str, Any]]:
    start_time = time.time()
    distance_km = 20.0
    eta_ch = attenuation(distance_km)
    eta_det = 0.10
    dc = 100.0
    dt = 1e-9
    runs_per_cell = 20
    base_seed = 2024

    e_channels = [0.01, 0.02, 0.05]
    N_values = [100_000, 1_000_000, 10_000_000]
    p_key_values = [0.5, 0.7, 0.9, 0.95, 0.98]

    # Two evaluation modes for baseline fairness:
    # 1. 'tuned': Q_tol = e_channel + 0.01
    # 2. 'conservative_fixed': Q_tol = 0.06
    modes = [("tuned", None), ("fixed_conservative_0.06", 0.06)]

    results = []
    total_cells = len(modes) * len(e_channels) * len(N_values) * len(p_key_values)
    cell_count = 0

    print(f"Starting sweep: {total_cells} cells, {runs_per_cell} runs each...")
    print(f"L={distance_km} km (eta_ch={eta_ch:.6f}), eta_det={eta_det}, dc={dc} Hz, dt={dt} s")
    print(f"Detection probability per pulse: eta_ch * eta_det ~= {eta_ch * eta_det:.6f}")

    for mode_name, fixed_qtol in modes:
        print(f"\n=================== EVALUATION MODE: {mode_name} ===================")
        for e_ch in e_channels:
            Q_tol = fixed_qtol if fixed_qtol is not None else (e_ch + 0.01)
            for N in N_values:
                for p_k in p_key_values:
                    cell_count += 1
                    sifting_list = []
                    ez_list = []
                    ex_list = []
                    fk_rate_list = []
                    asym_rate_list = []
                    aborted_list = []

                    for r in range(runs_per_cell):
                        run_seed = base_seed + r
                        rng = np.random.default_rng(run_seed)
                        res = run_lca(
                            n_sent=N,
                            rng=rng,
                            p_key=p_k,
                            eta_ch=eta_ch,
                            eta_det=eta_det,
                            e_channel=e_ch,
                            dc=dc,
                            dt=dt,
                            Q_tol=Q_tol,
                            ec_leakage_model="q_tol",  # paper-faithful predetermined convention
                            f_ec=1.16,
                            eps_sec=1e-10,
                            eps_cor=1e-10,
                        )
                        sifting_list.append(res["sifting_efficiency"])
                        ez_list.append(res["e_Z_est"])
                        ex_list.append(res["e_X_est"])
                        fk_rate_list.append(res["finite_key_bits_per_pulse"])
                        asym_rate_list.append(res["asymptotic_bits_per_pulse"])
                        aborted_list.append(1 if res["aborted"] else 0)

                    cell_summary = {
                        "mode": mode_name,
                        "e_channel": e_ch,
                        "Q_tol": Q_tol,
                        "N": N,
                        "p_key": p_k,
                        "p_test": round(1.0 - p_k, 2),
                        "sifting_mean": float(np.mean(sifting_list)),
                        "sifting_std": float(np.std(sifting_list, ddof=1)),
                        "ez_mean": float(np.mean(ez_list)),
                        "ex_mean": float(np.mean(ex_list)),
                        "fk_rate_mean": float(np.mean(fk_rate_list)),
                        "fk_rate_std": float(np.std(fk_rate_list, ddof=1)),
                        "asym_rate_mean": float(np.mean(asym_rate_list)),
                        "abort_rate": float(np.mean(aborted_list)),
                    }
                    results.append(cell_summary)

                    if cell_count % 5 == 0 or cell_count == total_cells:
                        print(
                            f"[{cell_count:02d}/{total_cells}] mode={mode_name:12s} e_ch={e_ch:.2f}, N={N:e}, p_key={p_k:.2f} | "
                            f"sift={cell_summary['sifting_mean']:.4f}, "
                            f"FK_rate={cell_summary['fk_rate_mean']:.4e}, "
                            f"abort={cell_summary['abort_rate']:.2f}"
                        )

    # Save to experiments/results_final (tracked) and legacy raw_data
    elapsed = time.time() - start_time
    os.makedirs(os.path.join(_REPO_ROOT, "experiments/results_final"), exist_ok=True)
    os.makedirs(os.path.join(_REPO_ROOT, "experiments/results/raw_data"), exist_ok=True)
    csv_final = os.path.join(_REPO_ROOT, "experiments/results_final/task4_lca_sweep.csv")
    csv_raw = os.path.join(_REPO_ROOT, "experiments/results/raw_data/task4_lca_sweep.csv")

    for path in (csv_final, csv_raw):
        with open(path, "w", newline="") as f:
            fieldnames = list(results[0].keys())
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in results:
                writer.writerow(row)
        print(f"Saved sweep results to {path}")

    # Gather git hash
    try:
        git_hash = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=_REPO_ROOT, text=True
        ).strip()
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
        "simulation_parameters": {
            "distance_km": distance_km,
            "eta_ch": eta_ch,
            "eta_det": eta_det,
            "dc": dc,
            "dt": dt,
            "runs_per_cell": runs_per_cell,
            "base_seed": base_seed,
            "e_channels": e_channels,
            "N_values": N_values,
            "p_key_values": p_key_values,
            "ec_leakage_model": "predetermined_q_tol",
            "f_ec": 1.16,
            "eps_sec": 1e-10,
            "eps_cor": 1e-10,
            "modes": [m[0] for m in modes],
        },
        "runtime_seconds": elapsed,
        "total_cells": total_cells,
        "total_runs": total_cells * runs_per_cell,
        "output_files": [
            "experiments/results_final/task4_lca_sweep.csv",
            "experiments/results/raw_data/task4_lca_sweep.csv",
        ],
    }

    meta_final = os.path.join(_REPO_ROOT, "experiments/results_final/task4_lca_sweep.metadata.json")
    with open(meta_final, "w") as f:
        json.dump(metadata, f, indent=2)
    print(f"Saved metadata to {meta_final}")

    print(f"Total sweep execution time: {elapsed:.2f} seconds ({elapsed/60.0:.2f} minutes)")

    return results


def print_markdown_table(results: list[dict[str, Any]]):
    print("\n### TASK 4: BB84-LCA Sanity Sweep Table (Predetermined Q_tol EC Leakage, 20 runs/cell)")

    for mode in ["tuned", "fixed_conservative_0.06"]:
        mode_label = "Tuned Oracle Controller ($Q_{\\text{tol}} = e_{\\text{channel}} + 1\\%$)" if mode == "tuned" else "Fixed Conservative Baseline ($Q_{\\text{tol}} = 6\\%$)"
        print(f"\n#### {mode_label}\n")
        print("| $e_{\\text{channel}}$ | $N$ | $p_{\\text{key}}$ | $p_{\\text{test}}$ | $Q_{\\text{tol}}$ | Sifting Eff | $e_{Z,\\text{est}}$ | $e_{X,\\text{est}}$ | Finite Key / pulse | Asym Key / pulse | Abort Rate |")
        print("|---|---|---|---|---|---|---|---|---|---|---|")
        for r in results:
            if r["mode"] != mode:
                continue
            print(
                f"| {r['e_channel']*100:.0f}% | {r['N']:.0e} | {r['p_key']:.2f} | {r['p_test']:.2f} | {r['Q_tol']*100:.0f}% | "
                f"{r['sifting_mean']:.4f} | {r['ez_mean']:.4f} | {r['ex_mean']:.4f} | "
                f"{r['fk_rate_mean']:.4e} | {r['asym_rate_mean']:.4e} | {r['abort_rate']:.2f} |"
            )

    print("\n### Optimal $p_{\\text{key}}$ Comparison across Controllers\n")
    print("| $e_{\\text{channel}}$ | $N$ | Expected $M_{\\text{det}}$ | Tuned Opt $p_{\\text{key}}$ | Tuned Yield | Fixed Opt $p_{\\text{key}}$ | Fixed Yield | Analytic Cont. Opt $p_{\\text{key}}^*$ |")
    print("|---|---|---|---|---|---|---|---|")

    # Group by (e_channel, N)
    e_channels = [0.01, 0.02, 0.05]
    N_values = [100_000, 1_000_000, 10_000_000]
    distance_km = 20.0
    eta_ch = attenuation(distance_km)
    eta_det = 0.10
    M_det_factor = eta_ch * eta_det

    for e_ch in e_channels:
        for N in N_values:
            m_det = N * M_det_factor
            tuned_cells = [r for r in results if r["mode"] == "tuned" and r["e_channel"] == e_ch and r["N"] == N]
            fixed_cells = [r for r in results if r["mode"] == "fixed_conservative_0.06" and r["e_channel"] == e_ch and r["N"] == N]

            best_tuned = max(tuned_cells, key=lambda x: x["fk_rate_mean"])
            best_fixed = max(fixed_cells, key=lambda x: x["fk_rate_mean"])

            cont_opt_pkey, _ = compute_analytic_optimal_pkey(m_det, best_tuned["Q_tol"])

            print(
                f"| {e_ch*100:.0f}% | {N:.0e} | {m_det:.1e} | "
                f"**{best_tuned['p_key']:.2f}** | {best_tuned['fk_rate_mean']:.4e} | "
                f"**{best_fixed['p_key']:.2f}** | {best_fixed['fk_rate_mean']:.4e} | "
                f"**{cont_opt_pkey:.3f}** |"
            )


if __name__ == "__main__":
    results = run_sweep()
    print_markdown_table(results)
