"""
backend/postprocessing.py
=========================
Shared, single-code-path post-processing for ALL QKD protocols.

Pipeline
--------
1. Parameter estimation (PE): draw a random sample from the sifted bits,
   compare publicly to estimate QBER_est, and REMOVE those bits from the key.
2. Error correction (EC): leakage model — we do NOT implement Cascade; we
   assume ideal EC has already corrected errors and simply account for the
   information leaked by computing
       leak_EC = f_EC * n_remaining * h2(QBER_est)
   where f_EC (default 1.16) is the standard efficiency factor for Cascade.
   The key is assumed corrected (Alice and Bob hold the same string).
3. Privacy amplification (PA): asymptotic BB84-style formula
       l = n_remaining * (1 - h2(QBER_est)) - leak_EC - log2(1/eps_sec)
   floored at 0, then truncated to an integer.
4. Abort rule: QBER_est >= QBER_ABORT_THRESHOLD (default 0.11) or l <= 0
   → key_length = 0, aborted = True.

The BB84 asymptotic formula 1 − 2·h2(Q) that appears in the literature is
the special case where f_EC = 1 and PE sampling is ignored.  We use the
more conservative form above for physical honesty.

NOTE on SARG04: This module uses the same formula for SARG04 as for BB84.
That is documented as a simplification; a rigorous SARG04 bound requires
a separate security proof and is NOT implemented here.  Every SARG04 output
row carries the flag formula_note = "simplified_BB84_formula".

References
----------
- Scarani et al., Rev. Mod. Phys. 81, 1301 (2009)   [Eq. general PA bound]
- Tomamichel & Leverrier, Quantum 1, 14 (2017)       [finite-size correction]
- Bennett et al., J. Cryptology 5, 3 (1992)          [Cascade efficiency]
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np


# ---------------------------------------------------------------------------
# Constants (module-level defaults; callers may override via kwargs)
# ---------------------------------------------------------------------------
QBER_ABORT_THRESHOLD: float = 0.11   # abort if QBER_est >= this value
F_EC_DEFAULT:         float = 1.16   # EC efficiency factor (Cascade typical)
EPS_SEC_DEFAULT:      float = 1e-6   # security parameter ε_sec
SAMPLE_FRACTION_DEFAULT: float = 0.10  # fraction of sifted bits used for PE
SAMPLE_MIN_DEFAULT:   int   = 100    # minimum PE sample size in bits


# ---------------------------------------------------------------------------
# h2 — binary entropy
# ---------------------------------------------------------------------------
def h2(x: float) -> float:
    """Binary entropy function h2(x) = -x log2(x) - (1-x) log2(1-x).

    Safe at the edges: h2(0) = h2(1) = 0.  Returns 1.0 for x=0.5.
    Domain: x ∈ [0, 1].  Values outside this range raise ValueError.
    """
    if not (0.0 <= x <= 1.0):
        raise ValueError(f"h2 argument must be in [0, 1]; got {x}")
    if x == 0.0 or x == 1.0:
        return 0.0
    return -x * math.log2(x) - (1.0 - x) * math.log2(1.0 - x)


# ---------------------------------------------------------------------------
# Parameter estimation
# ---------------------------------------------------------------------------
def _parameter_estimation(
    alice_bits: list[int],
    bob_bits: list[int],
    rng: np.random.Generator,
    sample_fraction: float,
    sample_min: int,
) -> tuple[int, float, list[int], list[int]]:
    """Draw a random sample, estimate QBER, return remaining bits.

    Returns
    -------
    n_sampled : int
        Number of bits consumed for parameter estimation.
    qber_est : float
        Estimated QBER from the PE sample.
    remaining_alice : list[int]
        Alice's bits after PE sample removed.
    remaining_bob : list[int]
        Bob's bits after PE sample removed.
    """
    n_sifted = len(alice_bits)
    n_sample = max(sample_min, int(math.ceil(sample_fraction * n_sifted)))
    n_sample = min(n_sample, n_sifted)   # can't exceed what we have

    # Draw without replacement
    indices = rng.choice(n_sifted, size=n_sample, replace=False)
    idx_set = set(indices.tolist())

    # Count errors in sample
    errors = sum(1 for i in indices if alice_bits[i] != bob_bits[i])
    qber_est = errors / n_sample if n_sample > 0 else 0.0

    # Remaining bits
    remaining_alice = [alice_bits[i] for i in range(n_sifted) if i not in idx_set]
    remaining_bob   = [bob_bits[i]   for i in range(n_sifted) if i not in idx_set]

    return n_sample, qber_est, remaining_alice, remaining_bob


# ---------------------------------------------------------------------------
# Asymptotic key length
# ---------------------------------------------------------------------------
def _asymptotic_key_length(
    n_remaining: int,
    qber_est: float,
    f_ec: float,
    eps_sec: float,
) -> int:
    """Compute the asymptotic secret key length.

    Formula:
        l = n_remaining * (1 - h2(QBER_est)) - leak_EC - log2(1/eps_sec)
        leak_EC = f_EC * n_remaining * h2(QBER_est)

    Returns 0 if the result is negative.
    """
    if n_remaining <= 0 or qber_est >= 1.0:
        return 0
    h = h2(qber_est)
    leak_ec = f_ec * n_remaining * h
    correction = math.log2(1.0 / eps_sec) if eps_sec > 0 else 0.0
    l = n_remaining * (1.0 - h) - leak_ec - correction
    return max(0, int(math.floor(l)))


# ---------------------------------------------------------------------------
# Finite-size key length
# ---------------------------------------------------------------------------
def finite_key_length(
    n_remaining: int,
    qber_est: float,
    f_ec: float = F_EC_DEFAULT,
    eps_sec: float = EPS_SEC_DEFAULT,
    eps_pe: float = 1e-6,
) -> int:
    """Compute a simplified finite-size secret key length.

    This implements the simplified correction term

        l_finite = l_asymptotic - sqrt(n_remaining) * log2(1 / eps_pe)

    as described in Tomamichel & Leverrier (2017) §3.  This is a rough
    approximation: a full finite-size analysis requires smooth min-entropy
    calculations and is NOT done here.  The correction term penalises the
    key length for the statistical uncertainty in the PE sample.

    Both asymptotic and finite lengths are returned by ``run_postprocessing``.

    Parameters
    ----------
    eps_pe : float
        PE failure probability (statistical confidence of QBER estimate).

    Returns
    -------
    int
        Finite-size key length (≥ 0).
    """
    l_asym = _asymptotic_key_length(n_remaining, qber_est, f_ec, eps_sec)
    if l_asym == 0 or n_remaining <= 0:
        return 0
    # Simplified finite-size correction
    correction_fs = math.sqrt(n_remaining) * math.log2(1.0 / max(eps_pe, 1e-300))
    l_finite = l_asym - correction_fs
    return max(0, int(math.floor(l_finite)))


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------
def run_postprocessing(
    alice_bits: list[int],
    bob_bits: list[int],
    rng: np.random.Generator,
    *,
    protocol: str = "bb84",
    n_raw: int = 0,
    n_detected: int = 0,
    sample_fraction: float = SAMPLE_FRACTION_DEFAULT,
    sample_min: int = SAMPLE_MIN_DEFAULT,
    f_ec: float = F_EC_DEFAULT,
    eps_sec: float = EPS_SEC_DEFAULT,
    eps_pe: float = 1e-6,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run the full post-processing pipeline on a pair of sifted bit lists.

    This is the SINGLE code path used by every protocol.  No per-protocol
    factors are permitted here.

    Parameters
    ----------
    alice_bits : list[int]
        Alice's sifted bits (after basis sifting).
    bob_bits : list[int]
        Bob's sifted bits (same positions as alice_bits).
    rng : np.random.Generator
        Seeded random number generator (passed in by the caller).
    protocol : str
        Name tag written to output (e.g. "bb84", "sarg04", "aurora").
    n_raw : int
        Number of pulses Alice sent (for efficiency statistics).
    n_detected : int
        Number of detection events (before sifting).
    sample_fraction : float
        Fraction of sifted bits to sacrifice for PE (default 0.10).
    sample_min : int
        Minimum number of bits to use for PE (default 100).
    f_ec : float
        Error-correction efficiency factor (default 1.16).
    eps_sec : float
        Security parameter ε_sec (default 1e-6).
    eps_pe : float
        PE failure probability for finite-size correction (default 1e-6).
    extra : dict, optional
        Any extra fields to include verbatim in the output dict.

    Returns
    -------
    dict with keys:
        protocol, n_raw, n_detected, n_sifted, n_sampled, qber_est,
        leak_ec, final_key_length_asymptotic, final_key_length_finite,
        aborted, abort_reason,
        config (sub-dict: sample_fraction, sample_min, f_ec, eps_sec, eps_pe),
        formula_note (SARG04 only)
    """
    n_sifted = len(alice_bits)
    assert len(bob_bits) == n_sifted, "alice and bob bit lists must have same length"

    config_used = {
        "sample_fraction": sample_fraction,
        "sample_min":      sample_min,
        "f_ec":            f_ec,
        "eps_sec":         eps_sec,
        "eps_pe":          eps_pe,
        "qber_abort_threshold": QBER_ABORT_THRESHOLD,
    }

    # --- Edge case: nothing sifted ---
    if n_sifted == 0:
        result = dict(
            protocol=protocol,
            n_raw=n_raw,
            n_detected=n_detected,
            n_sifted=0,
            n_sampled=0,
            qber_est=None,
            leak_ec=0.0,
            final_key_length_asymptotic=0,
            final_key_length_finite=0,
            aborted=True,
            abort_reason="no_sifted_bits",
            config=config_used,
        )
        if protocol.lower() == "sarg04":
            result["formula_note"] = "simplified_BB84_formula"
        if extra:
            result.update(extra)
        return result

    # --- Parameter estimation ---
    n_sampled, qber_est, rem_alice, rem_bob = _parameter_estimation(
        alice_bits, bob_bits, rng, sample_fraction, sample_min
    )
    n_remaining = len(rem_alice)

    # --- Abort rule 1: QBER too high ---
    if qber_est >= QBER_ABORT_THRESHOLD:
        h = h2(min(qber_est, 1.0 - 1e-12))   # safe clamp for display
        leak_ec = f_ec * n_remaining * h
        result = dict(
            protocol=protocol,
            n_raw=n_raw,
            n_detected=n_detected,
            n_sifted=n_sifted,
            n_sampled=n_sampled,
            qber_est=qber_est,
            leak_ec=leak_ec,
            final_key_length_asymptotic=0,
            final_key_length_finite=0,
            aborted=True,
            abort_reason=f"qber_est={qber_est:.4f}_>=_{QBER_ABORT_THRESHOLD}",
            config=config_used,
        )
        if protocol.lower() == "sarg04":
            result["formula_note"] = "simplified_BB84_formula"
        if extra:
            result.update(extra)
        return result

    # --- EC leakage model ---
    h_val = h2(qber_est)
    leak_ec = f_ec * n_remaining * h_val

    # --- Key lengths ---
    l_asym = _asymptotic_key_length(n_remaining, qber_est, f_ec, eps_sec)
    l_finite = finite_key_length(n_remaining, qber_est, f_ec, eps_sec, eps_pe)

    # --- Abort rule 2: no key produced ---
    aborted = (l_asym <= 0)
    abort_reason = ("key_length_non_positive" if aborted else None)

    result = dict(
        protocol=protocol,
        n_raw=n_raw,
        n_detected=n_detected,
        n_sifted=n_sifted,
        n_sampled=n_sampled,
        qber_est=qber_est,
        leak_ec=leak_ec,
        final_key_length_asymptotic=l_asym,
        final_key_length_finite=l_finite,
        aborted=aborted,
        abort_reason=abort_reason,
        config=config_used,
    )
    if protocol.lower() == "sarg04":
        result["formula_note"] = "simplified_BB84_formula"
    if extra:
        result.update(extra)
    return result
