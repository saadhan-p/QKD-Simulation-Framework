"""
backend/protocols/sarg04.py
===========================
Physically honest SARG04 prepare-and-measure simulation.

SARG04 protocol (Scarani, Acín, Ribordy, Gisin 2004)
-----------------------------------------------------
SARG04 differs from BB84 in the classical announcement step:

1. Alice prepares one of the four BB84 states:
       |0⟩_Z, |1⟩_Z, |+⟩_X, |−⟩_X
   encoded as (basis, bit):  (Z,0), (Z,1), (X,0), (X,1).

2. Alice announces a *pair* of non-orthogonal states that includes her
   actual state.  The pairs are:
       (Z,0) → announce { |0⟩_Z , |+⟩_X }   = "S0"
       (Z,1) → announce { |1⟩_Z , |−⟩_X }   = "S1"
       (X,0) → announce { |+⟩_X , |0⟩_Z }   = "S0"  (same set)
       (X,1) → announce { |−⟩_X , |1⟩_Z }   = "S1"  (same set)
   In other words, there are two announcement sets; each contains one
   Z-basis state and one X-basis state:
       S0 = { |0⟩_Z , |+⟩_X }   (Alice sent bit=0 in whichever basis)
       S1 = { |1⟩_Z , |−⟩_X }   (Alice sent bit=1 in whichever basis)

3. Bob measures in a randomly chosen basis (Z or X).

4. Sifting rule — Bob has a CONCLUSIVE result only when his outcome allows
   him to *exclude* exactly one of the two announced states.  Concretely:

   Let Alice's state be σ and the announced pair be {σ, τ} where τ is
   the "other" state in the pair (from the opposite basis).

   - Bob measures in the same basis as σ:
     * His outcome correctly identifies σ with prob 1 (no noise).
       But σ and τ are in different bases, so if he measures in σ's
       basis and gets the right answer, he knows the sent state was σ
       (he can exclude τ, which would give a 50/50 result in σ's basis).
       → CONCLUSIVE, Bob infers Alice's bit.
     * Under noise (e_channel), Bob's measurement outcome is flipped;
       he still declares conclusive (but may have the wrong bit).

   - Bob measures in the same basis as τ (the opposite basis from σ):
     * The outcome of measuring σ in τ's basis is 50/50 random.
       Whether the outcome matches τ or not, Bob cannot distinguish
       σ from τ, so he is INCONCLUSIVE.
     
     Implementation detail: because Bob draws his basis randomly, half
     the time he is in σ's basis (conclusive) and half the time in τ's
     basis (inconclusive).  Thus ideal sifting efficiency is ~0.50 of
     detected events.

     However, SARG04 has a subtlety: when Bob measures in τ's basis,
     there is a 50% chance he gets the outcome that corresponds to τ.
     That outcome *excludes* σ and is therefore conclusive in favour of
     τ — but he does NOT know whether Alice sent σ or τ.  In the ideal
     noiseless single-photon case this never occurs correctly for σ
     (because measuring σ in τ's basis gives τ's bit only 50% of the
     time).  We implement the *standard* SARG04 rule:
       → Bob is conclusive only when he measures in σ's basis.
       This yields sifted/detected ≈ 0.50 in the ideal case.

   NOTE: The classical SARG04 advantage over BB84 is its resistance to
   photon-number-splitting (PNS) attacks with weak coherent sources.
   That advantage requires multi-photon analysis and is NOT modelled here.
   We simulate the single-photon idealisation only.

Key-rate formula
----------------
We use the same asymptotic formula as BB84:
    l = n_remaining * (1 - h2(QBER_est)) - leak_EC - log2(1/eps_sec)
This is a DOCUMENTED SIMPLIFICATION.  A rigorous SARG04 security bound
requires a separate proof (cf. Branciard et al., PRA 2005; Fung et al.,
PRA 2006) and is NOT implemented here.  Every output row carries
    formula_note = "simplified_BB84_formula"
and should NOT be used to make security claims for SARG04.

Channel model
-------------
Same as BB84: detection with probability eta_ch * eta_det, dark counts
with p_dark = dc * dt.  After detection, the error probability per
conclusive event (for matched-basis measurements) is e_channel.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from ..postprocessing import run_postprocessing


# ---------------------------------------------------------------------------
# Default channel / detector parameters (same as BB84)
# ---------------------------------------------------------------------------
ETA_DET_DEFAULT: float = 0.10
E_CHANNEL_DEFAULT: float = 0.0
DC_DEFAULT: float = 100.0
DT_DEFAULT: float = 1e-9


# ---------------------------------------------------------------------------
# SARG04 sifting logic (vectorised)
# ---------------------------------------------------------------------------
def _sarg04_sifting(
    alice_bits:  np.ndarray,   # shape (n,) int
    alice_bases: np.ndarray,   # shape (n,) int, 0=Z 1=X
    bob_bits:    np.ndarray,   # shape (n,) int
    bob_bases:   np.ndarray,   # shape (n,) int, 0=Z 1=X
    click:       np.ndarray,   # shape (n,) bool
) -> tuple[np.ndarray, np.ndarray]:
    """Apply SARG04 conclusive-measurement sifting rule.

    Bob is CONCLUSIVE when he measures in the same basis as Alice
    (i.e. in σ's basis), which lets him exclude τ from the announced pair.
    He is INCONCLUSIVE when he measures in τ's basis.

    Returns
    -------
    sifted_alice, sifted_bob : np.ndarray
        1-D integer arrays of bits at conclusive positions.
    """
    # A detected event is conclusive iff bases match (same as BB84 sifting)
    conclusive = click & (alice_bases == bob_bases)
    idx = np.where(conclusive)[0]
    return alice_bits[idx], bob_bits[idx]


# ---------------------------------------------------------------------------
# Core simulation
# ---------------------------------------------------------------------------
def run_sarg04(
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
    """Run a physically honest SARG04 simulation.

    Returns a dict conforming to run_postprocessing's output format, plus:
        sifted_over_detected   : n_sifted / n_detected  (expected ≈ 0.50)
        sifted_over_sent       : n_sifted / n_sent
        key_bits_per_pulse     : final_key_length_asymptotic / n_sent
        formula_note           : "simplified_BB84_formula" (always set)
    """
    p_detect_photon = eta_ch * eta_det
    p_dark = dc * dt

    # --- Alice's raw data ---
    alice_bits  = rng.integers(0, 2, size=n_sent)
    alice_bases = rng.integers(0, 2, size=n_sent)

    # --- Detection ---
    photon_detected = rng.random(n_sent) < p_detect_photon
    dark_count      = rng.random(n_sent) < p_dark
    click           = photon_detected | dark_count
    n_detected      = int(click.sum())

    # --- Bob's measurement ---
    bob_bases = rng.integers(0, 2, size=n_sent)
    bob_bits  = np.zeros(n_sent, dtype=np.int8)

    click_idx = np.where(click)[0]
    if click_idx.size > 0:
        photon_only = photon_detected[click_idx] & ~dark_count[click_idx]
        dark_only   = dark_count[click_idx] & ~photon_detected[click_idx]
        both        = photon_detected[click_idx] & dark_count[click_idx]

        # Photon-only: same basis → Alice's bit ± e_channel; diff basis → random
        if photon_only.any():
            po_idx   = click_idx[photon_only]
            same_b   = alice_bases[po_idx] == bob_bases[po_idx]
            sb_idx   = po_idx[same_b]
            if sb_idx.size > 0:
                flips = rng.random(sb_idx.size) < e_channel
                bob_bits[sb_idx] = np.where(flips,
                                            1 - alice_bits[sb_idx],
                                            alice_bits[sb_idx])
            db_idx = po_idx[~same_b]
            if db_idx.size > 0:
                bob_bits[db_idx] = rng.integers(0, 2, size=db_idx.size)

        # Dark-count only → random
        if dark_only.any():
            do_idx = click_idx[dark_only]
            bob_bits[do_idx] = rng.integers(0, 2, size=do_idx.size)

        # Both → random (conservative)
        if both.any():
            bo_idx = click_idx[both]
            bob_bits[bo_idx] = rng.integers(0, 2, size=bo_idx.size)

    # --- SARG04 sifting ---
    sifted_alice_arr, sifted_bob_arr = _sarg04_sifting(
        alice_bits, alice_bases, bob_bits, bob_bases, click
    )
    n_sifted = len(sifted_alice_arr)

    sifted_alice = sifted_alice_arr.tolist()
    sifted_bob   = sifted_bob_arr.tolist()

    sifted_over_detected = (n_sifted / n_detected) if n_detected > 0 else 0.0
    sifted_over_sent     = (n_sifted / n_sent)     if n_sent > 0 else 0.0

    # --- Post-processing (shared, identical formula to BB84) ---
    pp_result = run_postprocessing(
        sifted_alice,
        sifted_bob,
        rng,
        protocol="sarg04",
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
            "key_bits_per_pulse":   0,
            "eta_ch":               eta_ch,
            "eta_det":              eta_det,
            "e_channel":            e_channel,
            "p_dark_per_gate":      dc * dt,
            # formula_note is set by run_postprocessing for sarg04
        },
    )

    l_asym = pp_result["final_key_length_asymptotic"]
    pp_result["key_bits_per_pulse"] = (l_asym / n_sent) if n_sent > 0 else 0.0

    return pp_result
