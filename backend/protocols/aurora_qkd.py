# backend/protocols/aurora_qkd.py
"""
Aurora QKD Protocol - Advanced hybrid protocol with adaptive mode switching.

IMPORTANT — PROVISIONAL STATUS
================================
Aurora results at this stage are PROVISIONAL.  The physics engine for the
Efficient Mode (EM) and Verified Mode (VM) has not been redesigned in this
phase.  Specifically:
  - _bb84_transmission (VM) does NOT perform basis sifting — all bits are
    kept as if every basis matched.  This over-counts the sifted length.
  - The EM "paired-state" model is a heuristic (not derived from first
    principles of SARG-like non-orthogonal state discrimination).
  - The rescue protocol for inconclusive EM measurements is unphysical.
The shared postprocessing (run_postprocessing) is now used for PA and the
abort rule, so those steps are physically honest.  However, the QBER
estimated from Aurora's sifted bits includes the bias from the above issues.

A proper Aurora physics redesign is deferred to a later phase.  Aurora
outputs must NOT be used for quantitative security comparisons until the
EM redesign is complete.

Legacy mode
-----------
Pass ``legacy=True`` to get the old behaviour including the old per-protocol
PA factor (0.65) and no abort-by-key-length.  This preserves the audit trail.
"""
import random as _stdlib_random
from typing import Dict, Any, List, Tuple, Optional

import numpy as np

from ..postprocessing import run_postprocessing


def _random_bits_legacy(n: int) -> List[int]:
    """Generate n random bits using the legacy (stdlib) RNG."""
    return [_stdlib_random.getrandbits(1) for _ in range(n)]


def _simulate_anchor(n_anchor: int, noise: float) -> float:
    """
    Simulate entanglement anchor verification.
    Returns S-value (CHSH violation parameter).
    Ideal S = 2.828, classical limit S = 2.0

    NOTE: This is a heuristic model, not a real entanglement simulation.
    """
    ideal_S = 2.828  # Quantum limit for CHSH inequality
    S = max(2.0, ideal_S * (1 - noise * 1.5))
    return S


def _paired_state_send(
    n: int,
    paired_angle: float,
    qber: float,
    rng: Optional[np.random.Generator] = None,
) -> Tuple[List[int], List[Optional[int]]]:
    """
    Simulate paired-state transmission for Efficient Mode.
    
    HEURISTIC: The overlap parameter is not derived from real quantum optics.
    
    Args:
        n: Number of bits to send
        paired_angle: Angle parameter affecting conclusive/inconclusive ratio
        qber: Quantum bit error rate
        rng: Seeded numpy RNG (if None, falls back to stdlib — legacy mode)
        
    Returns:
        (alice_bits, bob_outcomes) where bob_outcomes may contain None for inconclusive
    """
    overlap = abs(paired_angle % 1.0) * 0.4  # Maps to 0-0.4 range
    
    if rng is not None:
        alice_bits = rng.integers(0, 2, size=n).tolist()
        rand_conclusive = rng.random(n)
        rand_error = rng.random(n)
        rand_rand = rng.integers(0, 2, size=n).tolist()
    else:
        alice_bits = _random_bits_legacy(n)
        rand_conclusive = [_stdlib_random.random() for _ in range(n)]
        rand_error = [_stdlib_random.random() for _ in range(n)]
        rand_rand = _random_bits_legacy(n)
    
    bob_outcomes: List[Optional[int]] = []
    for i, bit in enumerate(alice_bits):
        if rand_conclusive[i] < (1 - overlap):  # Conclusive
            if rand_error[i] < qber:
                bob_outcomes.append(1 - bit)
            else:
                bob_outcomes.append(bit)
        else:  # Inconclusive
            bob_outcomes.append(None)
    
    return alice_bits, bob_outcomes


def _bb84_transmission(
    n: int,
    qber: float,
    rng: Optional[np.random.Generator] = None,
) -> Tuple[List[int], List[int]]:
    """
    Simulate BB84-like transmission for Verified Mode.
    
    KNOWN ISSUE (audit finding): This function does NOT perform basis sifting.
    All n bits are returned as sifted, which inflates the sifted length by ~2×.
    This is preserved here for the audit trail; it will be fixed in the Aurora
    physics redesign phase.
    
    Args:
        n: Number of bits to send
        qber: Quantum bit error rate
        rng: Seeded numpy RNG (if None, falls back to stdlib — legacy mode)
        
    Returns:
        (alice_bits, bob_bits) — NO SIFTING APPLIED
    """
    if rng is not None:
        alice_bits_arr = rng.integers(0, 2, size=n)
        flip_mask = rng.random(n) < qber
        bob_bits_arr = np.where(flip_mask, 1 - alice_bits_arr, alice_bits_arr)
        alice_bits = alice_bits_arr.tolist()
        bob_bits = bob_bits_arr.tolist()
    else:
        alice_bits = _random_bits_legacy(n)
        bob_bits = []
        for bit in alice_bits:
            if _stdlib_random.random() < qber:
                bob_bits.append(1 - bit)
            else:
                bob_bits.append(bit)
    
    return alice_bits, bob_bits


def run_aurora(
    raw_key_length: int = 1000,
    block_size: int = 200,
    p_anchor: float = 0.05,
    paired_angle: float = 0.2,
    rescue_fraction: float = 0.25,
    eff_to_verif_qber: float = 0.06,
    verif_to_eff_qber: float = 0.03,
    qber: float = 0.02,
    rng: Optional[np.random.Generator] = None,
    legacy: bool = False,
    # postprocessing kwargs (used only when legacy=False)
    sample_fraction: float = 0.10,
    sample_min: int = 100,
    f_ec: float = 1.16,
    eps_sec: float = 1e-6,
    eps_pe: float = 1e-6,
) -> Dict[str, Any]:
    """
    Run Aurora QKD protocol simulation.
    
    Parameters
    ----------
    raw_key_length : int
        Total number of qubits to transmit.
    block_size : int
        Size of each transmission block.
    p_anchor : float
        Fraction of each block used for anchor verification.
    paired_angle : float
        Angle parameter for paired-state protocol.
    rescue_fraction : float
        Fraction of inconclusive bits to rescue.
    eff_to_verif_qber : float
        QBER threshold to switch from EM to VM.
    verif_to_eff_qber : float
        QBER threshold to switch from VM to EM.
    qber : float
        Base quantum bit error rate.
    rng : np.random.Generator, optional
        Seeded RNG.  If None and legacy=False, a default-seeded RNG is used.
        If legacy=True, stdlib random is used (old behaviour).
    legacy : bool
        If True, use the old per-protocol PA factor (0.65) and skip the
        shared postprocessing abort rule.  This preserves the audit trail.
    
    Returns
    -------
    dict
        Protocol results.  When legacy=False, includes all fields from
        run_postprocessing.  Always includes the field
        ``aurora_provisional = True`` to flag that the physics engine is
        not yet fully redesigned.
    """
    if not legacy and rng is None:
        # Use a deterministic default so tests don't break; callers should
        # always pass an explicit rng.
        rng = np.random.default_rng(0)

    sifted_alice: List[int] = []
    sifted_bob:   List[int] = []
    block_mode = "EM"
    blocks = max(1, raw_key_length // block_size)
    S_values: List[float] = []
    mode_history: List[str] = []
    count_standard = 0
    count_rescued  = 0
    
    for block_idx in range(blocks):
        if block_idx < blocks - 1:
            n_block = block_size
        else:
            n_block = raw_key_length - block_size * (blocks - 1)
        
        n_anchor = max(1, int(n_block * p_anchor))
        n_key    = n_block - n_anchor
        
        # Step 1: Anchor verification
        S = _simulate_anchor(n_anchor, qber)
        S_values.append(S)
        
        if S < 2.2:
            result = {
                "protocol":           "aurora",
                "aurora_provisional": True,
                "status":             "aborted",
                "reason":             "anchor_verification_failed",
                "S_value":            S,
                "block":              block_idx,
                "sifted_alice_bits":  [],
                "sifted_bob_bits":    [],
                "sifted_key_length":  0,
                "estimated_qber":     1.0,
                "raw_key_length":     raw_key_length,
                "final_key_length_asymptotic": 0,
                "final_key_length_finite":     0,
                "aborted":            True,
            }
            return result
        
        # Step 2: Key generation based on current mode
        if block_mode == "EM":
            alice_bits, bob_outcomes = _paired_state_send(n_key, paired_angle, qber, rng)
            
            conclusive_pairs = [(a, b) for a, b in zip(alice_bits, bob_outcomes) if b is not None]
            alice_conclusive = [a for a, _ in conclusive_pairs]
            bob_conclusive   = [b for _, b in conclusive_pairs]
            
            inconclusive_alice = [a for a, b in zip(alice_bits, bob_outcomes) if b is None]
            n_rescue = int(len(inconclusive_alice) * rescue_fraction)
            rescued_alice = inconclusive_alice[:n_rescue]
            rescued_bob: List[int] = []
            
            if rng is not None:
                for bit in rescued_alice:
                    flip = rng.random() < qber
                    rescued_bob.append(1 - bit if flip else bit)
            else:
                for bit in rescued_alice:
                    if _stdlib_random.random() < qber:
                        rescued_bob.append(1 - bit)
                    else:
                        rescued_bob.append(bit)
            
            sifted_alice.extend(alice_conclusive + rescued_alice)
            sifted_bob.extend(bob_conclusive + rescued_bob)
            count_standard += len(alice_conclusive)
            count_rescued  += len(rescued_alice)
            mode_history.append("EM")
            
        else:  # VM - Verified Mode (KNOWN ISSUE: no basis sifting)
            alice_bits, bob_bits = _bb84_transmission(n_key, qber, rng)
            sifted_alice.extend(alice_bits)
            sifted_bob.extend(bob_bits)
            count_standard += len(alice_bits)
            mode_history.append("VM")
        
        # Step 3: Estimate QBER and adapt mode
        if sifted_alice:
            mismatches  = sum(1 for a, b in zip(sifted_alice, sifted_bob) if a != b)
            current_qber = mismatches / len(sifted_alice)
            if block_mode == "EM" and current_qber > eff_to_verif_qber:
                block_mode = "VM"
            elif block_mode == "VM" and current_qber < verif_to_eff_qber:
                block_mode = "EM"
    
    sifted_len = len(sifted_alice)
    
    if sifted_len == 0:
        result = {
            "protocol":           "aurora",
            "aurora_provisional": True,
            "status":             "failed",
            "reason":             "no_sifted_bits",
            "sifted_alice_bits":  [],
            "sifted_bob_bits":    [],
            "sifted_key_length":  0,
            "estimated_qber":     1.0,
            "raw_key_length":     raw_key_length,
            "standard_bits_count": 0,
            "rescued_bits_count":  0,
            "mode_history":        mode_history,
            "final_key_length_asymptotic": 0,
            "final_key_length_finite":     0,
            "aborted":            True,
        }
        return result
    
    total_mismatches = sum(1 for a, b in zip(sifted_alice, sifted_bob) if a != b)
    estimated_qber   = total_mismatches / sifted_len
    sifting_efficiency = sifted_len / raw_key_length if raw_key_length > 0 else 0.0
    avg_S = sum(S_values) / len(S_values) if S_values else 0.0
    
    base_result = {
        "protocol":             "aurora",
        "aurora_provisional":   True,
        "raw_key_length":       raw_key_length,
        "sifted_key_length":    sifted_len,
        "sifting_efficiency":   sifting_efficiency,
        "estimated_qber":       estimated_qber,
        "sifted_alice_bits":    sifted_alice,
        "sifted_bob_bits":      sifted_bob,
        "S_values":             S_values,
        "avg_S_value":          avg_S,
        "mode_history":         mode_history,
        "final_mode":           block_mode,
        "blocks_processed":     len(S_values),
        "standard_bits_count":  count_standard,
        "rescued_bits_count":   count_rescued,
        "status":               "success",
    }
    
    if legacy:
        # ── LEGACY PATH ── old per-protocol PA factor, no honest abort rule
        pa_factor = max(0.1, min(0.9, 0.65 - 1.5 * estimated_qber))
        out_len = max(1, int(sifted_len * pa_factor))
        security_passed = estimated_qber < 0.125
        if not security_passed:
            out_len = 0
        base_result.update({
            "final_key_length": out_len,
            "final_key_length_asymptotic": out_len,
            "final_key_length_finite":     0,
            "security_passed":  security_passed,
            "legacy_mode":      True,
            "aborted":          not security_passed,
        })
        return base_result
    
    # ── CURRENT PATH ── shared postprocessing
    pp_result = run_postprocessing(
        sifted_alice,
        sifted_bob,
        rng,
        protocol="aurora",
        n_raw=raw_key_length,
        n_detected=sifted_len,   # Aurora doesn't track pre-sift detections yet
        sample_fraction=sample_fraction,
        sample_min=sample_min,
        f_ec=f_ec,
        eps_sec=eps_sec,
        eps_pe=eps_pe,
    )
    base_result.update(pp_result)
    base_result["legacy_mode"] = False
    return base_result
