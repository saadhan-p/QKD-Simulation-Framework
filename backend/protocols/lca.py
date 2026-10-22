"""
backend/protocols/lca.py
========================
Faithful biased-basis BB84 engine based on Lo-Chau-Ardehali (2005) "LCA".

Primary Reference:
- Hoi-Kwong Lo, H. F. Chau, and M. Ardehali,
  "Efficient Quantum Key Distribution Scheme And Proof of Its Unconditional Security",
  Journal of Cryptology 18, 133-165 (2005), arXiv:quant-ph/0011056v3.

Paper Sections Followed:
- Section 4.1 "Bias" (page 25): Alice and Bob independently choose between two bases
  with probabilities p_Z and 1 - p_Z.
- Section 4.2 "Refined Error Analysis" (page 26): Accepted data is divided by basis.
  The error rate for each basis is estimated separately; both must satisfy security tolerances.
- Section 4.3 "Protocol E: Protocol for efficient QKD" (pages 27-29):
  - Step (1): Alice chooses basis Z with prob p_Z and X with prob 1 - p_Z.
  - Step (2): Bob independently measures in basis Z with prob p_Z and X with prob 1 - p_Z.
  - Step (6): Partition detected clicks into four subsets: ZZ, XX, ZX, XZ. Discard mismatches (ZX, XZ).
  - Step (7): From ZZ events, randomly pick m1 (k_Z) test bits to estimate bit error e1 = r1 / m1.
              From XX events, randomly pick m2 (k_X) test bits to estimate phase error e2 = r2 / m2.
  - Step (8): Untested ZZ events (n = n_ZZ - k_Z) form the raw key.
- Section 4.4 "Outline proof of Security": Key is distilled from the Z basis; the bit-flip error rate
  is e_Z (estimated from ZZ) and the phase-flip error rate is e_X (estimated from XX).

Single-Code-Path Guarantee:
When p_Z = 0.5, the engine executes the EXACT same code path, reducing naturally to standard BB84
without any conditional branching on p_Z.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from ..finite_key import (
    compute_asymptotic_lca_rate,
    compute_tlgr2012_key_length,
)

# ---------------------------------------------------------------------------
# Default channel / detector parameters (consistent with bb84.py)
# ---------------------------------------------------------------------------
ETA_DET_DEFAULT: float = 0.10   # detector efficiency
E_CHANNEL_DEFAULT: float = 0.0  # channel optical misalignment error probability
DC_DEFAULT: float = 100.0       # dark count rate (Hz)
DT_DEFAULT: float = 1e-9        # gate width (s)


def run_lca(
    n_sent: int,
    rng: np.random.Generator,
    *,
    p_Z: float = 0.5,
    eta_ch: float = 1.0,
    eta_det: float = ETA_DET_DEFAULT,
    e_channel: float = E_CHANNEL_DEFAULT,
    dc: float = DC_DEFAULT,
    dt: float = DT_DEFAULT,
    # Parameter estimation config
    sample_fraction_z: float = 0.10,
    sample_min_z: int = 100,
    k_z: int | None = None,
    k_x: int | None = None,
    # Finite-key security config (Tomamichel et al. 2012)
    Q_tol: float = 0.11,
    f_ec: float = 1.16,
    eps_sec: float = 1e-10,
    eps_cor: float = 1e-10,
    q: float = 1.0,
) -> dict[str, Any]:
    """Run a faithful biased-basis BB84 (LCA) simulation block.

    Parameters
    ----------
    n_sent : int
        Number of optical pulses transmitted by Alice.
    rng : np.random.Generator
        Mandatory seeded NumPy Generator for reproducible physical Monte Carlo.
    p_Z : float
        Probability that Alice (and independently Bob) chooses basis Z (0 <= p_Z <= 1).
    eta_ch : float
        Channel optical transmission factor (0 <= eta_ch <= 1).
    eta_det : float
        Single-photon detector efficiency (default 0.10).
    e_channel : float
        Physical outcome-flip probability for matching-basis transmission.
    dc : float
        Detector dark count rate in Hz (default 100 Hz).
    dt : float
        Detector gate / time-bin width in seconds (default 1e-9 s = 1 ns).
    sample_fraction_z : float
        Fraction of ZZ events sampled for bit error estimation (default 0.10).
    sample_min_z : int
        Minimum number of ZZ events sampled for bit error estimation (default 100).
    k_z : int | None
        Explicit number of ZZ events to sample (overrides sample_fraction_z if given).
    k_x : int | None
        Explicit number of XX events to test for phase error estimation (defaults to all XX).
    Q_tol : float
        Phase error tolerance threshold for finite-key abort check (default 0.11).
    f_ec : float
        Error correction efficiency factor (default 1.16).
    eps_sec : float
        Secrecy parameter epsilon_sec (default 1e-10).
    eps_cor : float
        Correctness parameter epsilon_cor (default 1e-10).
    q : float
        Preparation quality (default 1.0 for BB84 qubit states).

    Returns
    -------
    dict[str, Any]
        Dictionary reporting counts, error estimates, sifting efficiencies,
        finite-key bound, asymptotic rates, and all protocol parameters.
    """
    if not (0.0 <= p_Z <= 1.0):
        raise ValueError(f"p_Z must be in [0, 1]; got {p_Z}")
    if n_sent < 0:
        raise ValueError(f"n_sent must be non-negative; got {n_sent}")

    p_detect_photon = eta_ch * eta_det
    p_dark = dc * dt

    # 1. Alice raw data generation
    # Basis 0 = Z, Basis 1 = X
    alice_bits = rng.integers(0, 2, size=n_sent, dtype=np.int8)
    alice_bases = np.where(rng.random(n_sent) < p_Z, 0, 1).astype(np.int8)

    # 2. Per-pulse channel detection and dark counts
    photon_detected = rng.random(n_sent) < p_detect_photon
    dark_count = rng.random(n_sent) < p_dark
    click = photon_detected | dark_count
    n_detected = int(click.sum())

    # 3. Bob basis choice (chosen independently with probability p_Z for Z)
    bob_bases = np.where(rng.random(n_sent) < p_Z, 0, 1).astype(np.int8)

    # 4. Bob measurement outcomes
    bob_bits = np.zeros(n_sent, dtype=np.int8)
    click_idx = np.where(click)[0]

    if click_idx.size > 0:
        photon_only = photon_detected[click_idx] & ~dark_count[click_idx]
        dark_only = dark_count[click_idx] & ~photon_detected[click_idx]
        both = photon_detected[click_idx] & dark_count[click_idx]

        # Case A: Real photon only (no dark count)
        if photon_only.any():
            po_idx = click_idx[photon_only]
            same_basis = (alice_bases[po_idx] == bob_bases[po_idx])

            # Matching basis: Alice's bit, flipped with probability e_channel
            sb_idx = po_idx[same_basis]
            if sb_idx.size > 0:
                flips = rng.random(sb_idx.size) < e_channel
                bob_bits[sb_idx] = np.where(flips, 1 - alice_bits[sb_idx], alice_bits[sb_idx])

            # Different basis: Uniform random bit
            db_idx = po_idx[~same_basis]
            if db_idx.size > 0:
                bob_bits[db_idx] = rng.integers(0, 2, size=db_idx.size, dtype=np.int8)

        # Case B: Dark count only (no photon) -> uniform random bit
        if dark_only.any():
            do_idx = click_idx[dark_only]
            bob_bits[do_idx] = rng.integers(0, 2, size=do_idx.size, dtype=np.int8)

        # Case C: Both photon and dark count -> conservative: random bit
        if both.any():
            bo_idx = click_idx[both]
            bob_bits[bo_idx] = rng.integers(0, 2, size=bo_idx.size, dtype=np.int8)

    # 5. Classify detected clicks into ZZ, XX, ZX, XZ
    if click_idx.size > 0:
        is_z_a = (alice_bases[click_idx] == 0)
        is_z_b = (bob_bases[click_idx] == 0)

        is_zz = is_z_a & is_z_b
        is_xx = (~is_z_a) & (~is_z_b)
        is_zx = is_z_a & (~is_z_b)
        is_xz = (~is_z_a) & is_z_b

        zz_pulse_idx = click_idx[is_zz]
        xx_pulse_idx = click_idx[is_xx]
        zx_pulse_idx = click_idx[is_zx]
        xz_pulse_idx = click_idx[is_xz]
    else:
        zz_pulse_idx = np.empty(0, dtype=int)
        xx_pulse_idx = np.empty(0, dtype=int)
        zx_pulse_idx = np.empty(0, dtype=int)
        xz_pulse_idx = np.empty(0, dtype=int)

    n_ZZ = int(len(zz_pulse_idx))
    n_XX = int(len(xx_pulse_idx))
    n_ZX = int(len(zx_pulse_idx))
    n_XZ = int(len(xz_pulse_idx))
    n_mismatch = n_ZX + n_XZ
    n_sifted = n_ZZ + n_XX

    # 6. Error estimation in ZZ and XX (LCA Protocol E Step 7 & Section 4.4)
    # Subset ZZ (key basis): Sample k_Z bits to estimate bit error rate e_Z
    if k_z is not None:
        target_kz = max(0, min(n_ZZ, k_z))
    else:
        target_kz = min(n_ZZ, max(sample_min_z, int(math.ceil(sample_fraction_z * n_ZZ))))

    if n_ZZ > 0 and target_kz > 0:
        sample_zz_rel_idx = rng.choice(n_ZZ, size=target_kz, replace=False)
        sample_zz_pulse_idx = zz_pulse_idx[sample_zz_rel_idx]
        errors_z = int(np.sum(alice_bits[sample_zz_pulse_idx] != bob_bits[sample_zz_pulse_idx]))
        sample_size_z = target_kz
        e_Z_est = errors_z / sample_size_z

        # Remaining untested ZZ bits are the raw key string (LCA Protocol E Step 8)
        mask = np.ones(n_ZZ, dtype=bool)
        mask[sample_zz_rel_idx] = False
        raw_key_pulse_idx = zz_pulse_idx[mask]
        n_key = int(len(raw_key_pulse_idx))
    else:
        sample_size_z = 0
        errors_z = 0
        e_Z_est = 0.0
        n_key = n_ZZ
        raw_key_pulse_idx = zz_pulse_idx

    # Subset XX (conjugate test basis): Sample k_X bits to estimate phase error e_X
    if k_x is not None:
        target_kx = max(0, min(n_XX, k_x))
    else:
        target_kx = n_XX  # by default, test all XX events for maximal statistical precision

    if n_XX > 0 and target_kx > 0:
        if target_kx == n_XX:
            sample_xx_pulse_idx = xx_pulse_idx
        else:
            sample_xx_rel_idx = rng.choice(n_XX, size=target_kx, replace=False)
            sample_xx_pulse_idx = xx_pulse_idx[sample_xx_rel_idx]
        errors_x = int(np.sum(alice_bits[sample_xx_pulse_idx] != bob_bits[sample_xx_pulse_idx]))
        sample_size_x = target_kx
        e_X_est = errors_x / sample_size_x
    else:
        sample_size_x = 0
        errors_x = 0
        e_X_est = 0.0

    # 7. Sifting and key-rate metrics
    sifting_efficiency = (n_sifted / n_detected) if n_detected > 0 else 0.0
    sifted_over_sent = (n_sifted / n_sent) if n_sent > 0 else 0.0
    key_bits_over_detected = (n_key / n_detected) if n_detected > 0 else 0.0
    key_bits_over_sent = (n_key / n_sent) if n_sent > 0 else 0.0

    # 8. Finite-key bound (Tomamichel et al. 2012 Eq. 2)
    fk_result = compute_tlgr2012_key_length(
        n=n_key,
        k=sample_size_x,
        Q_tol=Q_tol,
        observed_test_error=e_X_est,
        e_Z_est=e_Z_est,
        f_ec=f_ec,
        eps_sec=eps_sec,
        eps_cor=eps_cor,
        q=q,
    )
    finite_key_length = fk_result["finite_key_length"]
    finite_key_bits_per_pulse = (finite_key_length / n_sent) if n_sent > 0 else 0.0

    # 9. Asymptotic LCA rate (LCA 2005 Section 3.6 & 4.4)
    r_asym = compute_asymptotic_lca_rate(e_Z=e_Z_est, e_X=e_X_est, f_ec=f_ec)
    asymptotic_key_length = int(math.floor(n_key * r_asym))
    asymptotic_bits_per_pulse = (asymptotic_key_length / n_sent) if n_sent > 0 else 0.0

    return {
        # Transmission counts
        "n_sent": n_sent,
        "n_detected": n_detected,
        # Basis-specific detection counts
        "n_ZZ": n_ZZ,
        "n_XX": n_XX,
        "n_ZX": n_ZX,
        "n_XZ": n_XZ,
        "n_mismatch": n_mismatch,
        "n_sifted": n_sifted,
        "n_key": n_key,
        # Sifting metrics
        "sifting_efficiency": sifting_efficiency,
        "sifted_over_sent": sifted_over_sent,
        "key_bits_over_detected": key_bits_over_detected,
        "key_bits_over_sent": key_bits_over_sent,
        # Error estimation sampling
        "sample_size_z": sample_size_z,
        "errors_z": errors_z,
        "e_Z_est": e_Z_est,
        "sample_size_x": sample_size_x,
        "errors_x": errors_x,
        "e_X_est": e_X_est,
        # Finite-key bound results
        "finite_key_length": finite_key_length,
        "finite_key_bits_per_pulse": finite_key_bits_per_pulse,
        "aborted": fk_result["aborted"],
        "abort_reason": fk_result["abort_reason"],
        "mu": fk_result["mu"],
        "leak_ec": fk_result["leak_ec"],
        "delta_eps": fk_result["delta_eps"],
        "bound_source": fk_result["bound_source"],
        # Asymptotic results
        "r_asym": r_asym,
        "asymptotic_key_length": asymptotic_key_length,
        "asymptotic_bits_per_pulse": asymptotic_bits_per_pulse,
        # Parameters
        "p_Z": p_Z,
        "eta_ch": eta_ch,
        "eta_det": eta_det,
        "e_channel": e_channel,
        "dc": dc,
        "dt": dt,
        "p_dark_per_gate": p_dark,
        "Q_tol": Q_tol,
        "f_ec": f_ec,
        "eps_sec": eps_sec,
        "eps_cor": eps_cor,
        "q": q,
    }
