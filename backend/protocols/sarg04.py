"""SARG04 protocol (simplified simulation stub).

SARG04 has different sifting and security properties from BB84. This file provides
a simplified behavior for demonstration and comparison — it intentionally uses
a slightly different sifting rule (toy): we mark more positions as usable to
illustrate differing sifting efficiency and QBER.

Return format is similar to bb84.run_bb84 so client/backend can handle both uniformly.
"""
from typing import Dict, List, Tuple
import random


def _random_bits(n: int) -> List[int]:
    return [random.getrandbits(1) for _ in range(n)]


def _random_bases(n: int) -> List[int]:
    return [random.getrandbits(1) for _ in range(n)]


def _sarg_sift(alice_bits: List[int],
               alice_bases: List[int],
               bob_bits: List[int],
               bob_bases: List[int]) -> Tuple[List[int], List[int], List[int]]:
    """
    Toy SARG04 sifting: In real SARG04 the classical sifting differs; here we
    approximate by accepting some mismatched basis outcomes with a probability
    to increase sifted size (purely for demo).
    """
    sifted_alice = []
    sifted_bob = []
    indices = []
    for i, (a_b, a_basis, b_b, b_basis) in enumerate(zip(alice_bits, alice_bases, bob_bits, bob_bases)):
        if a_basis == b_basis:
            sifted_alice.append(a_b)
            sifted_bob.append(b_b)
            indices.append(i)
        else:
            # with small probability accept some mismatches (toy behavior)
            if random.random() < 0.2:
                sifted_alice.append(a_b)
                sifted_bob.append(b_b)
                indices.append(i)
    return sifted_alice, sifted_bob, indices


def run_sarg04(raw_key_length: int, sample_size: int = 50) -> Dict:
    """
    Run a simplified SARG04-like simulation.

    Args:
        raw_key_length: number of qubits sent by Alice.
        sample_size: number of sifted bits used to estimate QBER.

    Returns:
        Dictionary similar to run_bb84 with sifted bits for both parties.
    """
    alice_bits = _random_bits(raw_key_length)
    alice_bases = _random_bases(raw_key_length)

    bob_bases = _random_bases(raw_key_length)
    bob_bits = []
    for i in range(raw_key_length):
        if bob_bases[i] == alice_bases[i]:
            bob_bits.append(alice_bits[i])
        else:
            # mismatched basis => random result
            bob_bits.append(random.getrandbits(1))

    sifted_alice, sifted_bob, sifted_indices = _sarg_sift(alice_bits, alice_bases, bob_bits, bob_bases)
    sifting_efficiency = (len(sifted_alice) / raw_key_length) if raw_key_length > 0 else 0.0

    sample_len = min(sample_size, len(sifted_alice))
    if sample_len == 0:
        estimated_qber = 0.0
    else:
        errors = sum(1 for i in range(sample_len) if sifted_alice[i] != sifted_bob[i])
        estimated_qber = errors / sample_len

    # Provide a lightweight security indicator (toy)
    security_level_hint = "medium" if estimated_qber < 0.15 else "low"

    return {
        "protocol": "sarg04",
        "raw_key_length": raw_key_length,
        "sifted_key_length": len(sifted_alice),
        "sifting_efficiency": sifting_efficiency,
        "estimated_qber": estimated_qber,
        "security_hint": security_level_hint,
        "sifted_alice_bits": sifted_alice,
        "sifted_bob_bits": sifted_bob,
        "sifted_indices": sifted_indices,
    }
