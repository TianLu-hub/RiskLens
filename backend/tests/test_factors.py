"""Regression-based factor exposure invariants."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.data.market_data import PriceHistory, get_market_data_provider
from app.main import app

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


@pytest.mark.parametrize("amplitude", [0.0, 1e-11])
@pytest.mark.parametrize("risk_free", [0.0, 0.04])
@pytest.mark.parametrize("window", [20, 60])
def test_rolling_beta_omits_degenerate_windows_and_recovers(
    amplitude, risk_free, window
):
    index = pd.bdate_range("2024-01-02", periods=180)
    time = np.arange(60)
    market = pd.Series(
        np.r_[
            0.01 * np.sin(time / 7),
            0.001 + amplitude * np.sin(time),
            0.01 * np.cos(time / 5),
        ],
        index=index,
    )
    portfolio = pd.Series(0.008 * np.cos(np.arange(180) / 5), index=index)
    result = market_factor_regression(
        portfolio, market, risk_free, rolling_window=window
    )
    assert result.available is True
    # Full-sample OLS remains available; only near-zero-variance windows disappear.
    expected_beta = portfolio.cov(market) / market.var(ddof=1)
    assert result.market_beta == pytest.approx(expected_beta)
    daily_rf = (1 + risk_free) ** (1 / 252) - 1
    assert result.alpha_annualized == pytest.approx(
        ((portfolio - daily_rf).mean() - expected_beta * (market - daily_rf).mean())
        * 252
    )
    flat_window_ends = index[60 + window - 1 : 120]
    assert result.rolling_beta.index.intersection(flat_window_ends).empty
    assert index[window - 1] in result.rolling_beta.index
    assert index[-1] in result.rolling_beta.index
    expected_last = (
        portfolio.iloc[-window:].cov(market.iloc[-window:])
        / market.iloc[-window:].var()
    )
    assert result.rolling_beta.iloc[-1] == pytest.approx(expected_last)
    assert np.isfinite(result.rolling_beta).all()


def test_rolling_beta_retains_small_but_identifiable_market_variance():
    index = pd.bdate_range("2024-01-02", periods=120)
    market = pd.Series(1e-7 * np.sin(np.arange(120)), index=index)
    portfolio = 2.5 * market
    result = market_factor_regression(portfolio, market, 0)
    assert len(result.rolling_beta) == 61
    np.testing.assert_allclose(result.rolling_beta, 2.5, rtol=1e-8)


def test_analysis_api_omits_unstable_rolling_beta_and_discloses_policy(monkeypatch):
    index = pd.bdate_range("2024-01-02", periods=181)
    market = np.r_[
        0.01 * np.sin(np.arange(60) / 7), 0.001 + 1e-11 * np.sin(np.arange(120))
    ]
    stock = 0.008 * np.cos(np.arange(180) / 5)
    prices = pd.DataFrame(
        {
            "SPY": 100 * np.cumprod(np.r_[1, 1 + market]),
            "AAPL": 100 * np.cumprod(np.r_[1, 1 + stock]),
        },
        index=index,
    )

    class Provider:
        def get_adjusted_prices(self, tickers, start, end):
            return PriceHistory(
                prices=prices[tickers], source="Synthetic Test Data", warnings=[]
            )

    monkeypatch.setitem(app.dependency_overrides, get_market_data_provider, Provider)
    with TestClient(app) as client:
        response = client.post(
            "/portfolio/analyze",
            json={
                "positions": [
                    {"ticker": "AAPL", "weight": 0.5},
                    {"ticker": "SPY", "weight": 0.5},
                ]
            },
        )
    assert response.status_code == 200
    factor = response.json()["factor_exposure"]
    assert factor["available"] is True
    assert np.isfinite(factor["market_beta"])
    assert factor["rolling_beta"]
    flat_window_ends = {date.date().isoformat() for date in index[120:]}
    assert not {point["date"] for point in factor["rolling_beta"]} & flat_window_ends
    assert "omitted, not replaced by zero" in factor["methodology"]
