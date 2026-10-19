"""
tests/conftest.py
=================
Shared pytest fixtures for the QKD test suite.

Note: ``make_rng`` is defined here and re-exported so test modules can do
    ``from tests.conftest import make_rng``
or simply call ``np.random.default_rng(seed)`` directly.
"""

import sys
from pathlib import Path

import numpy as np
import pytest

# Make sure the project root is on sys.path so ``backend`` is importable
_project_root = str(Path(__file__).parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)


def make_rng(seed: int) -> np.random.Generator:
    """Helper: create a reproducible RNG from an integer seed."""
    return np.random.default_rng(seed)


@pytest.fixture
def seeded_rng():
    """Return a deterministically seeded numpy Generator (seed=42)."""
    return make_rng(42)


@pytest.fixture
def seeded_rng_alt():
    """Return a different deterministically seeded numpy Generator (seed=99)."""
    return make_rng(99)
