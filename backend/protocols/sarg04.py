"""
backend/protocols/sarg04.py
===========================
Physically honest SARG04 prepare-and-measure simulation.

SARG04 protocol (Scarani, Acín, Ribordy, Gisin 2004)
------------------------------------------------------
SARG04 differs from BB84 only in the *classical announcement*:

1. Alice prepares one of four BB84 states |0⟩_Z, |1⟩_Z, |+⟩_X, |−⟩_X.

2. She announces a PAIR of non-orthogonal states that includes her actual
   state.  There are two pairs:
       S0 = {|0⟩_Z, |+⟩_X}   (both encode bit = 0)
       S1 = {|1⟩_Z, |−⟩_X}   (both encode bit = 1)

   Mapping from (alice_basis, alice_bit) → announced pair:
       (Z, 0) → S0;   (X, 0) → S0
       (Z, 1) → S1;   (X, 1) → S1
   So the pair is determined entirely by alice_bit.

3. Bob measures in a randomly chosen basis (Z or X).

4. SARG04 conclusive-event rule (derived from first principles):

   Let Alice's state be σ = (alice_basis, alice_bit).  The announced pair
   is S_{alice_bit} = {σ, τ}, where the OTHER state τ has
       τ_basis = 1 - alice_basis   (opposite basis to σ)
       τ_bit   = alice_bit         (same bit value as σ)

   Bob can exclude one member of {σ, τ} only if his outcome is
   ORTHOGONAL to that member.  In discrete-variable QKD, two states in
   the same basis are orthogonal iff their bit values differ.  States in
   different bases are never orthogonal (overlap = 1/√2).

   Therefore Bob can exclude τ only if:
       (a) bob_basis == τ_basis  (measures in τ's basis)  AND
       (b) bob_raw_bit ≠ τ_bit  (gets the bit orthogonal to τ in that basis)

   Substituting τ_basis = 1-alice_basis, τ_bit = alice_bit:
       (a) bob_basis ≠ alice_basis  (cross-basis measurement)
       (b) bob_raw_bit ≠ alice_bit  (excluding outcome)

   Probability of conclusive event (ideal, no loss):
       P(a) = 1/2  (independent basis choices)
       P(b | a) = 1/2  (Bob's cross-basis measurement is uniformly random)
       P(conclusive) = 1/4

   This gives sifted/detected ≈ 0.25, compared with ≈ 0.50 for BB84.

   Worked example:  Alice sends |0⟩_Z, announces S0 = {|0⟩_Z, |+⟩_X}.
   - Bob in Z: gets |0⟩.  |0⟩ is consistent with |0⟩_Z (prob 1) and
     with |+⟩_X (prob 1/2).  Neither is excluded. → INCONCLUSIVE.
   - Bob in X: gets |+⟩ (prob 1/2) or |−⟩ (prob 1/2).
     * |+⟩ result: |+⟩_X gives |+⟩ with prob 1; consistent. INCONCLUSIVE.
     * |−⟩ result: |+⟩_X gives |−⟩ with prob 0 (orthogonal → excluded).
       Bob deduces Alice sent |0⟩_Z, infers bit = 0. → CONCLUSIVE.

   Note: measuring in Alice's OWN basis (Z here) is always inconclusive,
   because σ gives a deterministic result while τ (from X basis) gives
   50/50 in Z, so the same outcome is consistent with both states.

Bob's key bit for conclusive events
------------------------------------
When Bob's measurement in bob_basis = τ_basis = 1-alice_basis gives a
result that EXCLUDES τ, he deduces Alice sent σ, so his key bit equals
alice_bit (inferred from the pair label S0 or S1).

In the noiseless ideal, bob_raw_bit = 1-alice_bit for a conclusive event.
To recover alice_bit, Bob does NOT use his raw bit; he uses the announced
pair label.  In the simulation we set bob_key_bit = alice_bit directly for
photon-only events, then apply e_channel as an additive error probability.

Dark-count events that accidentally satisfy the conclusive condition
contribute QBER ≈ 0.5 (the dark count outcome is uncorrelated with
alice_bit, so the key bit is random from the pair label).

QBER approximation from dark counts (same formula as BB84):
    QBER_dc ≈ 0.5 × p_dark / (eta_ch × eta_det)
Regime: p_dark << eta_ch × eta_det.

SARG04 advantage over BB84
----------------------------
SARG04's lower sifted/detected (1/4 vs 1/2) is the price paid in the
single-photon case.  The protocol's actual advantage is resistance to
photon-number-splitting (PNS) attacks in the WEAK COHERENT PULSE regime,
which requires multi-photon modelling NOT implemented here.  In the
simulated single-photon case, SARG04 produces fewer sifted bits per
detected photon than BB84.

Key-rate formula
-----------------
Same asymptotic formula as BB84 — DOCUMENTED SIMPLIFICATION.  A rigorous
SARG04 bound (Branciard et al. PRA 2005; Fung et al. PRA 2006) is NOT
implemented.  All output rows carry formula_note = "simplified_BB84_formula".
Do NOT use these numbers for security claims.

Channel model
-------------
Same as BB84: eta_ch * eta_det detection probability, p_dark = dc * dt
dark counts.  Channel error e_channel applied at the key-bit level for
photon-only conclusive events.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from ..postprocessing import run_postprocessing


# ---------------------------------------------------------------------------
# Default channel / detector parameters (same as BB84)
# ---------------------------------------------------------------------------
ETA_DET_DEFAULT:   float = 0.10
E_CHANNEL_DEFAULT: float = 0.0
DC_DEFAULT:        float = 100.0    # Hz
DT_DEFAULT:        float = 1e-9    # s


# ---------------------------------------------------------------------------
# Core simulation
# ---------------------------------------------------------------------------
def run_sarg04(
    n_sent: int,
    rng: np.random.Generator,
    *,
    eta_ch:       float = 1.0,
    eta_det:      float = ETA_DET_DEFAULT,
    e_channel:    float = E_CHANNEL_DEFAULT,
    dc:           float = DC_DEFAULT,
    dt:           float = DT_DEFAULT,
    # postprocessing kwargs
    sample_fraction: float = 0.10,
    sample_min:      int   = 100,
    f_ec:            float = 1.16,
    eps_sec:         float = 1e-6,
    eps_pe:          float = 1e-6,
) -> dict[str, Any]:
    """Run a physically honest SARG04 simulation.

    Returns a dict conforming to run_postprocessing's output format, plus:
        sifted_over_detected : n_sifted / n_detected  (expected ≈ 0.25 ideal)
        sifted_over_sent     : n_sifted / n_sent
        key_bits_per_pulse   : final_key_length_asymptotic / n_sent
        formula_note         : "simplified_BB84_formula" (always)
    """
    p_detect_photon = eta_ch * eta_det
    p_dark          = dc * dt

    # ── Alice's raw data ──────────────────────────────────────────────────
    alice_bits  = rng.integers(0, 2, size=n_sent)   # int8-compatible
    alice_bases = rng.integers(0, 2, size=n_sent)   # 0=Z, 1=X

    # ── Detection ─────────────────────────────────────────────────────────
    photon_detected = rng.random(n_sent) < p_detect_photon
    dark_count      = rng.random(n_sent) < p_dark
    click           = photon_detected | dark_count
    n_detected      = int(click.sum())

    # ── Bob's basis choices ───────────────────────────────────────────────
    bob_bases = rng.integers(0, 2, size=n_sent)

    # ── Bob's RAW measurement outcomes ────────────────────────────────────
    # For SARG04 we need raw outcomes for ALL detected events.
    # For photon-only events:
    #   - same basis as Alice → alice_bit (deterministic, noiseless channel)
    #     (e_channel is applied at the KEY BIT stage for conclusive events,
    #      not here, because same-basis events are never conclusive in SARG04)
    #   - different basis → uniformly random bit
    # For dark-count events: uniformly random bit.
    bob_raw = np.zeros(n_sent, dtype=np.int8)

    click_idx = np.where(click)[0]
    if click_idx.size > 0:
        photon_only = photon_detected[click_idx] & ~dark_count[click_idx]
        dark_only   = dark_count[click_idx]       & ~photon_detected[click_idx]
        both        = photon_detected[click_idx]  & dark_count[click_idx]

        # Photon-only
        if photon_only.any():
            po_idx = click_idx[photon_only]
            same_b = alice_bases[po_idx] == bob_bases[po_idx]

            # Same basis (never conclusive in SARG04): deterministic, noiseless
            sb_idx = po_idx[same_b]
            if sb_idx.size > 0:
                bob_raw[sb_idx] = alice_bits[sb_idx]

            # Opposite basis (potentially conclusive): uniformly random
            db_idx = po_idx[~same_b]
            if db_idx.size > 0:
                bob_raw[db_idx] = rng.integers(0, 2, size=db_idx.size)

        # Dark-count only → uniformly random
        if dark_only.any():
            do_idx = click_idx[dark_only]
            bob_raw[do_idx] = rng.integers(0, 2, size=do_idx.size)

        # Both photon + dark count → conservative: uniformly random
        if both.any():
            bo_idx = click_idx[both]
            bob_raw[bo_idx] = rng.integers(0, 2, size=bo_idx.size)

    # ── SARG04 conclusive-event sifting ───────────────────────────────────
    # Conclusive iff:
    #   (a) click (a detection occurred)
    #   (b) bob_bases ≠ alice_bases  (cross-basis: Bob measured in τ's basis)
    #   (c) bob_raw ≠ alice_bits     (excluding outcome: orthogonal to τ)
    #
    # Expected P(conclusive | click) = P(b) × P(c|b) = 1/2 × 1/2 = 1/4
    conclusive_mask = (
        click
        & (bob_bases != alice_bases)     # cross-basis
        & (bob_raw   != alice_bits)      # excluding outcome
    )
    sift_idx  = np.where(conclusive_mask)[0]
    n_sifted  = sift_idx.size

    # ── Bob's KEY BITS for conclusive events ──────────────────────────────
    # For a conclusive event Bob infers that Alice's state was σ (the one
    # he excluded τ from).  Alice's key bit = alice_bits[i] (from pair label).
    #
    # Photon-only conclusive events: key bit = alice_bit ± e_channel error.
    # Dark-count conclusive events: key bit is RANDOM (dark count is
    # uncorrelated with alice_bit, so QBER from dark counts ≈ 0.5).
    sifted_alice = alice_bits[sift_idx]

    # Start with the correct key bit (alice's bit)
    correct_key  = alice_bits[sift_idx].copy()

    # Mask: is this conclusive event a photon-only event?
    is_photon = photon_detected[sift_idx] & ~dark_count[sift_idx]

    # Photon-only: apply e_channel error
    error_flip  = rng.random(n_sifted) < e_channel
    photon_bob  = np.where(error_flip, 1 - correct_key, correct_key).astype(np.int8)

    # Dark-count (or both): uniformly random key bit → QBER ≈ 0.5
    dc_bob      = rng.integers(0, 2, size=n_sifted, dtype=np.int8)

    sifted_bob  = np.where(is_photon, photon_bob, dc_bob)

    sifted_alice_list = sifted_alice.tolist()
    sifted_bob_list   = sifted_bob.tolist()

    # ── Sifting efficiency ─────────────────────────────────────────────────
    sifted_over_detected = (n_sifted / n_detected) if n_detected > 0 else 0.0
    sifted_over_sent     = (n_sifted / n_sent)     if n_sent     > 0 else 0.0

    # ── Post-processing (shared formula, same as BB84) ────────────────────
    pp_result = run_postprocessing(
        sifted_alice_list,
        sifted_bob_list,
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
            "key_bits_per_pulse":   0,          # filled below
            "eta_ch":               eta_ch,
            "eta_det":              eta_det,
            "e_channel":            e_channel,
            "p_dark_per_gate":      dc * dt,
        },
    )

    l_asym = pp_result["final_key_length_asymptotic"]
    pp_result["key_bits_per_pulse"] = (l_asym / n_sent) if n_sent > 0 else 0.0

    return pp_result
