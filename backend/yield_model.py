"""
backend/yield_model.py
======================
Expected-yield predictor and optimum parameter mapper for BB84-LCA with
Tomamichel-Lim-Gisin-Renner (TLGR) 2012 finite-key security bounds.

Formulas:
- Detection count model:
    M_det = g * N
    n_key = M_det * p_key^2
    k_test = M_det * (1 - p_key)^2
- Test basis error distribution:
    K_err ~ Binomial(k_test, e_test)
    Abort condition: K_err / k_test > Q_tol <=> K_err > floor(k_test * Q_tol)
    p_non_abort = P(K_err <= floor(k_test * Q_tol))
    - Exact binomial sum for k_test <= 1000
    - Documented normal approximation with continuity correction for k_test > 1000
- Finite secret key length bound (TLGR 2012 Eq. 2):
    mu = sqrt( (n + k)/(n*k) * (k+1)/k * ln(4 / eps_sec) )
    ell = max(0, floor( n * (q - h2(Q_tol + mu)) - leak_EC - 2*log2(1/eps_sec) - log2(2/eps_cor) ))
    where leak_EC = f_ec * n * h2(Q_tol) (predetermined_Qtol default)
- Expected finite yield:
    expected_rate = p_non_abort * (ell / N)
"""

from __future__ import annotations

import math
from typing import Any, Mapping

from backend.finite_key import compute_mu, compute_tlgr2012_key_length, truncated_h2


def compute_p_non_abort(k_test: int, e_test: float, Q_tol: float) -> float:
    """Compute probability that observed test error does not exceed Q_tol.

    K_err ~ Binomial(k_test, e_test).
    Protocol does NOT abort iff K_err <= floor(k_test * Q_tol).

    Uses exact binomial sum for k_test <= 1000, and documented normal
    approximation with continuity correction for k_test > 1000.
    """
    if k_test <= 0:
        return 0.0
    if Q_tol < 0.0:
        return 0.0
    if Q_tol >= 1.0:
        return 1.0
    if e_test <= 0.0:
        return 1.0 if Q_tol >= 0.0 else 0.0

    k_max = math.floor(k_test * Q_tol)
    if k_max < 0:
        return 0.0
    if k_max >= k_test:
        return 1.0

    if k_test <= 1000:
        # Exact binomial CDF via sum of PMFs
        prob = 0.0
        log_e = math.log(e_test)
        log_1me = math.log(1.0 - e_test)
        for i in range(k_max + 1):
            log_pmf = math.lgamma(k_test + 1) - math.lgamma(i + 1) - math.lgamma(k_test - i + 1) + i * log_e + (k_test - i) * log_1me
            prob += math.exp(log_pmf)
        return min(1.0, max(0.0, prob))
    else:
        # Documented normal approximation with continuity correction
        mean = k_test * e_test
        variance = k_test * e_test * (1.0 - e_test)
        if variance <= 0.0:
            return 1.0 if k_max >= mean else 0.0
        sigma = math.sqrt(variance)
        # Continuity correction: P(K <= k_max) approx Phi((k_max + 0.5 - mean) / sigma)
        z = (k_max + 0.5 - mean) / sigma
        prob = 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))
        return min(1.0, max(0.0, prob))


def expected_finite_yield(
    g: float,
    e_key: float,
    e_test: float,
    N: int | float,
    p_key: float,
    Q_tol: float,
    params: Mapping[str, Any] | None = None,
) -> tuple[float, float]:
    """Compute expected finite key rate per pulse sent and non-abort probability.

    Parameters
    ----------
    g : float
        Detection probability per pulse sent (0 < g <= 1).
    e_key : float
        Expected error rate on key basis events.
    e_test : float
        Expected error rate on test basis events.
    N : int or float
        Total number of pulses sent in the block.
    p_key : float
        Probability Alice and Bob choose the key basis.
    Q_tol : float
        Error tolerance threshold for abort test.
    params : Mapping[str, Any], optional
        Protocol configuration:
            - f_ec: Error correction efficiency (default 1.16)
            - eps_sec: Secrecy parameter (default 1e-10)
            - eps_cor: Correctness parameter (default 1e-10)
            - q: Preparation quality (default 1.0)
            - ec_leakage_model: 'predetermined_Qtol' (default) or 'measured_error'

    Returns
    -------
    tuple[float, float]
        (expected_key_bits_per_pulse_sent, p_non_abort)
    """
    if params is None:
        params = {}

    f_ec = float(params.get("f_ec", 1.16))
    eps_sec = float(params.get("eps_sec", 1e-10))
    eps_cor = float(params.get("eps_cor", 1e-10))
    q = float(params.get("q", 1.0))
    ec_leakage_model = str(params.get("ec_leakage_model", "predetermined_Qtol"))
    sample_fraction_z = float(params.get("sample_fraction_z", 0.10))
    sample_min_z = int(params.get("sample_min_z", 100))

    if g <= 0.0 or N <= 0 or p_key <= 0.0 or p_key >= 1.0:
        return 0.0, 0.0

    p_test = 1.0 - p_key
    m_det = g * N
    n_key_expected = m_det * (p_key ** 2)
    k_test_expected = m_det * (p_test ** 2)

    # Key basis error estimation bits sacrificed (LCA Protocol E Step 7 & 8)
    if n_key_expected > 0 and sample_fraction_z > 0.0:
        kz = min(n_key_expected, max(float(sample_min_z), math.ceil(sample_fraction_z * n_key_expected)))
    else:
        kz = 0.0

    n_k = int(math.floor(max(0.0, n_key_expected - kz)))
    k_t = int(math.floor(k_test_expected))

    if n_k <= 0 or k_t <= 0:
        return 0.0, 0.0

    # 1. Non-abort probability
    p_non_abort = compute_p_non_abort(k_t, e_test, Q_tol)

    # 2. Key length conditional on non-abort
    # For predetermined_Qtol, error correction uses Q_tol directly.
    # For measured_error, error correction uses e_key.
    res = compute_tlgr2012_key_length(
        n=n_k,
        k=k_t,
        Q_tol=Q_tol,
        observed_test_error=e_test,  # evaluation at expected test error
        e_Z_est=e_key,
        ec_leakage_model=ec_leakage_model,
        f_ec=f_ec,
        eps_sec=eps_sec,
        eps_cor=eps_cor,
        q=q,
    )

    ell = res["finite_key_length"]
    rate_cond = float(ell) / float(N)
    expected_rate = p_non_abort * rate_cond

    return expected_rate, p_non_abort
