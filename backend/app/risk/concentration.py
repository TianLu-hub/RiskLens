"""Weight-based portfolio concentration measures."""

from __future__ import annotations

import numpy as np


def herfindahl_hirschman_index(weights: np.ndarray) -> float:
    """Calculate HHI = sum(w_i^2)."""

    return float(np.square(weights).sum())


def effective_number_of_positions(weights: np.ndarray) -> float:
    """Calculate N_eff = 1 / HHI."""

    hhi = herfindahl_hirschman_index(weights)
    if hhi <= 0:
        raise ValueError("At least one portfolio weight must be positive")
    return float(1.0 / hhi)


def top_n_concentration(weights: np.ndarray, count: int = 3) -> float:
    """Return the sum of the largest count weights."""

    return float(np.sort(weights)[::-1][:count].sum())
