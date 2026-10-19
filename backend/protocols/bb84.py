"""BB84 protocol (simplified simulation).

This module implements a toy BB84 simulation:
- Alice generates random bits and bases.
- Bob chooses random bases and measures (recovers Alice's bit if bases match, otherwise random).
- Sifting extracts positions where bases matched (returns both Alice's and Bob's sifted bits).
- Estimated QBER is computed on a sample of the sifted bits by comparing Alice vs Bob.

This is intentionally lightweight — replace or extend with more realistic modeling as needed.
"""
from typing import Dict, List, Tuple
import random


def _random_bits(n: int) -> List[int]:
    return [random.getrandbits(1) for _ in range(n)]


def _random_bases(n: int) -> List[int]:
    # 0 == Z basis, 1 == X basis
    return [random.getrandbits(1) for _ in range(n)]


def _sift_bits(alice_bits: List[int],
               alice_bases: List[int],
               bob_bits: List[int],
               bob_bases: List[int]) -> Tuple[List[int], List[int], List[int]]:
    """
    Return (sifted_alice_bits, sifted_bob_bits, sifted_indices).
    Sifted indices are positions where bases matched.
    """
    sifted_alice = []
    sifted_bob = []
    indices = []
    for i, (a_b, a_basis, b_b, b_basis) in enumerate(zip(alice_bits, alice_bases, bob_bits, bob_bases)):
        if a_basis == b_basis:
            sifted_alice.append(a_b)
            sifted_bob.append(b_b)
            indices.append(i)
    return sifted_alice, sifted_bob, indices


def run_bb84(raw_key_length: int, sample_size: int = 50) -> Dict:
    """
    Run a simplified BB84 simulation.

    Args:
        raw_key_length: Number of qubits sent by Alice.
        sample_size: Number of bits used to estimate QBER (sample from the start of sifted bits).

    Returns:
        A dictionary containing raw/sifted lengths, sifting efficiency, estimated QBER,
        and the actual sifted bit lists for Alice and Bob (useful for error correction).
    """
    # Generate Alice's bits and bases
    alice_bits = _random_bits(raw_key_length)
    alice_bases = _random_bases(raw_key_length)

    # Bob chooses bases and measures
    bob_bases = _random_bases(raw_key_length)
    bob_bits = []
    for i in range(raw_key_length):
        if bob_bases[i] == alice_bases[i]:
            # correct measurement
            bob_bits.append(alice_bits[i])
        else:
            # random result because bases differ
            bob_bits.append(random.getrandbits(1))

    sifted_alice, sifted_bob, sifted_indices = _sift_bits(alice_bits, alice_bases, bob_bits, bob_bases)
    sifting_efficiency = (len(sifted_alice) / raw_key_length) if raw_key_length > 0 else 0.0

    # Estimated QBER: compare a sample (first sample_size bits) of sifted_alice vs sifted_bob
    sample_len = min(sample_size, len(sifted_alice))
    if sample_len == 0:
        estimated_qber = 0.0
    else:
        errors = sum(1 for i in range(sample_len) if sifted_alice[i] != sifted_bob[i])
        estimated_qber = errors / sample_len

    return {
        "protocol": "bb84",
        "raw_key_length": raw_key_length,
        "sifted_key_length": len(sifted_alice),
        "sifting_efficiency": sifting_efficiency,
        "estimated_qber": estimated_qber,
        # Provide sifted bits for downstream error correction & privacy amplification
        "sifted_alice_bits": sifted_alice,
        "sifted_bob_bits": sifted_bob,
        "sifted_indices": sifted_indices,
    }
