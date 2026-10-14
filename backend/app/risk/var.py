"""Historical value-at-risk and expected shortfall."""

from __future__ import annotations

import pandas as pd


def historical_var(returns: pd.Series, confidence_level: float = 0.95) -> float:
    """Return one-period historical VaR as a positive loss under normal cases."""

    _validate_inputs(returns, confidence_level)
    quantile = float(returns.quantile(1.0 - confidence_level))
    return -quantile


def historical_cvar(returns: pd.Series, confidence_level: float = 0.95) -> float:
    """Return expected shortfall conditional on returns at or below VaR quantile."""

    _validate_inputs(returns, confidence_level)
    quantile = float(returns.quantile(1.0 - confidence_level))
    tail = returns[returns <= quantile]
    return -float(tail.mean())


def _validate_inputs(returns: pd.Series, confidence_level: float) -> None:
    if returns.empty:
        raise ValueError("Return series cannot be empty")
    if not 0.0 < confidence_level < 1.0:
        raise ValueError("Confidence level must be between zero and one")
