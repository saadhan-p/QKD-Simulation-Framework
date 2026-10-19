"""
backend/protocols/bb84.py
=========================
Physically honest BB84 prepare-and-measure simulation.

Protocol steps
--------------
1. Alice draws a random bit and random basis (Z=0, X=1) for each pulse.
2. The photon traverses the channel with transmission probability
   ``eta_ch * eta_det``.  If a photon is detected, Bob draws a random
   basis and measures:
   - Same basis as Alice → outcome = Alice bit, flipped with probability
     ``e_channel`` (the channel error parameter, optical/alignment noise).
   - Different basis → outcome = uniform random bit (BB84 security relies on
     this being truly random from an eavesdropper's view; we model it so).
3. Dark counts: each time slot has a probability ``p_dark = dc * dt`` of
   triggering independently of the photon.  A dark-count event produces a
   random outcome bit.  If both a real photon AND a dark count would fire,
   we model the outcome as random (dark count dominates — conservative).
4. Sifting: keep detected events where Alice and Bob used the same basis.
   Discard all events where no photon was detected AND no dark count.
5. The sifted bits are passed to ``run_postprocessing`` for PE, EC leakage,
   and PA.

Sifting efficiency
------------------
- sifted / detected  ≈ 0.5  (basis matching, independent choices)
- sifted / raw_sent  ≈ 0.5 * eta_ch * eta_det  (channel loss included)

Definitions
-----------
- n_raw (n_sent)  : number of pulses Alice sent
- n_detected      : number of time slots where Bob had at least one click
                    (photon or dark count)
- n_sifted        : number of matching-basis clicks kept

Parameters
----------
n_sent : int
    Number of pulses Alice transmits.
eta_ch : float
    Channel transmission factor (0–1).  Use channel.attenuation(L) to compute.
eta_det : float
    Detector efficiency (0–1, default 0.1 — typical InGaAs SPAD at 1550 nm).
e_channel : float
    Channel error probability per detected photon in the matching-basis case.
    Models optical misalignment / polarisation rotation (default 0.0 = ideal).
dc : float
    Dark count rate in counts per second (default 100 Hz).
dt : float
    Gate / time-bin width in seconds (default 1e-9 s = 1 ns).
    Dark count probability per gate: p_dark = dc * dt.
rng : np.random.Generator
    Seeded RNG — mandatory, no global random state is used.
sample_fraction, sample_min, f_ec, eps_sec, eps_pe :
    Passed through to run_postprocessing (see that module's docstring).
"""

from __future__ import annotations

from typing import Any

import numpy as np

from ..postprocessing import run_postprocessing


# ---------------------------------------------------------------------------
# Default channel / detector parameters
# ---------------------------------------------------------------------------
ETA_DET_DEFAULT: float = 0.10   # detector efficiency
E_CHANNEL_DEFAULT: float = 0.0  # channel error probability
DC_DEFAULT: float = 100.0       # dark count rate (Hz)
DT_DEFAULT: float = 1e-9        # gate width (s)


# ---------------------------------------------------------------------------
# Core simulation
# ---------------------------------------------------------------------------
def run_bb84(
    n_sent: int,
    rng: np.random.Generator,
    *,
    eta_ch: float = 1.0,
    eta_det: float = ETA_DET_DEFAULT,
    e_channel: float = E_CHANNEL_DEFAULT,
    dc: float = DC_DEFAULT,
    dt: float = DT_DEFAULT,
    # postprocessing kwargs
    sample_fraction: float = 0.10,
    sample_min: int = 100,
    f_ec: float = 1.16,
    eps_sec: float = 1e-6,
    eps_pe: float = 1e-6,
) -> dict[str, Any]:
    """Run a physically honest BB84 simulation.

    Returns a dict conforming to run_postprocessing's output format, plus:
        sifted_over_detected   : n_sifted / n_detected
        sifted_over_sent       : n_sifted / n_sent
        key_bits_per_pulse     : final_key_length_asymptotic / n_sent
    """
    p_detect_photon = eta_ch * eta_det   # prob photon reaches and clicks
    p_dark = dc * dt                     # prob dark count per gate

    # --- Generate Alice's raw data ---
    alice_bits  = rng.integers(0, 2, size=n_sent)   # shape (n_sent,)
    alice_bases = rng.integers(0, 2, size=n_sent)   # 0=Z, 1=X

    # --- Per-pulse detection ---
    # Photon detected (independently of dark count)
    photon_detected = rng.random(n_sent) < p_detect_photon  # bool array
    # Dark count in each gate
    dark_count = rng.random(n_sent) < p_dark                 # bool array

    # A slot registers a "click" if either photon or dark count fires
    click = photon_detected | dark_count  # bool array
    n_detected = int(click.sum())

    # Bob's basis choices (for all slots — we only use them at click positions)
    bob_bases = rng.integers(0, 2, size=n_sent)

    # --- Bob's measurement outcomes ---
    # Start with all zeros; we only set values at click positions.
    bob_bits = np.zeros(n_sent, dtype=np.int8)

    click_idx = np.where(click)[0]

    if click_idx.size > 0:
        # For photon-only clicks (no dark count): deterministic outcome + error
        photon_only = photon_detected[click_idx] & ~dark_count[click_idx]
        dark_only   = dark_count[click_idx] & ~photon_detected[click_idx]
        both        = photon_detected[click_idx] & dark_count[click_idx]

        # --- Photon-only clicks ---
        if photon_only.any():
            po_idx = click_idx[photon_only]
            same_basis = alice_bases[po_idx] == bob_bases[po_idx]

            # Same basis: Alice's bit, flipped with prob e_channel
            sb_idx = po_idx[same_basis]
            if sb_idx.size > 0:
                flips = rng.random(sb_idx.size) < e_channel
                bob_bits[sb_idx] = np.where(flips, 1 - alice_bits[sb_idx], alice_bits[sb_idx])

            # Different basis: uniform random
            db_idx = po_idx[~same_basis]
            if db_idx.size > 0:
                bob_bits[db_idx] = rng.integers(0, 2, size=db_idx.size)

        # --- Dark-count only (no photon): always random ---
        if dark_only.any():
            do_idx = click_idx[dark_only]
            bob_bits[do_idx] = rng.integers(0, 2, size=do_idx.size)

        # --- Both photon and dark count: conservative → random ---
        if both.any():
            bo_idx = click_idx[both]
            bob_bits[bo_idx] = rng.integers(0, 2, size=bo_idx.size)

    # --- Sifting: keep click events where bases match ---
    # Sifting is done on detected (click) events only.
    # Non-click slots are discarded automatically by restricting to click_idx.
    sift_mask = click & (alice_bases == bob_bases)
    sift_idx = np.where(sift_mask)[0]
    n_sifted = sift_idx.size

    sifted_alice = alice_bits[sift_idx].tolist()
    sifted_bob   = bob_bits[sift_idx].tolist()

    # --- Sifting efficiency ---
    sifted_over_detected = (n_sifted / n_detected) if n_detected > 0 else 0.0
    sifted_over_sent     = (n_sifted / n_sent)     if n_sent > 0 else 0.0

    # --- Post-processing ---
    pp_result = run_postprocessing(
        sifted_alice,
        sifted_bob,
        rng,
        protocol="bb84",
        n_raw=n_sent,
        n_detected=n_detected,
        sample_fraction=sample_fraction,
        sample_min=sample_min,
        f_ec=f_ec,
        eps_sec=eps_sec,
        eps_pe=eps_pe,
        extra={
            "sifted_over_detected": sifted_over_detected,
            "sifted_over_sent":     sifted_over_sent,
            "key_bits_per_pulse":   0,  # filled below
            # channel / detector config
            "eta_ch":       eta_ch,
            "eta_det":      eta_det,
            "e_channel":    e_channel,
            "p_dark_per_gate": dc * dt,
        },
    )

    # Fill derived stat
    l_asym = pp_result["final_key_length_asymptotic"]
    pp_result["key_bits_per_pulse"] = (l_asym / n_sent) if n_sent > 0 else 0.0

    return pp_result
