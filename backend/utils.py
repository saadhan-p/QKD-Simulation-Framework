"""Utility helpers used across backend modules."""

import random
from typing import List


def random_bits(n: int) -> List[int]:
    """Return a list of n random bits (0/1)."""
    return [random.getrandbits(1) for _ in range(n)]


def random_bases(n: int) -> List[int]:
    """Return a list of n random bases (0 or 1)."""
    return [random.getrandbits(1) for _ in range(n)]


def list_to_bitstring(bits: List[int]) -> str:
    """Convert list of bits to string representation like '0101...'."""
    return "".join(str(int(b)) for b in bits)
