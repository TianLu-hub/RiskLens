"""Cumulative wealth and drawdown analysis."""

from __future__ import annotations

import pandas as pd


def wealth_index(returns: pd.Series) -> pd.Series:
    """Compound a simple return stream from an initial wealth of one."""

    return (1.0 + returns).cumprod().rename("wealth")


def drawdown_series(returns: pd.Series) -> pd.Series:
    """Calculate V_t / max(V_s) - 1 for s <= t."""

    wealth = wealth_index(returns)
    # The initial wealth of one is an eligible high-water mark, including when
    # the first observed return is negative.
    running_maximum = wealth.cummax().clip(lower=1.0)
    return (wealth / running_maximum - 1.0).rename("drawdown")


def maximum_drawdown(returns: pd.Series) -> float:
    """Return the most negative historical drawdown."""

    if returns.empty:
        raise ValueError("Return series cannot be empty")
    return float(drawdown_series(returns).min())
