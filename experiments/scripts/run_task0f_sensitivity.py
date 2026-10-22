"""
experiments/scripts/run_task0f_sensitivity.py
============================================
Evaluates Q_tol sensitivity for Task 0f:
- e_channel = 2% (0.02)
- N in {1e6, 1e7}
- p_key in {0.7, 0.9}
- Q_tol margin in {0.5%, 1.0%, 2.0%} (i.e. Q_tol in {0.025, 0.030, 0.040})
- Predetermined Q_tol EC leakage convention
- 20 runs per cell (seed 2024 + run_idx)
"""

from __future__ import annotations

import csv
import json
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
from backend.protocols.lca import run_lca


def run_qtol_sensitivity() -> list[dict[str, Any]]:
    start_time = time.time()
    distance_km = 20.0
    eta_ch = attenuation(distance_km)
    eta_det = 0.10
    dc = 100.0
    dt = 1e-9
    runs_per_cell = 20
    base_seed = 2024
    e_ch = 0.02

    cells = [
        (1_000_000, 0.70),
        (1_000_000, 0.90),
        (10_000_000, 0.70),
        (10_000_000, 0.90),
    ]
    margins = [0.005, 0.010, 0.020]

    results = []
    print("Running Task 0f Q_tol Sensitivity Evaluation...")
    for N, p_k in cells:
        for m in margins:
            Q_tol = e_ch + m
            fk_rates = []
            aborted = []
            ez_ests = []

            for r in range(runs_per_cell):
                rng = np.random.default_rng(base_seed + r)
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
                    ec_leakage_model="q_tol",
                    f_ec=1.16,
                    eps_sec=1e-10,
                    eps_cor=1e-10,
                )
                fk_rates.append(res["finite_key_bits_per_pulse"])
                aborted.append(1 if res["aborted"] else 0)
                ez_ests.append(res["e_Z_est"])

            summary = {
                "e_channel": e_ch,
                "N": N,
                "p_key": p_k,
                "p_test": round(1.0 - p_k, 2),
                "margin": m,
                "Q_tol": Q_tol,
                "yield_mean": float(np.mean(fk_rates)),
                "yield_std": float(np.std(fk_rates, ddof=1)),
                "abort_rate": float(np.mean(aborted)),
                "ez_est_mean": float(np.mean(ez_ests)),
            }
            results.append(summary)
            print(
                f"N={N:e}, p_key={p_k:.2f}, margin={m*100:.1f}%, Q_tol={Q_tol*100:.1f}% -> "
                f"Yield={summary['yield_mean']:.4e}, Abort={summary['abort_rate']:.2f}"
            )

    elapsed = time.time() - start_time

    # Output CSV and metadata
    os.makedirs(os.path.join(_REPO_ROOT, "experiments/results_final"), exist_ok=True)
    csv_path = os.path.join(_REPO_ROOT, "experiments/results_final/task0f_qtol_sensitivity.csv")
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(results[0].keys()))
        writer.writeheader()
        for row in results:
            writer.writerow(row)

    meta_path = os.path.join(_REPO_ROOT, "experiments/results_final/task0f_qtol_sensitivity.metadata.json")
    try:
        git_hash = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=_REPO_ROOT, text=True
        ).strip()
    except Exception:
        git_hash = "unknown"

    metadata = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "git_hash": git_hash,
        "runtime_seconds": elapsed,
        "parameters": {
            "e_channel": e_ch,
            "cells": cells,
            "margins": margins,
            "runs_per_cell": runs_per_cell,
            "base_seed": base_seed,
        },
    }
    with open(meta_path, "w") as f:
        json.dump(metadata, f, indent=2)

    return results


def print_table(results: list[dict[str, Any]]):
    print("\n### Task 0f: Q_tol Margin Sensitivity ($e_{\\text{channel}} = 2\\%$)")
    print("| $N$ | $p_{\\text{key}}$ | Margin | $Q_{\\text{tol}}$ | Yield (bits/pulse) | Abort Rate | Note |")
    print("|---|---|---|---|---|---|---|")
    for r in results:
        note = ""
        if r["abort_rate"] > 0:
            note = f"Aborts {r['abort_rate']*100:.0f}% due to fluctuation exceeding $Q_{{\\text{{tol}}}}$"
        elif r["yield_mean"] == 0:
            note = "Zero yield (finite-key penalty dominates)"
        else:
            note = "Nominal positive yield"
        print(
            f"| {r['N']:.0e} | {r['p_key']:.2f} | {r['margin']*100:.1f}% | {r['Q_tol']*100:.1f}% | "
            f"{r['yield_mean']:.4e} | {r['abort_rate']:.2f} | {note} |"
        )


if __name__ == "__main__":
    res = run_qtol_sensitivity()
    print_table(res)
