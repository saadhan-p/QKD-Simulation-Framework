"""Channel models: attenuation and noise application."""

import math
import random
from typing import List


def attenuation(distance_km: float, alpha_db_per_km: float = 0.2) -> float:
    """
    Compute linear transmission factor from fiber attenuation model.

    Args:
        distance_km: distance in kilometers.
        alpha_db_per_km: attenuation in dB/km (typical ~0.2 dB/km for telecom fiber).

    Returns:
        Linear transmission factor in [0,1].
    """
    loss_db = alpha_db_per_km * distance_km
    return 10 ** (-loss_db / 10)


def apply_noise(bits: List[int], qber: float) -> List[int]:
    """
    Flip bits independently with probability `qber` (quantum bit error rate).

    Returns corrupted bit list.
    """
    if qber <= 0:
        return list(bits)
    corrupted = []
    for b in bits:
        if random.random() < qber:
            corrupted.append(1 - int(b))
        else:
            corrupted.append(int(b))
    return corrupted
