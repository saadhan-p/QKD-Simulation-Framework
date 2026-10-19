"""
tests/test_aurora_state_check.py
================================
Unit tests for the linear algebraic verification of Aurora's state space.
"""

import numpy as np
import pytest

from analysis.aurora_state_check import (
    build_aurora_states,
    compute_gram_matrix,
    evaluate_posterior,
    simulate_intercept_resend,
)


def test_gram_matrix_convention_hadamard():
    states = build_aurora_states("hadamard")
    assert len(states) == 4
    G, rank, is_identity = compute_gram_matrix(states)
    assert rank == 4
    assert is_identity is True
    assert np.allclose(G, np.eye(4), atol=1e-12)


def test_gram_matrix_convention_computational():
    states = build_aurora_states("computational")
    assert len(states) == 4
    G, rank, is_identity = compute_gram_matrix(states)
    assert rank == 4
    assert is_identity is True
    assert np.allclose(G, np.eye(4), atol=1e-12)


@pytest.mark.parametrize("eps", [0.0, 0.02, 0.05, 0.10])
@pytest.mark.parametrize("w", [0.1, 0.5, 0.9])
def test_symmetric_posterior_is_half(eps, w):
    states = build_aurora_states("hadamard")
    valid, p0, p1, post0 = evaluate_posterior(states, w, w, eps)
    assert valid is True
    assert post0 == pytest.approx(0.5, abs=1e-12)


def test_asymmetric_posterior_biased():
    states = build_aurora_states("hadamard")
    valid, p0, p1, post0 = evaluate_posterior(states, 0.95, 0.05, 0.0)
    assert valid is True
    # When w0 >> w1, M_perp is almost entirely in the subspace of bit 1, so P(0 | M_perp) approaches 0.05 / 1.0 = 0.05
    assert post0 < 0.10


def test_eve_intercept_resend_qber_zero():
    qber = simulate_intercept_resend(n=50_000, convention="hadamard", seed=123)
    assert qber == 0.0
