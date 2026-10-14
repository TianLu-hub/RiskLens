"""Portfolio return, volatility, and Sharpe calculations."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

TRADING_DAYS = 252


def daily_returns(prices: pd.DataFrame) -> pd.DataFrame:
    """Calculate aligned simple daily returns from adjusted prices."""

    if prices.empty:
        raise ValueError("Price history cannot be empty")
    returns = prices.pct_change(fill_method=None).dropna(how="any")
    if returns.empty:
        raise ValueError("Price history does not contain enough observations")
    return returns


def portfolio_returns(asset_returns: pd.DataFrame, weights: np.ndarray) -> pd.Series:
    """Calculate r_p,t = w^T r_t."""

    if asset_returns.shape[1] != len(weights):
        raise ValueError("Weight vector length must match the return matrix")
    return asset_returns.dot(weights).rename("portfolio_return")


def annualized_geometric_return(
    returns: pd.Series, periods_per_year: int = TRADING_DAYS
) -> float:
    """Annualize compounded simple returns geometrically."""

    if returns.empty:
        raise ValueError("Return series cannot be empty")
    growth = float(np.prod(1.0 + returns.to_numpy(dtype=float)))
    if growth <= 0:
        return -1.0
    return float(growth ** (periods_per_year / len(returns)) - 1.0)


def annualized_covariance(
    asset_returns: pd.DataFrame, periods_per_year: int = TRADING_DAYS
) -> pd.DataFrame:
    """Estimate the sample covariance matrix on an annual basis."""

    return asset_returns.cov() * periods_per_year


def portfolio_volatility(covariance: pd.DataFrame, weights: np.ndarray) -> float:
    """Calculate sqrt(w^T Sigma w), guarding floating-point roundoff."""

    matrix = covariance.to_numpy(dtype=float)
    variance = float(weights.T @ matrix @ weights)
    if variance < -1e-12:
        raise ValueError("Covariance matrix produced a negative portfolio variance")
    return float(math.sqrt(max(variance, 0.0)))


def sharpe_ratio(
    annualized_return: float, annualized_volatility: float, risk_free_rate: float
) -> float | None:
    """Return the annualized Sharpe estimate, or None for zero volatility."""

    if annualized_volatility <= 1e-12:
        return None
    return float((annualized_return - risk_free_rate) / annualized_volatility)
