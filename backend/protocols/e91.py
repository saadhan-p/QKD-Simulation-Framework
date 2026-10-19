"""E91 protocol (simplified simulation).

This module implements a toy E91 simulation:
- Relies on entangled pairs distributed to Alice and Bob.
- They choose from 3 measurement bases.
- For bits where bases match, they are perfectly correlated (or anti-correlated).
- Other bases are used for the CHSH inequality test.
- We simulate the correlated portion here.
"""
from typing import Dict, List, Tuple
import random

def _random_bits(n: int) -> List[int]:
    return [random.getrandbits(1) for _ in range(n)]

def _random_bases_e91(n: int) -> List[int]:
    # 0, 1, 2 representing 3 bases
    return [random.choice([0, 1, 2]) for _ in range(n)]

def run_e91(raw_key_length: int, sample_size: int = 50) -> Dict:
    """
    Run a simplified E91 simulation.
    """
    alice_bases = _random_bases_e91(raw_key_length)
    bob_bases = _random_bases_e91(raw_key_length)
    
    # Entangled pairs (perfectly correlated if bases match)
    entangled_bits = _random_bits(raw_key_length)
    
    sifted_alice = []
    sifted_bob = []
    sifted_indices = []
    
    for i in range(raw_key_length):
        if alice_bases[i] == bob_bases[i]:
            sifted_alice.append(entangled_bits[i])
            sifted_bob.append(entangled_bits[i])
            sifted_indices.append(i)

    sifting_efficiency = (len(sifted_alice) / raw_key_length) if raw_key_length > 0 else 0.0

    # Estimated QBER
    sample_len = min(sample_size, len(sifted_alice))
    if sample_len == 0:
        estimated_qber = 0.0
    else:
        errors = sum(1 for i in range(sample_len) if sifted_alice[i] != sifted_bob[i])
        estimated_qber = errors / sample_len

    return {
        "protocol": "e91",
        "raw_key_length": raw_key_length,
        "sifted_key_length": len(sifted_alice),
        "sifting_efficiency": sifting_efficiency,
        "estimated_qber": estimated_qber,
        "sifted_alice_bits": sifted_alice,
        "sifted_bob_bits": sifted_bob,
        "sifted_indices": sifted_indices,
    }
