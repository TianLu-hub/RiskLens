"""Deterministic regression-based portfolio factor exposure estimates."""

from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np
import pandas as pd

from app.risk.metrics import TRADING_DAYS

MARKET_BENCHMARK = "SPY"
DEFAULT_ROLLING_WINDOW = 60


@dataclass(frozen=True)
class MarketFactorEstimate:
    """OLS estimate for portfolio excess returns against a market proxy."""

    available: bool
    alpha_annualized: float | None
    market_beta: float | None
    r_squared: float | None
    idiosyncratic_volatility: float | None
    observations: int
    rolling_beta: pd.Series
    unavailable_reason: str | None = None


def market_factor_regression(
    portfolio_return_series: pd.Series,
    market_return_series: pd.Series,
    annual_risk_free_rate: float,
    *,
    rolling_window: int = DEFAULT_ROLLING_WINDOW,
    periods_per_year: int = TRADING_DAYS,
) -> MarketFactorEstimate:
    """Estimate a CAPM-style market beta using daily excess returns.

    The intercept is annualized arithmetically as ``daily alpha * 252``.
    Rolling beta is the sample covariance divided by the sample market
    variance over the disclosed trailing window.
    """

    if rolling_window < 2:
        raise ValueError("Rolling beta window must contain at least two observations")

    aligned = pd.concat(
        [
            portfolio_return_series.rename("portfolio"),
            market_return_series.rename("market"),
        ],
        axis=1,
    ).dropna(how="any")
    observations = len(aligned)
    empty_rolling = pd.Series(dtype=float, name="rolling_beta")
    if observations < 3:
        return MarketFactorEstimate(
            available=False,
            alpha_annualized=None,
            market_beta=None,
            r_squared=None,
            idiosyncratic_volatility=None,
            observations=observations,
            rolling_beta=empty_rolling,
            unavailable_reason=(
                "Fewer than three aligned portfolio and benchmark returns are available."
            ),
        )

    daily_risk_free_rate = (1.0 + annual_risk_free_rate) ** (
        1.0 / periods_per_year
    ) - 1.0
    market_excess = aligned["market"] - daily_risk_free_rate
    portfolio_excess = aligned["portfolio"] - daily_risk_free_rate
    market_variance = float(market_excess.var(ddof=1))
    if not math.isfinite(market_variance) or market_variance <= 1e-18:
        return MarketFactorEstimate(
            available=False,
            alpha_annualized=None,
            market_beta=None,
            r_squared=None,
            idiosyncratic_volatility=None,
            observations=observations,
            rolling_beta=empty_rolling,
            unavailable_reason="The benchmark return variance is effectively zero.",
        )

    covariance = float(portfolio_excess.cov(market_excess))
    beta = covariance / market_variance
    daily_alpha = float(portfolio_excess.mean() - beta * market_excess.mean())
    fitted = daily_alpha + beta * market_excess
    residuals = portfolio_excess - fitted

    total_sum_squares = float(((portfolio_excess - portfolio_excess.mean()) ** 2).sum())
    residual_sum_squares = float((residuals**2).sum())
    r_squared = (
        max(0.0, min(1.0, 1.0 - residual_sum_squares / total_sum_squares))
        if total_sum_squares > 1e-18
        else None
    )
    idiosyncratic_volatility = float(
        residuals.std(ddof=1) * math.sqrt(periods_per_year)
    )

    rolling_covariance = portfolio_excess.rolling(rolling_window).cov(market_excess)
    rolling_variance = market_excess.rolling(rolling_window).var(ddof=1)
    rolling_beta = (
        (rolling_covariance / rolling_variance)
        .replace([np.inf, -np.inf], np.nan)
        .dropna()
    )
    rolling_beta.name = "rolling_beta"

    return MarketFactorEstimate(
        available=True,
        alpha_annualized=daily_alpha * periods_per_year,
        market_beta=beta,
        r_squared=r_squared,
        idiosyncratic_volatility=idiosyncratic_volatility,
        observations=observations,
        rolling_beta=rolling_beta,
    )
