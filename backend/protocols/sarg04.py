"""
backend/protocols/sarg04.py
===========================
Physically honest SARG04 prepare-and-measure simulation with simulated
measurement outcomes and outcome-flip error modeling.

SARG04 Protocol & Convention (Scarani, Acín, Ribordy, Gisin 2004)
-----------------------------------------------------------------
Reference: V. Scarani, A. Acín, G. Ribordy, N. Gisin,
"Quantum cryptography protocols robust against photon number splitting attacks for weak laser pulses",
Phys. Rev. Lett. 92, 057901 (2004).

Convention used here:
1. Four BB84 states across two mutually unbiased bases:
   - Z basis (0): |0⟩ (bit 0), |1⟩ (bit 1)
   - X basis (1): |+⟩ (bit 0), |−⟩ (bit 1)
   Bit assignment:
     |0⟩_Z -> 0,  |+⟩_X -> 0
     |1⟩_Z -> 1,  |−⟩_X -> 1

2. Classical announcement:
   Alice prepares state σ = (alice_basis, alice_bit).
   She announces a pair of non-orthogonal states {σ, τ}, where τ is a state
   from the OTHER basis with the OPPOSITE bit value:
       τ_basis = 1 - alice_basis
       τ_bit   = 1 - alice_bit
   Because σ and τ belong to different bases (Z and X), they are non-orthogonal
   (|⟨σ|τ⟩|² = 1/2). Because they carry opposite bit values, one state in the
   pair represents bit 0 and the other represents bit 1.

3. Bob's measurement:
   Bob chooses basis bob_basis in {0, 1} uniformly at random.
   - For photon events: Bob measures state σ in basis bob_basis.
     * If bob_basis == alice_basis: ideal outcome = alice_bit (prob 1).
     * If bob_basis != alice_basis: ideal outcome = 0 or 1 with prob 1/2 each
       (from quantum state overlap |⟨±|0⟩|² = 1/2).
     * Outcome-flip noise: with probability e_channel, Bob's physical detector
       outcome is flipped (e.g. optical misalignment / detector channel flip):
           actual_outcome = 1 - ideal_outcome  (prob e_channel)
           actual_outcome = ideal_outcome      (prob 1 - e_channel)
   - For dark-count clicks: Bob's detector fires spontaneously; the outcome
     in Bob's chosen basis is uniformly random in {0, 1}.

4. SARG04 conclusive-event discrimination (first principles, NO shortcuts):
   Bob tests whether his measured outcome state (bob_basis, bob_outcome)
   is orthogonal to either state in the announced pair {σ, τ}.
   In discrete-variable QKD, state (b1, o1) is orthogonal to (b2, o2) iff
   they are in the same basis (b1 == b2) and have opposite outcomes (o1 != o2).

   - perp_sigma: (bob_basis == alice_basis) and (bob_outcome != alice_bit)
   - perp_tau:   (bob_basis == tau_basis)   and (bob_outcome != tau_bit)

   Conclusive condition: Bob's outcome is orthogonal to EXACTLY ONE member:
       conclusive = click and (perp_sigma ^ perp_tau)

   Inference:
   - If perp_tau is True: Bob rules out τ. The inferred state is σ,
     so Bob's key bit is alice_bit (CORRECT).
   - If perp_sigma is True: Bob rules out σ. The inferred state is τ,
     so Bob's key bit is tau_bit = 1 - alice_bit (ERROR).
   Notice: Bob's key bit is inferred strictly from state exclusion, with NO
   shortcut bit-flips applied to the key bit.

Analytic Probabilities (Pure Outcome-Flip Model, No Dark Counts)
----------------------------------------------------------------
1. P(conclusive | detected):
   - Bob measures in τ's basis (cross-basis, prob 1/2):
     Bob can only be orthogonal to τ (never σ). Ideal outcome is orthogonal to τ
     with prob 1/2, flipped with prob e_channel.
     P(perp_tau) = (1/2)*(1 - e) + (1/2)*e = 1/2.
     All cross-basis conclusive events correctly infer σ.
     Contribution: (1/2) * (1/2) = 1/4.
   - Bob measures in σ's basis (same basis, prob 1/2):
     Bob can only be orthogonal to σ (never τ). Ideal outcome is alice_bit.
     With prob e_channel, the outcome flips to 1 - alice_bit, which is
     orthogonal to σ! Bob mistakenly excludes σ and infers τ (error).
     Contribution: (1/2) * e.
   - Total P(conclusive) = 1/4 + e/2.

2. QBER = P(error | conclusive):
   P(error and conclusive) = e/2.
   QBER = (e/2) / (1/4 + e/2) = 2e / (1 + 2e).

   Examples:
     e = 0.00 -> P(concl) = 0.2500, QBER = 0.0000
     e = 0.02 -> P(concl) = 0.2600, QBER = 0.03846 (3.85%)
     e = 0.05 -> P(concl) = 0.2750, QBER = 0.09091 (9.09%)
     e = 0.11 -> P(concl) = 0.3050, QBER = 0.18033 (18.03%)
     e = 0.15 -> P(concl) = 0.3250, QBER = 0.23077 (23.08%)

3. Dark Counts:
   Dark counts yield random outcomes in random bases. When a dark count
   accidentally satisfies the exclusion condition, it is equally likely to
   exclude σ or τ, driving the asymptotic QBER of dark-count events to 0.5.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from ..postprocessing import run_postprocessing


# ---------------------------------------------------------------------------
# Default channel / detector parameters
# ---------------------------------------------------------------------------
ETA_DET_DEFAULT:   float = 0.10
E_CHANNEL_DEFAULT: float = 0.0
DC_DEFAULT:        float = 100.0    # Hz
DT_DEFAULT:        float = 1e-9     # s


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
    """Run a physically honest SARG04 simulation with state-exclusion logic.

    Parameters
    ----------
    n_sent : int
        Number of optical pulses sent by Alice.
    rng : np.random.Generator
        Seeded NumPy random generator.
    eta_ch : float
        Channel transmission efficiency (10^(-alpha * L / 10)).
    eta_det : float
        Detector quantum efficiency.
    e_channel : float
        Physical outcome-flip error probability (misalignment/channel noise).
    dc : float
        Dark count rate in Hz.
    dt : float
        Gate width in seconds.

    Returns
    -------
    dict conforming to run_postprocessing's output format, plus:
        sifted_over_detected : n_sifted / n_detected  (expected ~ 0.25 + e/2)
        sifted_over_sent     : n_sifted / n_sent
        key_bits_per_pulse   : final_key_length_asymptotic / n_sent
        formula_note         : "simplified_BB84_formula"
        e_channel            : physical outcome-flip parameter
    """
    p_detect_photon = eta_ch * eta_det
    p_dark          = dc * dt

    # ── 1. Alice's state preparation ─────────────────────────────────────
    # Basis: 0 = Z (|0⟩, |1⟩), 1 = X (|+⟩, |−⟩)
    # Bit:   0 for {|0⟩, |+⟩}, 1 for {|1⟩, |−⟩}
    alice_bits  = rng.integers(0, 2, size=n_sent, dtype=np.int8)
    alice_bases = rng.integers(0, 2, size=n_sent, dtype=np.int8)

    # Announced pair {σ, τ}:
    # τ has the opposite basis and opposite bit value
    tau_bases = (1 - alice_bases).astype(np.int8)
    tau_bits  = (1 - alice_bits).astype(np.int8)

    # ── 2. Channel transmission & detection ──────────────────────────────
    photon_detected = rng.random(n_sent) < p_detect_photon
    dark_count      = rng.random(n_sent) < p_dark
    click           = photon_detected | dark_count
    n_detected      = int(click.sum())

    # ── 3. Bob's measurement ─────────────────────────────────────────────
    bob_bases = rng.integers(0, 2, size=n_sent, dtype=np.int8)

    # Ideal outcomes from state vector projection
    # Same basis as Alice: deterministic outcome = alice_bits
    # Cross basis: 50/50 projection onto {|0⟩, |1⟩} or {|+⟩, |−⟩}
    cross_outcomes = rng.integers(0, 2, size=n_sent, dtype=np.int8)
    ideal_outcomes = np.where(bob_bases == alice_bases, alice_bits, cross_outcomes).astype(np.int8)

    # Outcome-flip noise (e_channel) applied to physical measurement
    flips = rng.random(n_sent) < e_channel
    photon_outcomes = np.where(flips, 1 - ideal_outcomes, ideal_outcomes).astype(np.int8)

    # Dark-count outcomes: purely random in Bob's basis
    dc_outcomes = rng.integers(0, 2, size=n_sent, dtype=np.int8)

    # For clicks: photon_only uses photon_outcomes; dark_count uses dc_outcomes
    photon_only = photon_detected & ~dark_count
    bob_outcomes = np.where(photon_only, photon_outcomes, dc_outcomes).astype(np.int8)

    # ── 4. SARG04 state-exclusion discrimination ──────────────────────────
    # Check orthogonality of Bob's outcome (bob_bases, bob_outcomes) against
    # the two members of the announced pair {σ, τ}:
    # Orthogonal iff basis matches AND outcome differs.
    perp_sigma = (bob_bases == alice_bases) & (bob_outcomes != alice_bits)
    perp_tau   = (bob_bases == tau_bases)   & (bob_outcomes != tau_bits)

    # Conclusive event iff orthogonal to EXACTLY ONE member
    conclusive_mask = click & (perp_sigma ^ perp_tau)
    sift_idx = np.where(conclusive_mask)[0]
    n_sifted = sift_idx.size

    # Inferred key bits:
    # If orthogonal to τ -> infer σ -> key bit = alice_bits (correct)
    # If orthogonal to σ -> infer τ -> key bit = tau_bits (error)
    # No shortcut flips: key bit is taken directly from the non-excluded state.
    inferred_bits = np.where(perp_tau[sift_idx], alice_bits[sift_idx], tau_bits[sift_idx]).astype(np.int8)

    sifted_alice_list = alice_bits[sift_idx].tolist()
    sifted_bob_list   = inferred_bits.tolist()

    # ── 5. Sifting efficiency metrics ────────────────────────────────────
    sifted_over_detected = (n_sifted / n_detected) if n_detected > 0 else 0.0
    sifted_over_sent     = (n_sifted / n_sent)     if n_sent     > 0 else 0.0

    # ── 6. Shared postprocessing pipeline ─────────────────────────────────
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
