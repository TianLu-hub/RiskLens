"""Regression-based factor exposure invariants."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from app.risk.factors import market_factor_regression


def test_market_factor_regression_recovers_known_beta_and_alpha() -> None:
    index = pd.bdate_range("2024-01-02", periods=120)
    market = pd.Series(0.001 + 0.01 * np.sin(np.arange(len(index)) / 7.0), index=index)
    daily_alpha = 0.0002
    portfolio = daily_alpha + 1.5 * market

    result = market_factor_regression(portfolio, market, 0.0)

    assert result.available is True
    assert result.market_beta == pytest.approx(1.5)
    assert result.alpha_annualized == pytest.approx(daily_alpha * 252)
    assert result.r_squared == pytest.approx(1.0)
    assert result.idiosyncratic_volatility == pytest.approx(0.0, abs=1e-12)
    assert len(result.rolling_beta) == 61
    assert result.rolling_beta.iloc[-1] == pytest.approx(1.5)


def test_market_factor_regression_uses_excess_returns() -> None:
    index = pd.bdate_range("2024-01-02", periods=90)
    annual_risk_free = 0.04
    daily_risk_free = (1.0 + annual_risk_free) ** (1.0 / 252) - 1.0
    market_excess = pd.Series(0.008 * np.cos(np.arange(len(index)) / 5.0), index=index)
    market = market_excess + daily_risk_free
    portfolio = daily_risk_free + 0.0001 + 0.8 * market_excess

    result = market_factor_regression(portfolio, market, annual_risk_free)

    assert result.market_beta == pytest.approx(0.8)
    assert result.alpha_annualized == pytest.approx(0.0001 * 252)


def test_market_factor_regression_rejects_zero_variance_benchmark() -> None:
    index = pd.bdate_range("2024-01-02", periods=30)
    market = pd.Series(0.0, index=index)
    portfolio = pd.Series(np.linspace(-0.01, 0.01, len(index)), index=index)

    result = market_factor_regression(portfolio, market, 0.0)

    assert result.available is False
    assert result.market_beta is None
    assert "variance" in (result.unavailable_reason or "").lower()
