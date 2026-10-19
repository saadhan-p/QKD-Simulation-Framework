# backend/protocols/aurora_qkd.py
"""
Aurora QKD Protocol - Advanced hybrid protocol with adaptive mode switching.

Aurora combines elements of entanglement verification and efficient paired-state 
transmission, dynamically switching between Efficient Mode (EM) and Verified Mode (VM)
based on real-time QBER estimation.

Key Features:
- Entanglement anchor verification for security
- Paired-state transmission for efficiency
- Adaptive mode switching based on QBER thresholds
- Rescue protocol for inconclusive measurements
"""
import random
from typing import Dict, Any, List, Tuple


def _random_bits(n: int) -> List[int]:
    """Generate n random bits."""
    return [random.getrandbits(1) for _ in range(n)]


def _simulate_anchor(n_anchor: int, noise: float) -> float:
    """
    Simulate entanglement anchor verification.
    Returns S-value (CHSH violation parameter).
    Ideal S = 2.828, classical limit S = 2.0
    """
    ideal_S = 2.828  # Quantum limit for CHSH inequality
    # Degrade S-value based on noise
    S = max(2.0, ideal_S * (1 - noise * 1.5))
    return S


def _paired_state_send(n: int, paired_angle: float, qber: float) -> Tuple[List[int], List[int | None]]:
    """
    Simulate paired-state transmission for Efficient Mode.
    
    Args:
        n: Number of bits to send
        paired_angle: Angle parameter affecting conclusive/inconclusive ratio
        qber: Quantum bit error rate
        
    Returns:
        (alice_bits, bob_outcomes) where bob_outcomes may contain None for inconclusive
    """
    # Calculate overlap probability from paired angle
    overlap = abs(paired_angle % 1.0) * 0.4  # Maps to 0-0.4 range
    
    alice_bits = _random_bits(n)
    bob_outcomes = []
    
    for bit in alice_bits:
        if random.random() < (1 - overlap):  # Conclusive measurement
            # Apply quantum bit error
            if random.random() < qber:
                bob_outcomes.append(1 - bit)  # Bit flip
            else:
                bob_outcomes.append(bit)
        else:  # Inconclusive measurement
            bob_outcomes.append(None)
    
    return alice_bits, bob_outcomes


def _bb84_transmission(n: int, qber: float) -> Tuple[List[int], List[int]]:
    """
    Simulate standard BB84-like transmission for Verified Mode.
    
    Args:
        n: Number of bits to send
        qber: Quantum bit error rate
        
    Returns:
        (alice_bits, bob_bits)
    """
    alice_bits = _random_bits(n)
    bob_bits = []
    
    for bit in alice_bits:
        if random.random() < qber:
            bob_bits.append(1 - bit)  # Bit flip error
        else:
            bob_bits.append(bit)
    
    return alice_bits, bob_bits


def run_aurora(raw_key_length: int = 1000,
               block_size: int = 200,
               p_anchor: float = 0.05,
               paired_angle: float = 0.2,
               rescue_fraction: float = 0.25,
               eff_to_verif_qber: float = 0.06,
               verif_to_eff_qber: float = 0.03,
               qber: float = 0.02) -> Dict[str, Any]:
    """
    Run Aurora QKD protocol simulation.
    
    Args:
        raw_key_length: Total number of qubits to transmit
        block_size: Size of each transmission block
        p_anchor: Fraction of each block used for anchor verification
        paired_angle: Angle parameter for paired-state protocol
        rescue_fraction: Fraction of inconclusive bits to rescue
        eff_to_verif_qber: QBER threshold to switch from EM to VM
        verif_to_eff_qber: QBER threshold to switch from VM to EM
        qber: Base quantum bit error rate
        
    Returns:
        Dictionary with protocol results including sifted bits and statistics
    """
    # Session-level accumulators
    sifted_alice = []
    sifted_bob = []
    block_mode = "EM"  # Start in Efficient Mode
    blocks = max(1, raw_key_length // block_size)
    S_values = []
    mode_history = []
    
    # Counters for Table VI
    count_standard = 0
    count_rescued = 0
    
    for block_idx in range(blocks):
        # Calculate block size (last block may be smaller)
        if block_idx < blocks - 1:
            n_block = block_size
        else:
            n_block = raw_key_length - block_size * (blocks - 1)
        
        n_anchor = max(1, int(n_block * p_anchor))
        n_key = n_block - n_anchor
        
        # Step 1: Anchor verification
        S = _simulate_anchor(n_anchor, qber)
        S_values.append(S)
        
        # Abort if anchor fails (security threshold)
        if S < 2.2:
            return {
                "protocol": "aurora",
                "status": "aborted",
                "reason": "anchor_verification_failed",
                "S_value": S,
                "block": block_idx,
                "sifted_alice_bits": [],
                "sifted_bob_bits": [],
                "sifted_key_length": 0,
                "estimated_qber": 1.0,
                "raw_key_length": raw_key_length,
            }
        
        # Step 2: Key generation based on current mode
        if block_mode == "EM":
            # Efficient Mode: Use paired-state protocol
            alice_bits, bob_outcomes = _paired_state_send(n_key, paired_angle, qber)
            
            # Collect conclusive measurements
            conclusive_pairs = [(a, b) for a, b in zip(alice_bits, bob_outcomes) if b is not None]
            alice_conclusive = [a for a, _ in conclusive_pairs]
            bob_conclusive = [b for _, b in conclusive_pairs]
            
            # Rescue some inconclusive measurements
            inconclusive_alice = [a for a, b in zip(alice_bits, bob_outcomes) if b is None]
            n_rescue = int(len(inconclusive_alice) * rescue_fraction)
            rescued_alice = inconclusive_alice[:n_rescue]
            rescued_bob = []
            for bit in rescued_alice:
                if random.random() < qber:
                    rescued_bob.append(1 - bit)
                else:
                    rescued_bob.append(bit)
            
            # Combine conclusive and rescued
            sifted_alice.extend(alice_conclusive + rescued_alice)
            sifted_bob.extend(bob_conclusive + rescued_bob)
            
            # Update counters
            count_standard += len(alice_conclusive)
            count_rescued += len(rescued_alice)
            
            mode_history.append("EM")
            
        else:  # VM - Verified Mode
            # Verified Mode: Use BB84-like protocol
            alice_bits, bob_bits = _bb84_transmission(n_key, qber)
            sifted_alice.extend(alice_bits)
            sifted_bob.extend(bob_bits)
            
            # BB84-like bits count as standard
            count_standard += len(alice_bits)
            
            mode_history.append("VM")
        
        # Step 3: Estimate QBER and adapt mode
        if len(sifted_alice) > 0:
            mismatches = sum(1 for a, b in zip(sifted_alice, sifted_bob) if a != b)
            current_qber = mismatches / len(sifted_alice)
            
            # Mode switching logic
            if block_mode == "EM" and current_qber > eff_to_verif_qber:
                block_mode = "VM"  # Switch to more secure mode
            elif block_mode == "VM" and current_qber < verif_to_eff_qber:
                block_mode = "EM"  # Switch back to efficient mode
    
    # Final statistics
    sifted_len = len(sifted_alice)
    
    if sifted_len == 0:
        return {
            "protocol": "aurora",
            "status": "failed",
            "reason": "no_sifted_bits",
            "sifted_alice_bits": [],
            "sifted_bob_bits": [],
            "sifted_key_length": 0,
            "estimated_qber": 1.0,
            "raw_key_length": raw_key_length,
            "standard_bits_count": 0,
            "rescued_bits_count": 0,
            "mode_history": mode_history,
        }
    
    # Calculate final QBER
    total_mismatches = sum(1 for a, b in zip(sifted_alice, sifted_bob) if a != b)
    estimated_qber = total_mismatches / sifted_len
    
    # Sifting efficiency
    sifting_efficiency = sifted_len / raw_key_length if raw_key_length > 0 else 0.0
    
    # Average S-value
    avg_S = sum(S_values) / len(S_values) if S_values else 0.0
    
    return {
        "protocol": "aurora",
        "raw_key_length": raw_key_length,
        "sifted_key_length": sifted_len,
        "sifting_efficiency": sifting_efficiency,
        "estimated_qber": estimated_qber,
        "sifted_alice_bits": sifted_alice,
        "sifted_bob_bits": sifted_bob,
        "S_values": S_values,
        "avg_S_value": avg_S,
        "mode_history": mode_history,
        "final_mode": block_mode,
        "blocks_processed": len(S_values),
        "standard_bits_count": count_standard,
        "rescued_bits_count": count_rescued,
        "status": "success",
    }
