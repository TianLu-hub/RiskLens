"""Unit tests for deterministic portfolio calculations."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from app.risk.concentration import (
    effective_number_of_positions,
    herfindahl_hirschman_index,
    top_n_concentration,
)
from app.risk.contribution import volatility_risk_contributions
from app.risk.drawdown import drawdown_series, maximum_drawdown
from app.risk.metrics import (
    annualized_covariance,
    annualized_geometric_return,
    portfolio_returns,
    portfolio_volatility,
)
from app.risk.var import historical_cvar, historical_var


def test_portfolio_return_is_weighted_sum(
    asset_returns: pd.DataFrame, weights: np.ndarray
) -> None:
    result = portfolio_returns(asset_returns, weights)
    expected = asset_returns.mul(weights, axis=1).sum(axis=1)
    pd.testing.assert_series_equal(result, expected.rename("portfolio_return"))


def test_annualized_geometric_return() -> None:
    returns = pd.Series([0.01, -0.005, 0.012])
    expected = ((1.01 * 0.995 * 1.012) ** (252 / 3)) - 1
    assert annualized_geometric_return(returns) == pytest.approx(expected)


def test_volatility_formula(asset_returns: pd.DataFrame, weights: np.ndarray) -> None:
    covariance = annualized_covariance(asset_returns)
    expected = np.sqrt(weights.T @ covariance.to_numpy() @ weights)
    assert portfolio_volatility(covariance, weights) == pytest.approx(expected)


def test_historical_var_and_cvar() -> None:
    returns = pd.Series([-0.10, -0.04, -0.02, 0.01, 0.02])
    quantile = returns.quantile(0.20)
    expected_tail = returns[returns <= quantile]
    assert historical_var(returns, confidence_level=0.80) == pytest.approx(-quantile)
    assert historical_cvar(returns, confidence_level=0.80) == pytest.approx(
        -expected_tail.mean()
    )


def test_maximum_drawdown_includes_initial_wealth() -> None:
    returns = pd.Series([-0.10, 0.05, -0.20, 0.40])
    wealth = (1 + returns).cumprod()
    expected_drawdown = wealth / wealth.cummax().clip(lower=1.0) - 1
    pd.testing.assert_series_equal(
        drawdown_series(returns), expected_drawdown.rename("drawdown")
    )
    assert maximum_drawdown(returns) == pytest.approx(expected_drawdown.min())


def test_concentration_measures() -> None:
    weights = np.asarray([0.5, 0.3, 0.2])
    assert herfindahl_hirschman_index(weights) == pytest.approx(0.38)
    assert effective_number_of_positions(weights) == pytest.approx(1 / 0.38)
    assert top_n_concentration(weights, 2) == pytest.approx(0.8)


def test_risk_contributions_sum_to_one(
    asset_returns: pd.DataFrame, weights: np.ndarray
) -> None:
    covariance = annualized_covariance(asset_returns)
    result = volatility_risk_contributions(covariance, weights)
    assert result["risk_contribution"].sum() == pytest.approx(1.0, abs=1e-8)
    assert result["absolute_risk_contribution"].sum() == pytest.approx(
        portfolio_volatility(covariance, weights)
    )
