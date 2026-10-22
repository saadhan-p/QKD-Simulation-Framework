"""
experiments/scripts/generate_optimum_map.py
==========================================
Generates the optimum parameter map for Task 1:
- L in {5, 10, 20, 30, 40} km
- e_channel in {0.5%, 1%, 2%, 3%, 5%, 7%} (0.005, 0.01, 0.02, 0.03, 0.05, 0.07)
- N in {1e5, 1e6, 1e7, 1e8} pulses
- p_key in [0.50..0.98] step 0.02 (25 grid points)
- Q_tol margin in {0.5%, 1%, 2%} (0.005, 0.01, 0.02)

Outputs:
- CSV: experiments/results_final/optimum_map.csv
- Plot: experiments/results_final/optimum_map.png
- Metadata: experiments/results_final/optimum_map.metadata.json
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

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import matplotlib.pyplot as plt
import numpy as np

from backend.channel import attenuation
from backend.yield_model import expected_finite_yield


def run_optimum_map() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    start_time = time.time()
    eta_det = 0.10
    dc = 100.0
    dt = 1e-9

    L_list = [5.0, 10.0, 20.0, 30.0, 40.0]
    e_list = [0.005, 0.01, 0.02, 0.03, 0.05, 0.07]
    N_list = [100_000, 1_000_000, 10_000_000, 100_000_000]
    margins = [0.005, 0.010, 0.020]
    pkey_grid = [round(0.50 + 0.02 * i, 2) for i in range(25)]  # 0.50 to 0.98

    results = []
    total_cells = len(L_list) * len(e_list) * len(N_list) * len(margins)
    print(f"Generating optimum map across {total_cells} operating points...")

    cell_idx = 0
    for L in L_list:
        eta_ch = attenuation(L)
        g = eta_ch * eta_det + 2.0 * dc * dt

        for e_ch in e_list:
            e_eff = (e_ch * eta_ch * eta_det + 0.5 * 2.0 * dc * dt) / g

            for N in N_list:
                m_det = g * N

                for m in margins:
                    cell_idx += 1
                    Q_tol = e_eff + m

                    yield_curve: dict[float, float] = {}
                    p_pass_curve: dict[float, float] = {}

                    for p_k in pkey_grid:
                        rate, p_pass = expected_finite_yield(
                            g=g,
                            e_key=e_eff,
                            e_test=e_eff,
                            N=N,
                            p_key=p_k,
                            Q_tol=Q_tol,
                            params={"f_ec": 1.16, "eps_sec": 1e-10, "eps_cor": 1e-10, "ec_leakage_model": "predetermined_Qtol"},
                        )
                        yield_curve[p_k] = rate
                        p_pass_curve[p_k] = p_pass

                    # Best p_key
                    best_pkey = max(pkey_grid, key=lambda pk: yield_curve[pk])
                    best_yield = yield_curve[best_pkey]
                    best_pass = p_pass_curve[best_pkey]

                    # Sensitivity: off by -0.1 and +0.1
                    pk_minus = max(0.50, round(best_pkey - 0.10, 2))
                    pk_plus = min(0.98, round(best_pkey + 0.10, 2))
                    yield_minus = yield_curve[pk_minus]
                    yield_plus = yield_curve[pk_plus]

                    loss_minus_pct = ((best_yield - yield_minus) / best_yield * 100.0) if best_yield > 0 else 0.0
                    loss_plus_pct = ((best_yield - yield_plus) / best_yield * 100.0) if best_yield > 0 else 0.0

                    row = {
                        "L_km": L,
                        "eta_ch": eta_ch,
                        "e_channel": e_ch,
                        "N": N,
                        "m_det": m_det,
                        "margin": m,
                        "Q_tol": Q_tol,
                        "best_p_key": best_pkey,
                        "best_yield": best_yield,
                        "p_pass": best_pass,
                        "p_key_minus_0_1": pk_minus,
                        "yield_minus_0_1": yield_minus,
                        "loss_minus_0_1_pct": loss_minus_pct,
                        "p_key_plus_0_1": pk_plus,
                        "yield_plus_0_1": yield_plus,
                        "loss_plus_0_1_pct": loss_plus_pct,
                    }
                    results.append(row)

    elapsed = time.time() - start_time
    print(f"Optimum map generation completed in {elapsed:.2f} seconds.")

    # Save to CSV
    os.makedirs(os.path.join(_REPO_ROOT, "experiments/results_final"), exist_ok=True)
    csv_path = os.path.join(_REPO_ROOT, "experiments/results_final/optimum_map.csv")
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(results[0].keys()))
        writer.writeheader()
        for r in results:
            writer.writerow(r)
    print(f"Saved CSV to {csv_path}")

    # Generate Heatmaps
    # 4 subplots for each N, heatmap of best_p_key vs (L, e_channel) at margin = 1.0%
    fig, axes = plt.subplots(2, 2, figsize=(14, 11))
    axes = axes.flatten()

    for idx, N in enumerate(N_list):
        ax = axes[idx]
        grid = np.zeros((len(e_list), len(L_list)))
        for i, e_ch in enumerate(e_list):
            for j, L in enumerate(L_list):
                match = [
                    r for r in results
                    if r["N"] == N and abs(r["L_km"] - L) < 1e-3 and abs(r["e_channel"] - e_ch) < 1e-4 and abs(r["margin"] - 0.010) < 1e-4
                ]
                if match:
                    # If best_yield == 0, mark as 0.50 (no key extracted)
                    grid[i, j] = match[0]["best_p_key"] if match[0]["best_yield"] > 0 else 0.50

        im = ax.imshow(grid, cmap="viridis", vmin=0.50, vmax=0.98, origin="lower", aspect="auto")
        ax.set_xticks(range(len(L_list)))
        ax.set_xticklabels([f"{int(l)}" for l in L_list])
        ax.set_yticks(range(len(e_list)))
        ax.set_yticklabels([f"{e*100:.1f}%" for e in e_list])
        ax.set_xlabel("Distance L (km)")
        ax.set_ylabel("e_channel")
        ax.set_title(f"Optimal p_key (N = {N:.0e}, Margin = 1.0%)")

        for i in range(len(e_list)):
            for j in range(len(L_list)):
                val = grid[i, j]
                color = "white" if val < 0.75 else "black"
                ax.text(j, i, f"{val:.2f}", ha="center", va="center", color=color, fontsize=9, fontweight="bold")

    fig.subplots_adjust(right=0.88)
    cbar_ax = fig.add_axes([0.90, 0.15, 0.03, 0.7])
    fig.colorbar(im, cax=cbar_ax, label="Optimal p_key")
    fig.suptitle("Optimal Key-Basis Probability p_key Map (BB84-LCA with TLGR 2012 Bounds)", fontsize=14, fontweight="bold")

    plot_path = os.path.join(_REPO_ROOT, "experiments/results_final/optimum_map.png")
    plt.savefig(plot_path, dpi=200, bbox_inches="tight")
    plt.close()
    print(f"Saved Heatmap plot to {plot_path}")

    # Analysis summary for deliverable
    # 1. Dependence on M_det = g * N
    # 2. Dependence on e_channel
    # 3. Yield loss for +/- 0.1 off
    positive_cells = [r for r in results if r["best_yield"] > 0]
    avg_loss_minus = np.mean([r["loss_minus_0_1_pct"] for r in positive_cells]) if positive_cells else 0.0
    avg_loss_plus = np.mean([r["loss_plus_0_1_pct"] for r in positive_cells]) if positive_cells else 0.0
    max_loss_plus = np.max([r["loss_plus_0_1_pct"] for r in positive_cells]) if positive_cells else 0.0

    analysis = {
        "total_cells": len(results),
        "positive_yield_cells": len(positive_cells),
        "avg_loss_minus_0_1_pct": float(avg_loss_minus),
        "avg_loss_plus_0_1_pct": float(avg_loss_plus),
        "max_loss_plus_0_1_pct": float(max_loss_plus),
    }

    # Save metadata JSON
    meta_path = os.path.join(_REPO_ROOT, "experiments/results_final/optimum_map.metadata.json")
    try:
        git_hash = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=_REPO_ROOT, text=True).strip()
    except Exception:
        git_hash = "unknown"

    meta = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "git_hash": git_hash,
        "runtime_seconds": elapsed,
        "analysis_summary": analysis,
        "files": {
            "csv": "experiments/results_final/optimum_map.csv",
            "png": "experiments/results_final/optimum_map.png",
        },
    }
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)

    return results, analysis


if __name__ == "__main__":
    results, analysis = run_optimum_map()
    print("\n--- Summary of Sensitivity Analysis ---")
    print(f"Average yield loss when p_key is 0.1 below optimum: {analysis['avg_loss_minus_0_1_pct']:.2f}%")
    print(f"Average yield loss when p_key is 0.1 above optimum: {analysis['avg_loss_plus_0_1_pct']:.2f}%")
    print(f"Maximum yield loss when p_key is 0.1 above optimum: {analysis['max_loss_plus_0_1_pct']:.2f}% (often 100% due to sample starvation/abort)")
