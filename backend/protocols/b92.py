"""B92 protocol (simplified simulation).

This module implements a toy B92 simulation:
- Alice generates random bits (0 implies |0> state, 1 implies |+> state).
- Bob randomly measures in Z (0) or X (1) basis.
- If Bob gets a conclusive result (e.g., measures |1> in Z meaning Alice must have sent |+>), he keeps the bit.
- Sifting efficiency is lower than BB84 (~25%).
"""
from typing import Dict, List, Tuple
import random

def _random_bits(n: int) -> List[int]:
    return [random.getrandbits(1) for _ in range(n)]

def run_b92(raw_key_length: int, sample_size: int = 50) -> Dict:
    """
    Run a simplified B92 simulation.
    """
    alice_bits = _random_bits(raw_key_length)
    bob_bases = _random_bits(raw_key_length)
    
    sifted_alice = []
    sifted_bob = []
    sifted_indices = []
    
    for i in range(raw_key_length):
        a_bit = alice_bits[i]
        b_basis = bob_bases[i]
        
        # B92 simplified logic:
        # If Alice sends 0 (|0>) and Bob measures X (1), 50% chance of getting 1 (|->). If 1 -> conclusive (Alice sent 0).
        # If Alice sends 1 (|+>) and Bob measures Z (0), 50% chance of getting 1 (|1>). If 1 -> conclusive (Alice sent 1).
        # Otherwise inconclusive.
        is_conclusive = False
        if a_bit == 0 and b_basis == 1:
            if random.random() < 0.5:
                is_conclusive = True
        elif a_bit == 1 and b_basis == 0:
            if random.random() < 0.5:
                is_conclusive = True
                
        if is_conclusive:
            sifted_alice.append(a_bit)
            sifted_bob.append(a_bit)  # Bob correctly infers Alice's bit
            sifted_indices.append(i)

    sifting_efficiency = (len(sifted_alice) / raw_key_length) if raw_key_length > 0 else 0.0

    # For B92, estimated QBER
    sample_len = min(sample_size, len(sifted_alice))
    if sample_len == 0:
        estimated_qber = 0.0
    else:
        errors = sum(1 for i in range(sample_len) if sifted_alice[i] != sifted_bob[i])
        estimated_qber = errors / sample_len

    return {
        "protocol": "b92",
        "raw_key_length": raw_key_length,
        "sifted_key_length": len(sifted_alice),
        "sifting_efficiency": sifting_efficiency,
        "estimated_qber": estimated_qber,
        "sifted_alice_bits": sifted_alice,
        "sifted_bob_bits": sifted_bob,
        "sifted_indices": sifted_indices,
    }
