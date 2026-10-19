#!/usr/bin/env python3
"""
experiments/scripts/sanity_sweep.py
====================================
Quick sanity sweep for the deliverable table.

Runs BB84 and SARG04 (Aurora provisional) at:
  n_sent = 100,000 pulses
  eta_ch from L = 20 km  (10^(-0.2*20/10) ≈ 0.1)
  eta_det = 0.10 (default)
  QBER settings: 2%, 5%, 8%, 11%, 15%  → injected via e_channel
  20 runs per (protocol, QBER) using SeedSequence child streams

Usage:
    python experiments/scripts/sanity_sweep.py [--seed SEED]

Output:
    - Console table
    - experiments/results/raw_data/sanity_sweep.csv
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from statistics import mean

import numpy as np

# Make the project root importable
_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_root))

from backend.channel import attenuation
from backend.protocols.bb84 import run_bb84
from backend.protocols.sarg04 import run_sarg04
from backend.protocols.aurora_qkd import run_aurora


# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────
N_SENT      = 100_000
N_RUNS      = 20
DISTANCE_KM = 20.0
ETA_DET     = 0.10
DC          = 100.0      # Hz
DT          = 1e-9       # s
QBER_LEVELS = [0.02, 0.05, 0.08, 0.11, 0.15]
PROTOCOLS   = ["bb84", "sarg04", "aurora"]


def run_protocol(
    protocol: str,
    n_sent: int,
    eta_ch: float,
    e_channel: float,
    rng: np.random.Generator,
) -> dict:
    """Dispatch to the correct protocol runner."""
    common = dict(
        eta_ch=eta_ch, eta_det=ETA_DET,
        e_channel=e_channel, dc=DC, dt=DT,
        sample_fraction=0.10, sample_min=100,
    )
    if protocol == "bb84":
        return run_bb84(n_sent, rng, **common)
    elif protocol == "sarg04":
        return run_sarg04(n_sent, rng, **common)
    elif protocol == "aurora":
        # Aurora doesn't accept per-pulse channel params yet (provisional).
        # We pass qber = e_channel as the "base QBER" and use its own channel model.
        return run_aurora(
            raw_key_length=n_sent,
            block_size=200,
            qber=e_channel,
            rng=rng,
            legacy=False,
            sample_fraction=0.10,
            sample_min=100,
        )
    else:
        raise ValueError(f"Unknown protocol: {protocol}")


def main(base_seed: int = 2024):
    eta_ch = attenuation(DISTANCE_KM)

    # SeedSequence for independent child streams
    ss = np.random.SeedSequence(base_seed)
    run_idx = 0
    # pre-generate enough child seeds
    total_runs = len(PROTOCOLS) * len(QBER_LEVELS) * N_RUNS
    child_seeds = ss.spawn(total_runs)

    rows = []
    summary: dict[tuple, list] = {}   # (proto, qber) -> list of result dicts

    print(f"\n{'='*72}")
    print(f"  Sanity sweep  |  L={DISTANCE_KM} km  |  eta_ch={eta_ch:.4f}  |  "
          f"eta_det={ETA_DET}  |  seed={base_seed}")
    print(f"{'='*72}")

    for protocol in PROTOCOLS:
        for qber in QBER_LEVELS:
            key = (protocol, qber)
            summary[key] = []
            for run_num in range(1, N_RUNS + 1):
                rng = np.random.default_rng(child_seeds[run_idx])
                per_run_seed_int = int(child_seeds[run_idx].entropy)  # type: ignore[attr-defined]
                run_idx += 1

                result = run_protocol(protocol, N_SENT, eta_ch, qber, rng)

                n_sifted  = result.get("n_sifted", 0)
                n_det     = result.get("n_detected", n_sifted)  # Aurora fallback
                qber_est  = result.get("qber_est") or 0.0
                l_asym    = result.get("final_key_length_asymptotic", 0)
                aborted   = result.get("aborted", False)
                s_o_det   = result.get("sifted_over_detected",
                                       n_sifted / n_det if n_det else 0.0)
                s_o_sent  = result.get("sifted_over_sent",
                                       n_sifted / N_SENT if N_SENT else 0.0)

                row = {
                    "protocol":         protocol,
                    "n_sent":           N_SENT,
                    "distance_km":      DISTANCE_KM,
                    "eta_ch":           eta_ch,
                    "eta_det":          ETA_DET,
                    "qber_injected":    qber,
                    "run_number":       run_num,
                    "base_seed":        base_seed,
                    "per_run_seed":     per_run_seed_int,
                    "n_detected":       n_det,
                    "n_sifted":         n_sifted,
                    "sifted_over_detected": round(s_o_det, 5),
                    "sifted_over_sent":     round(s_o_sent, 5),
                    "qber_est":         round(qber_est, 6) if qber_est is not None else None,
                    "final_key_asym":   l_asym,
                    "aborted":          int(aborted),
                    "aurora_provisional": int(result.get("aurora_provisional", False)),
                    "formula_note":     result.get("formula_note", ""),
                }
                rows.append(row)
                summary[key].append(result)

    # ── Save CSV ──
    out_path = _root / "experiments" / "results" / "raw_data" / "sanity_sweep.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nRaw CSV → {out_path}")

    from experiments.scripts.sweep_metadata import save_sweep_metadata
    meta_path = save_sweep_metadata(out_path, base_seed)
    print(f"Metadata → {meta_path}\n")

    # ── Print summary table ──
    hdr = f"{'Protocol':<10} {'QBER%':>6} {'sift/det':>9} {'sift/sent':>10} "
    hdr += f"{'QBER_est%':>10} {'KeyAsym(mean)':>14} {'Abort%':>8}"
    print(hdr)
    print("-" * 72)
    for protocol in PROTOCOLS:
        for qber in QBER_LEVELS:
            results = summary[(protocol, qber)]
            s_det_vals = [r.get("sifted_over_detected",
                                r.get("n_sifted", 0) / max(r.get("n_detected", 1), 1))
                          for r in results]
            s_sent_vals = [r.get("sifted_over_sent",
                                 r.get("n_sifted", 0) / N_SENT)
                           for r in results]
            qber_vals   = [r.get("qber_est") or 0.0 for r in results]
            key_vals    = [r.get("final_key_length_asymptotic", 0) for r in results]
            aborts      = [r.get("aborted", False) for r in results]

            prov_tag = " [PROV]" if protocol == "aurora" else ""
            print(
                f"{protocol:<10}{prov_tag if prov_tag else ''}"[: 10] +
                f" {qber*100:>5.0f}%"
                f" {mean(s_det_vals):>9.4f}"
                f" {mean(s_sent_vals):>10.5f}"
                f" {mean(qber_vals)*100:>9.2f}%"
                f" {mean(key_vals):>14.1f}"
                f" {sum(aborts)/len(aborts)*100:>7.0f}%"
                + (" [PROV]" if protocol == "aurora" else "")
            )

    print(f"\nNote: Aurora marked [PROV] = provisional (physics engine not yet redesigned).")
    print(f"Note: SARG04 uses simplified BB84 formula for key length.")
    print(f"Numbers are as measured — not compared to any prior paper results.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="QKD sanity sweep")
    parser.add_argument("--seed", type=int, default=2024, help="Base random seed")
    args = parser.parse_args()
    main(base_seed=args.seed)
