"""Simple (toy) security estimators."""

from typing import List
from collections import Counter
import math


def min_entropy(bits: List[int]) -> float:
    """
    Toy min-entropy estimator: -log2(max probability of any symbol).
    For binary sequences, estimate frequency of 0 or 1.
    Returns per-bit min-entropy (in bits).
    """
    if not bits:
        return 0.0
    c = Counter(bits)
    p_max = max(c.values()) / len(bits)
    # avoid log(0)
    if p_max <= 0:
        return 0.0
    return -math.log2(p_max)


def estimated_entropy_total(bits: List[int]) -> float:
    """Return estimated total min-entropy (per-bit * length)."""
    return min_entropy(bits) * len(bits)


def security_status(bit_len: int, qber: float, estimated_entropy_per_bit: float) -> bool:
    """
    Simple policy decision: require estimated total entropy > threshold fraction of bit_len.
    This is a toy rule — replace with finite-key composable proofs for real usage.
    """
    if bit_len <= 0:
        return False
    total_ent = estimated_entropy_per_bit * bit_len
    threshold = 0.4 * bit_len  # require at least 40% of bits worth of entropy
    return total_ent > threshold
