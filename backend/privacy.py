"""Privacy amplification helpers (Toeplitz hashing toy implementation)."""

from typing import List
import numpy as np


def toeplitz_hash(input_bits: List[int], output_len: int, seed: List[int] = None) -> List[int]:
    """
    Compute a simple Toeplitz-hash compression: output = T * input (mod 2).
    seed length must be input_len + output_len - 1. If not provided, generates one.
    Returns a list of bits of length output_len.
    """
    input_len = len(input_bits)
    if input_len == 0:
        return []

    required_seed_len = input_len + output_len - 1
    if seed is None:
        seed = list(np.random.randint(0, 2, size=required_seed_len))

    # Multiply mod 2: each output bit is XOR of input_bits[j] & seed[i+j] across j
    out = [0] * output_len
    for i in range(output_len):
        acc = 0
        for j in range(input_len):
            acc ^= (seed[i + j] & (1 if input_bits[j] else 0))
        out[i] = acc
    return out


def compress_and_hash(bits: List[int], target_len: int) -> List[int]:
    """Wrapper to compress `bits` down to `target_len` using Toeplitz hashing."""
    if target_len <= 0:
        return []
    return toeplitz_hash(bits, target_len)
