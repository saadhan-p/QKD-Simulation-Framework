"""
experiments/scripts/validate_yield_model.py
===========================================
Validates expected_finite_yield against Monte Carlo simulations
for 16 diverse parameter settings.
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

import numpy as np

from backend.channel import attenuation
from backend.protocols.lca import run_lca
from backend.yield_model import expected_finite_yield


def run_validation() -> list[dict[str, Any]]:
    eta_det = 0.10
    dc = 100.0
    dt = 1e-9
    trials = 50
    base_seed = 3000

    settings = [
        # (L, e_ch, N, p_key, margin)
        (10.0, 0.01, 1_000_000, 0.70, 0.010),
        (10.0, 0.01, 1_000_000, 0.85, 0.010),
        (10.0, 0.02, 2_000_000, 0.75, 0.010),
        (10.0, 0.02, 5_000_000, 0.90, 0.005),
        (20.0, 0.01, 1_000_000, 0.70, 0.010),
        (20.0, 0.01, 2_000_000, 0.80, 0.010),
        (20.0, 0.02, 1_000_000, 0.70, 0.010),
        (20.0, 0.02, 1_000_000, 0.90, 0.010),
        (20.0, 0.02, 5_000_000, 0.85, 0.005),
        (20.0, 0.03, 5_000_000, 0.75, 0.015),
        (20.0, 0.05, 5_000_000, 0.65, 0.020),
        (30.0, 0.01, 2_000_000, 0.70, 0.010),
        (30.0, 0.02, 5_000_000, 0.75, 0.010),
        (30.0, 0.02, 10_000_000, 0.85, 0.010),
        (30.0, 0.03, 10_000_000, 0.70, 0.015),
        (30.0, 0.05, 10_000_000, 0.60, 0.020),
    ]

    results = []
    print(f"Running validation on {len(settings)} settings ({trials} MC trials each)...")

    for i, (L, e_ch, N, p_k, margin) in enumerate(settings, 1):
        eta_ch = attenuation(L)
        # Total detection prob per pulse: signal + dark counts
        g = eta_ch * eta_det + 2.0 * dc * dt
        # Dark count background contributes to error
        e_effective = (e_ch * eta_ch * eta_det + 0.5 * 2.0 * dc * dt) / g
        Q_tol = e_ch + margin

        # Predictor evaluation
        pred_rate, pred_p_non_abort = expected_finite_yield(
            g=g,
            e_key=e_effective,
            e_test=e_effective,
            N=N,
            p_key=p_k,
            Q_tol=Q_tol,
            params={"f_ec": 1.16, "eps_sec": 1e-10, "eps_cor": 1e-10, "ec_leakage_model": "predetermined_Qtol"},
        )

        # Monte Carlo simulation
        mc_rates = []
        mc_non_aborts = []
        for r in range(trials):
            rng = np.random.default_rng(base_seed + r)
            sim_res = run_lca(
                n_sent=N,
                rng=rng,
                p_key=p_k,
                eta_ch=eta_ch,
                eta_det=eta_det,
                e_channel=e_ch,
                dc=dc,
                dt=dt,
                Q_tol=Q_tol,
                ec_leakage_model="predetermined_Qtol",
                f_ec=1.16,
                eps_sec=1e-10,
                eps_cor=1e-10,
            )
            mc_rates.append(sim_res["finite_key_bits_per_pulse"])
            mc_non_aborts.append(0.0 if sim_res["aborted"] else 1.0)

        mc_rate_mean = float(np.mean(mc_rates))
        mc_rate_std = float(np.std(mc_rates, ddof=1))
        mc_non_abort_mean = float(np.mean(mc_non_aborts))

        # Relative error
        denom = max(mc_rate_mean, 1e-7)
        rel_err_rate = abs(pred_rate - mc_rate_mean) / denom if mc_rate_mean > 0 else (0.0 if pred_rate == 0.0 else 1.0)
        rel_err_abort = abs(pred_p_non_abort - mc_non_abort_mean)

        row = {
            "setting_idx": i,
            "L_km": L,
            "e_channel": e_ch,
            "N": N,
            "p_key": p_k,
            "margin": margin,
            "Q_tol": Q_tol,
            "pred_rate": pred_rate,
            "mc_rate_mean": mc_rate_mean,
            "mc_rate_std": mc_rate_std,
            "rel_err_rate": rel_err_rate,
            "pred_p_non_abort": pred_p_non_abort,
            "mc_p_non_abort": mc_non_abort_mean,
            "abs_err_p_non_abort": rel_err_abort,
        }
        results.append(row)
        print(
            f"[{i:02d}/16] L={L:4.1f}km e={e_ch:.2f} N={N:.0e} p_k={p_k:.2f} | "
            f"Pred_Rate={pred_rate:.4e} MC_Rate={mc_rate_mean:.4e} (rel err={rel_err_rate*100:5.2f}%) | "
            f"Pred_NonAbort={pred_p_non_abort:.2f} MC_NonAbort={mc_non_abort_mean:.2f}"
        )

    # Save to CSV
    os.makedirs(os.path.join(_REPO_ROOT, "experiments/results_final"), exist_ok=True)
    csv_path = os.path.join(_REPO_ROOT, "experiments/results_final/task1_yield_model_validation.csv")
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(results[0].keys()))
        writer.writeheader()
        for r in results:
            writer.writerow(r)

    # Save metadata JSON
    meta_path = os.path.join(_REPO_ROOT, "experiments/results_final/task1_yield_model_validation.metadata.json")
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
        "trials_per_setting": trials,
        "num_settings": len(settings),
        "output_csv": "experiments/results_final/task1_yield_model_validation.csv",
    }
    with open(meta_path, "w") as f:
        json.dump(metadata, f, indent=2)

    return results


def print_markdown(results: list[dict[str, Any]]):
    print("\n### Task 1: Expected-Yield Predictor Validation vs Monte Carlo (50 trials/setting)\n")
    print("| Setting | $L$ (km) | $e_{\\text{channel}}$ | $N$ | $p_{\\text{key}}$ | Margin | Pred Rate | MC Rate (mean $\\pm$ std) | Rate Rel Err | Pred $P_{\\text{pass}}$ | MC $P_{\\text{pass}}$ |")
    print("|---|---|---|---|---|---|---|---|---|---|---|")
    for r in results:
        print(
            f"| {r['setting_idx']:02d} | {r['L_km']:.0f} | {r['e_channel']*100:.1f}% | {r['N']:.0e} | "
            f"{r['p_key']:.2f} | {r['margin']*100:.1f}% | {r['pred_rate']:.4e} | "
            f"{r['mc_rate_mean']:.4e} $\\pm$ {r['mc_rate_std']:.2e} | {r['rel_err_rate']*100:.2f}% | "
            f"{r['pred_p_non_abort']:.3f} | {r['mc_p_non_abort']:.3f} |"
        )


if __name__ == "__main__":
    res = run_validation()
    print_markdown(res)
