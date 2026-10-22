"""
backend/finite_key.py
=====================
Finite-key security bounds and asymptotic key rate calculations for QKD.

Primary Reference:
- Marco Tomamichel, Charles Ci Wen Lim, Nicolas Gisin, and Renato Renner,
  "Tight Finite-Key Analysis for Quantum Cryptography",
  Nature Communications 3, Article 634 (2012), arXiv:1103.4130v2.
  - Main text Eq. (2): Closed-form finite-key length bound.
  - Supplementary Note 1, Eq. (S3)-(S4): Optimized finite-key length bound.
  - Table I: Protocol family Phi[n, k, ell, Q_tol, eps_cor, leak_EC] and abort condition.
  - Footnote 1 (page 12): Truncated binary entropy definition.

Decoy-State Reference (for comparison & context):
- Charles Ci Wen Lim, Marcos Curty, Nino Walenta, Feihu Xu, and Hugo Zbinden,
  "Concise Security Bounds for Practical Decoy-State Quantum Key Distribution",
  Phys. Rev. A 89, 022307 (2014), arXiv:1311.7129v1.
  - Eq. (1): Decoy-state finite key length bound.
  Note: Lim et al. (2014) is specifically derived for multi-intensity decoy states
  where vacuum events s_{X,0} and single-photon phase errors are estimated using
  multiple decoy settings. In the single-photon / prepare-and-measure qubit regime
  without decoy states, Tomamichel et al. (2012) provides the tight, directly applicable bound.

Asymptotic LCA Reference:
- Hoi-Kwong Lo, H. F. Chau, and M. Ardehali,
  "Efficient Quantum Key Distribution Scheme And Proof of Its Unconditional Security",
  Journal of Cryptology 18, 133-165 (2005), arXiv:quant-ph/0011056v3.
  - Section 3.6 & Section 4.4: Asymptotic key rate r_asym = 1 - f_EC * h2(e_Z) - h2(e_X).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Sequence


# ---------------------------------------------------------------------------
# Truncated binary entropy function
# ---------------------------------------------------------------------------
def truncated_h2(x: float) -> float:
    """Binary entropy function h(x) truncated at 0.5.

    Source: Tomamichel et al. (2012) arXiv:1103.4130v2, page 12, Footnote 1:
        "Here, h is a truncated binary entropy function,
         i.e. h : x |-> - x log2 x - (1-x) log2(1-x) if x <= 1/2 and 1 otherwise."

    For x == 0, returns 0.0 by continuity.
    Raises ValueError for x < 0.
    """
    if x < 0.0:
        raise ValueError(f"truncated_h2 argument must be non-negative; got {x}")
    if x >= 0.5:
        return 1.0
    if x == 0.0:
        return 0.0
    return -x * math.log2(x) - (1.0 - x) * math.log2(1.0 - x)


# ---------------------------------------------------------------------------
# Statistical fluctuation term mu
# ---------------------------------------------------------------------------
def compute_mu(n: int, k: int, eps_sec: float) -> float:
    """Compute the statistical fluctuation term mu.

    Source: Tomamichel et al. (2012) arXiv:1103.4130v2, Eq. (2):
        mu := sqrt( (n + k) / (n * k) * (k + 1) / k * ln(4 / eps_sec) )

    Parameters
    ----------
    n : int
        Number of raw key bits (from key basis).
    k : int
        Number of test bits (from conjugate basis).
    eps_sec : float
        Secrecy parameter.

    Returns
    -------
    float
        The fluctuation parameter mu. Returns math.inf if n <= 0 or k <= 0.
    """
    if n <= 0 or k <= 0:
        return math.inf
    if eps_sec <= 0.0 or eps_sec >= 1.0:
        raise ValueError(f"eps_sec must be in (0, 1); got {eps_sec}")

    ratio_total = (n + k) / (n * k)
    ratio_sample = (k + 1) / k
    log_term = math.log(4.0 / eps_sec)
    return math.sqrt(ratio_total * ratio_sample * log_term)


# ---------------------------------------------------------------------------
# Tomamichel et al. 2012 Eq. (2) finite-key length bound
# ---------------------------------------------------------------------------
def compute_tlgr2012_key_length(
    n: int,
    k: int,
    Q_tol: float,
    observed_test_error: float,
    e_Z_est: float,
    *,
    f_ec: float = 1.16,
    eps_sec: float = 1e-10,
    eps_cor: float = 1e-10,
    q: float = 1.0,
) -> dict[str, Any]:
    """Compute finite secret key length using Tomamichel et al. 2012 Eq. (2).

    Source: Tomamichel et al. (2012) arXiv:1103.4130v2:
        Eq. (2):
            ell <= n * (q - h(Q_tol + mu)) - leak_EC - log2(2 / (eps_sec^2 * eps_cor))
        where:
            mu := sqrt( (n + k) / (n * k) * (k + 1) / k * ln(4 / eps_sec) )
        Table I:
            The protocol aborts if observed_test_error > Q_tol.
        Error Correction Leakage model:
            leak_EC = f_ec * n * truncated_h2(e_Z_est)

    Parameters
    ----------
    n : int
        Number of key bits (remaining untested events in key basis).
    k : int
        Number of test bits (events in conjugate test basis).
    Q_tol : float
        Error tolerance threshold fixed before the run.
    observed_test_error : float
        Observed error rate on the k test bits (phase error estimation).
    e_Z_est : float
        Estimated bit error rate on key bits (from sample).
    f_ec : float
        Error correction efficiency factor (default 1.16).
    eps_sec : float
        Secrecy parameter epsilon_sec (default 1e-10).
    eps_cor : float
        Correctness parameter epsilon_cor (default 1e-10).
    q : float
        Preparation quality (1.0 for BB84 qubit states).

    Returns
    -------
    dict[str, Any]
        Dictionary containing key_length, aborted, and all audit parameters.
    """
    bound_id = "Tomamichel-Lim-Gisin-Renner 2012 Eq. (2)"

    # Protocol abort rule: Table I (Parameter Estimation)
    if observed_test_error > Q_tol:
        return {
            "bound_source": bound_id,
            "finite_key_length": 0,
            "aborted": True,
            "abort_reason": (
                f"Observed test error {observed_test_error:.5e} "
                f"exceeds tolerance Q_tol {Q_tol:.5e}"
            ),
            "n": n,
            "k": k,
            "Q_tol": Q_tol,
            "observed_test_error": observed_test_error,
            "e_Z_est": e_Z_est,
            "eps_sec": eps_sec,
            "eps_cor": eps_cor,
            "f_ec": f_ec,
            "q": q,
            "mu": compute_mu(n, k, eps_sec) if (n > 0 and k > 0) else math.inf,
            "leak_ec": 0.0,
            "delta_eps": 0.0,
            "raw_ell": 0.0,
        }

    if n <= 0 or k <= 0:
        return {
            "bound_source": bound_id,
            "finite_key_length": 0,
            "aborted": True,
            "abort_reason": f"Insufficient bits for key extraction (n={n}, k={k})",
            "n": n,
            "k": k,
            "Q_tol": Q_tol,
            "observed_test_error": observed_test_error,
            "e_Z_est": e_Z_est,
            "eps_sec": eps_sec,
            "eps_cor": eps_cor,
            "f_ec": f_ec,
            "q": q,
            "mu": math.inf,
            "leak_ec": 0.0,
            "delta_eps": 0.0,
            "raw_ell": 0.0,
        }

    mu = compute_mu(n, k, eps_sec)
    effective_phase_error = Q_tol + mu
    h_phase = truncated_h2(effective_phase_error)

    # EC leakage model: f_ec * n * h2(e_Z_est)
    h_bit = truncated_h2(e_Z_est)
    leak_ec = f_ec * n * h_bit

    # Security cost term: log2(2 / (eps_sec^2 * eps_cor))
    delta_eps = math.log2(2.0 / (eps_sec**2 * eps_cor))

    # Raw key length before floor
    raw_ell = n * (q - h_phase) - leak_ec - delta_eps

    if raw_ell > 0.0:
        finite_key_length = int(math.floor(raw_ell))
        aborted = False
        abort_reason = None
    else:
        finite_key_length = 0
        aborted = False
        abort_reason = "Raw key length <= 0 (finite-size and noise overhead exceed key capacity)"

    return {
        "bound_source": bound_id,
        "finite_key_length": finite_key_length,
        "aborted": aborted,
        "abort_reason": abort_reason,
        "n": n,
        "k": k,
        "Q_tol": Q_tol,
        "observed_test_error": observed_test_error,
        "e_Z_est": e_Z_est,
        "eps_sec": eps_sec,
        "eps_cor": eps_cor,
        "f_ec": f_ec,
        "q": q,
        "mu": mu,
        "effective_phase_error": effective_phase_error,
        "h_phase": h_phase,
        "leak_ec": leak_ec,
        "delta_eps": delta_eps,
        "raw_ell": raw_ell,
    }


# ---------------------------------------------------------------------------
# Supplementary Note 1 Eq. (S3)-(S4) Optimized Bound
# ---------------------------------------------------------------------------
def compute_tlgr2012_key_length_optimized(
    n: int,
    k: int,
    Q_tol: float,
    observed_test_error: float,
    e_Z_est: float,
    *,
    f_ec: float = 1.16,
    eps_sec: float = 1e-10,
    eps_cor: float = 1e-10,
    q: float = 1.0,
    num_grid_points: int = 100,
) -> dict[str, Any]:
    """Compute finite key length optimizing over epsilon and bar_epsilon.

    Source: Tomamichel et al. (2012) arXiv:1103.4130v2, Supplementary Note 1, Eq. (S3)-(S4):
        ell <= max_{eps, bar_eps} floor( n * (q - h(Q_tol + mu(eps))) - 2 log2(1 / (2 bar_eps)) - leak_EC - log2(2 / eps_cor) )
        subject to: 2 eps + bar_eps <= eps_sec
        where: mu(eps) = sqrt( (n + k)/(n*k) * (k+1)/k * ln(1/eps) )
    """
    bound_id = "Tomamichel-Lim-Gisin-Renner 2012 Eq. (S3)"

    if observed_test_error > Q_tol:
        return {
            "bound_source": bound_id,
            "finite_key_length": 0,
            "aborted": True,
            "abort_reason": f"Observed test error {observed_test_error:.5e} > Q_tol {Q_tol:.5e}",
            "n": n,
            "k": k,
            "Q_tol": Q_tol,
            "observed_test_error": observed_test_error,
            "e_Z_est": e_Z_est,
            "eps_sec": eps_sec,
            "eps_cor": eps_cor,
            "f_ec": f_ec,
            "q": q,
            "mu": math.inf,
            "leak_ec": 0.0,
            "delta_eps": 0.0,
            "raw_ell": 0.0,
        }

    if n <= 0 or k <= 0:
        return {
            "bound_source": bound_id,
            "finite_key_length": 0,
            "aborted": True,
            "abort_reason": f"Insufficient bits (n={n}, k={k})",
            "n": n,
            "k": k,
            "Q_tol": Q_tol,
            "observed_test_error": observed_test_error,
            "e_Z_est": e_Z_est,
            "eps_sec": eps_sec,
            "eps_cor": eps_cor,
            "f_ec": f_ec,
            "q": q,
            "mu": math.inf,
            "leak_ec": 0.0,
            "delta_eps": 0.0,
            "raw_ell": 0.0,
        }

    leak_ec = f_ec * n * truncated_h2(e_Z_est)
    log_cor = math.log2(2.0 / eps_cor)
    ratio_total = (n + k) / (n * k)
    ratio_sample = (k + 1) / k

    best_ell = 0
    best_mu = math.inf
    best_raw = -math.inf
    best_delta = 0.0

    # Grid search for eps in (0, eps_sec / 2)
    for i in range(1, num_grid_points):
        frac = i / num_grid_points
        eps = frac * (eps_sec / 2.0)
        bar_eps = eps_sec - 2.0 * eps
        if eps <= 0.0 or bar_eps <= 0.0:
            continue
        mu_candidate = math.sqrt(ratio_total * ratio_sample * math.log(1.0 / eps))
        h_phase = truncated_h2(Q_tol + mu_candidate)
        delta_candidate = 2.0 * math.log2(1.0 / (2.0 * bar_eps)) + log_cor
        raw = n * (q - h_phase) - leak_ec - delta_candidate
        ell_candidate = int(math.floor(raw)) if raw > 0 else 0
        if ell_candidate > best_ell or (best_raw == -math.inf and raw > best_raw):
            best_ell = ell_candidate
            best_mu = mu_candidate
            best_raw = raw
            best_delta = delta_candidate

    return {
        "bound_source": bound_id,
        "finite_key_length": max(0, best_ell),
        "aborted": False,
        "abort_reason": None if best_ell > 0 else "Raw key length <= 0",
        "n": n,
        "k": k,
        "Q_tol": Q_tol,
        "observed_test_error": observed_test_error,
        "e_Z_est": e_Z_est,
        "eps_sec": eps_sec,
        "eps_cor": eps_cor,
        "f_ec": f_ec,
        "q": q,
        "mu": best_mu,
        "effective_phase_error": Q_tol + best_mu,
        "leak_ec": leak_ec,
        "delta_eps": best_delta,
        "raw_ell": best_raw,
    }


# ---------------------------------------------------------------------------
# Lim et al. 2014 Single-Photon / Non-Decoy Reference Bound
# ---------------------------------------------------------------------------
def compute_lim2014_single_photon_bound(
    n: int,
    k: int,
    phi_X: float,
    e_Z_est: float,
    *,
    f_ec: float = 1.16,
    eps_sec: float = 1e-10,
    eps_cor: float = 1e-10,
) -> dict[str, Any]:
    """Compute key length bound using Lim et al. 2014 Eq. (1) specialized to single photons.

    Source: Lim et al. (2014) arXiv:1311.7129v1, Eq. (1):
        ell = floor( s_{X,0} + s_{X,1} - s_{X,1} * h(phi_X) - leak_EC - 6 log2(21 / eps_sec) - log2(2 / eps_cor) )
    When specialized to pure single photons (non-decoy):
        s_{X,0} = 0, s_{X,1} = n.

    Note: Lim et al. was specifically derived for decoy states. In single-photon
    qubit QKD, Tomamichel et al. (2012) is the tighter, standard bound.
    """
    bound_id = "Lim et al. 2014 Eq. (1) (single-photon specialization)"
    if n <= 0 or k <= 0:
        return {
            "bound_source": bound_id,
            "finite_key_length": 0,
            "aborted": True,
            "abort_reason": f"Insufficient bits (n={n}, k={k})",
            "n": n,
            "k": k,
            "phi_X": phi_X,
            "e_Z_est": e_Z_est,
            "eps_sec": eps_sec,
            "eps_cor": eps_cor,
            "leak_ec": 0.0,
            "delta_eps": 0.0,
            "raw_ell": 0.0,
        }

    leak_ec = f_ec * n * truncated_h2(e_Z_est)
    delta_sec = 6.0 * math.log2(21.0 / eps_sec)
    delta_cor = math.log2(2.0 / eps_cor)
    delta_eps = delta_sec + delta_cor

    h_phase = truncated_h2(phi_X)
    raw_ell = n * (1.0 - h_phase) - leak_ec - delta_eps
    finite_key_length = max(0, int(math.floor(raw_ell)))

    return {
        "bound_source": bound_id,
        "finite_key_length": finite_key_length,
        "aborted": False,
        "abort_reason": None if finite_key_length > 0 else "Raw key length <= 0",
        "n": n,
        "k": k,
        "phi_X": phi_X,
        "e_Z_est": e_Z_est,
        "eps_sec": eps_sec,
        "eps_cor": eps_cor,
        "f_ec": f_ec,
        "h_phase": h_phase,
        "leak_ec": leak_ec,
        "delta_eps": delta_eps,
        "raw_ell": raw_ell,
    }


# ---------------------------------------------------------------------------
# Asymptotic LCA key rate
# ---------------------------------------------------------------------------
def compute_asymptotic_lca_rate(
    e_Z: float,
    e_X: float,
    *,
    f_ec: float = 1.16,
) -> float:
    """Compute asymptotic LCA secret key fraction per key bit.

    Source: Lo, Chau, Ardehali (2005) arXiv:quant-ph/0011056v3:
        Section 3.6 & Section 4.4, Eq. (27)-(29):
            r_asym = max(0, 1 - f_EC * h2(e_Z) - h2(e_X))
    When e_Z == e_X == Q and f_EC == 1.0, this reduces to 1 - 2*h2(Q).

    Parameters
    ----------
    e_Z : float
        Bit error rate in key basis.
    e_X : float
        Phase error rate in conjugate test basis.
    f_ec : float
        Error correction efficiency factor (default 1.16).

    Returns
    -------
    float
        Asymptotic secret key fraction per raw key bit in [0, 1].
    """
    if e_Z < 0.0 or e_X < 0.0:
        raise ValueError(f"Error rates must be non-negative; got e_Z={e_Z}, e_X={e_X}")

    h_z = truncated_h2(e_Z)
    h_x = truncated_h2(e_X)
    raw_rate = 1.0 - f_ec * h_z - h_x
    return max(0.0, raw_rate)


# ---------------------------------------------------------------------------
# Public Block History and Controller Interface (Security Interface)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class BlockHistoryEntry:
    """Public statistics of a single completed block.

    Crucially:
    - Contains ONLY public statistics (counts, error rates, abort status).
    - Contains NO raw key bits.
    - Contains NO internal RNG states.
    - Immutable (frozen=True).
    """
    block_id: int
    n_sent: int
    n_detected: int
    n_ZZ: int
    n_XX: int
    n_mismatch: int
    sample_size_z: int
    errors_z: int
    sample_size_x: int
    errors_x: int
    e_Z_est: float
    e_X_est: float
    finite_key_length: int
    aborted: bool


@dataclass(frozen=True)
class History:
    """Immutable record of previous blocks' public statistics.

    Frozen to guarantee that history cannot be mutated by callers or controllers.
    Contains no current-block data and no raw key bits.
    """
    entries: tuple[BlockHistoryEntry, ...] = ()

    def append(self, entry: BlockHistoryEntry) -> History:
        """Return a new History instance with entry appended."""
        return History(entries=self.entries + (entry,))

    def __len__(self) -> int:
        return len(self.entries)

    def __getitem__(self, idx: int) -> BlockHistoryEntry:
        return self.entries[idx]


@dataclass(frozen=True)
class BlockParams:
    """Parameters for the next block run."""
    p_Z: float
    Q_tol: float
    N: int


class Controller:
    """Abstract controller interface."""
    def next_params(self, history: History) -> BlockParams:
        raise NotImplementedError


class FixedController(Controller):
    """Trivial fixed-parameter controller."""
    def __init__(self, p_Z: float, Q_tol: float, N: int):
        self.p_Z = p_Z
        self.Q_tol = Q_tol
        self.N = N

    def next_params(self, history: History) -> BlockParams:
        # History is inspected but fixed params are returned
        return BlockParams(p_Z=self.p_Z, Q_tol=self.Q_tol, N=self.N)
