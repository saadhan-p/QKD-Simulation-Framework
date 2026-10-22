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
- p_Z in {0.5, 0.7, 0.9, 0.95, 0.98}
- Q_tol = e_channel + 0.01
"""

from __future__ import annotations

import csv
import os
import sys
from typing import Any

import numpy as np

from backend.channel import attenuation
from backend.protocols.lca import run_lca


def run_sweep() -> list[dict[str, Any]]:
    distance_km = 20.0
    eta_ch = attenuation(distance_km)
    eta_det = 0.10
    dc = 100.0
    dt = 1e-9
    runs_per_cell = 20
    base_seed = 2024

    e_channels = [0.01, 0.02, 0.05]
    N_values = [100_000, 1_000_000, 10_000_000]
    p_Z_values = [0.5, 0.7, 0.9, 0.95, 0.98]

    results = []
    total_cells = len(e_channels) * len(N_values) * len(p_Z_values)
    cell_count = 0

    print(f"Starting sweep: {total_cells} cells, {runs_per_cell} runs each...")
    print(f"L={distance_km} km (eta_ch={eta_ch:.6f}), eta_det={eta_det}, dc={dc} Hz, dt={dt} s")

    for e_ch in e_channels:
        Q_tol = e_ch + 0.01
        for N in N_values:
            for p_z in p_Z_values:
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
                        p_Z=p_z,
                        eta_ch=eta_ch,
                        eta_det=eta_det,
                        e_channel=e_ch,
                        dc=dc,
                        dt=dt,
                        Q_tol=Q_tol,
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
                    "e_channel": e_ch,
                    "Q_tol": Q_tol,
                    "N": N,
                    "p_Z": p_z,
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

                print(
                    f"[{cell_count:02d}/{total_cells}] e_ch={e_ch:.2f}, N={N:e}, p_Z={p_z:.2f} | "
                    f"sift={cell_summary['sifting_mean']:.4f}, "
                    f"eZ={cell_summary['ez_mean']:.4f}, eX={cell_summary['ex_mean']:.4f}, "
                    f"FK_rate={cell_summary['fk_rate_mean']:.5e}, "
                    f"Asym_rate={cell_summary['asym_rate_mean']:.5e}, "
                    f"abort={cell_summary['abort_rate']:.2f}"
                )

    # Save to CSV
    os.makedirs("experiments/results/raw_data", exist_ok=True)
    csv_path = "experiments/results/raw_data/task4_lca_sweep.csv"
    with open(csv_path, "w", newline="") as f:
        fieldnames = list(results[0].keys())
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in results:
            writer.writerow(row)
    print(f"\nSaved CSV to {csv_path}")

    return results


def print_markdown_table(results: list[dict[str, Any]]):
    print("\n### TASK 4: BB84-LCA Sanity Sweep Table (20 runs/cell, seed=2024..2043)\n")
    print("| $e_{\\text{channel}}$ | $N$ | $p_Z$ | $Q_{\\text{tol}}$ | Sifting Eff | $e_{Z,\\text{est}}$ | $e_{X,\\text{est}}$ | Finite Key / pulse | Asym Key / pulse | Abort Rate |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    for r in results:
        print(
            f"| {r['e_channel']*100:.0f}% | {r['N']:.0e} | {r['p_Z']:.2f} | {r['Q_tol']*100:.0f}% | "
            f"{r['sifting_mean']:.4f} | {r['ez_mean']:.4f} | {r['ex_mean']:.4f} | "
            f"{r['fk_rate_mean']:.4e} | {r['asym_rate_mean']:.4e} | {r['abort_rate']:.2f} |"
        )

    print("\n### Optimal $p_Z$ for Each $(e_{\\text{channel}}, N)$ Condition\n")
    print("| $e_{\\text{channel}}$ | $N$ | Optimal $p_Z$ (Max Finite Yield) | Max Finite Key / pulse | Asymptotic Rate @ Opt |")
    print("|---|---|---|---|---|")

    conditions = {}
    for r in results:
        key = (r["e_channel"], r["N"])
        if key not in conditions:
            conditions[key] = []
        conditions[key].append(r)

    for (e_ch, N), cell_group in conditions.items():
        best = max(cell_group, key=lambda x: x["fk_rate_mean"])
        print(
            f"| {e_ch*100:.0f}% | {N:.0e} | **{best['p_Z']:.2f}** | "
            f"{best['fk_rate_mean']:.4e} | {best['asym_rate_mean']:.4e} |"
        )


if __name__ == "__main__":
    results = run_sweep()
    print_markdown_table(results)
