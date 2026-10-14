"""Euler decomposition of annualized portfolio volatility."""

from __future__ import annotations

import numpy as np
import pandas as pd


def volatility_risk_contributions(
    covariance: pd.DataFrame, weights: np.ndarray
) -> pd.DataFrame:
    """Return marginal, absolute, and percentage volatility contributions."""

    matrix = covariance.to_numpy(dtype=float)
    sigma = float(np.sqrt(max(float(weights.T @ matrix @ weights), 0.0)))
    if sigma <= 1e-12:
        zeros = np.zeros_like(weights, dtype=float)
        return pd.DataFrame(
            {
                "marginal_risk": zeros,
                "absolute_risk_contribution": zeros,
                "risk_contribution": zeros,
            },
            index=covariance.index,
        )

    marginal = matrix @ weights / sigma
    absolute = weights * marginal
    percentage = absolute / sigma
    if not np.isclose(float(percentage.sum()), 1.0, atol=1e-8):
        raise ArithmeticError("Risk contributions do not sum to one")

    return pd.DataFrame(
        {
            "marginal_risk": marginal,
            "absolute_risk_contribution": absolute,
            "risk_contribution": percentage,
        },
        index=covariance.index,
    )
