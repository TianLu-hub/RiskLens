"""Optimization constraints and comparison invariants."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.data.market_data import get_market_data_provider
from app.main import app
from app.optimization.optimizer import OptimizationUnavailableError, optimize_weights
from tests.test_api import SyntheticProvider


@pytest.fixture
def optimization_returns() -> pd.DataFrame:
    generator = np.random.default_rng(5)
    values = generator.normal(size=(756, 3)) * [0.005, 0.010, 0.018]
    values += [0.0002, 0.0006, 0.0010]
    return pd.DataFrame(values, columns=["LOW", "MID", "HIGH"])


def test_minimum_volatility_reduces_in_sample_risk(
    optimization_returns: pd.DataFrame,
) -> None:
    current = np.array([0.15, 0.15, 0.70])
    optimized = optimize_weights(
        optimization_returns, current, "minimum_volatility", 0.04, None
    ).weights
    covariance = optimization_returns.cov().to_numpy()
    assert np.sum(optimized) == pytest.approx(1.0, abs=1e-6)
    assert np.min(optimized) >= -1e-7
    assert optimized @ covariance @ optimized < current @ covariance @ current


def test_maximum_sharpe_respects_position_cap(
    optimization_returns: pd.DataFrame,
) -> None:
    current = np.array([0.15, 0.15, 0.70])
    optimized = optimize_weights(
        optimization_returns, current, "maximum_sharpe", 0.04, 0.45
    ).weights
    assert np.sum(optimized) == pytest.approx(1.0, abs=1e-6)
    assert np.min(optimized) >= -1e-7
    assert np.max(optimized) <= 0.45 + 1e-7


def test_risk_parity_equalizes_volatility_contributions(
    optimization_returns: pd.DataFrame,
) -> None:
    optimized = optimize_weights(
        optimization_returns,
        np.array([1 / 3, 1 / 3, 1 / 3]),
        "risk_parity",
        0.04,
        None,
    ).weights
    covariance = optimization_returns.cov().to_numpy()
    variance = optimized @ covariance @ optimized
    shares = optimized * (covariance @ optimized) / variance
    assert shares == pytest.approx([1 / 3] * 3, abs=0.005)


def test_singular_covariance_is_regularized() -> None:
    values = np.linspace(-0.01, 0.01, 100)
    returns = pd.DataFrame({"A": values, "B": values})
    result = optimize_weights(
        returns, np.array([0.5, 0.5]), "minimum_volatility", 0.04, None
    )
    assert result.covariance_regularized is True
    assert result.weights.sum() == pytest.approx(1.0)


def test_zero_volatility_rejected() -> None:
    returns = pd.DataFrame({"A": [0.01] * 100, "B": [0.01] * 100})
    with pytest.raises(OptimizationUnavailableError, match="zero sample volatility"):
        optimize_weights(
            returns, np.array([0.5, 0.5]), "minimum_volatility", 0.04, None
        )


def test_infeasible_cap_rejected_before_market_fetch() -> None:
    client = TestClient(app)
    response = client.post(
        "/portfolio/optimize",
        json={
            "positions": [
                {"ticker": "AAPL", "weight": 0.5},
                {"ticker": "MSFT", "weight": 0.5},
            ],
            "max_position_weight": 0.4,
        },
    )
    assert response.status_code == 422
    assert "infeasible" in response.text


def test_optimize_api_returns_reconciled_comparison() -> None:
    app.dependency_overrides[get_market_data_provider] = lambda: SyntheticProvider()
    try:
        client = TestClient(app)
        response = client.post(
            "/portfolio/optimize",
            json={
                "positions": [
                    {"ticker": "AAPL", "weight": 0.4},
                    {"ticker": "MSFT", "weight": 0.35},
                    {"ticker": "TLT", "weight": 0.25},
                ],
                "objective": "minimum_volatility",
                "max_position_weight": 0.6,
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200, response.text
    payload = response.json()
    allocations = payload["allocations"]
    assert sum(item["optimized_weight"] for item in allocations) == pytest.approx(
        1.0, abs=1e-6
    )
    assert payload["one_way_turnover"] == pytest.approx(
        sum(abs(item["weight_change"]) for item in allocations) / 2
    )
    assert (
        payload["optimized"]["annualized_volatility"]
        <= payload["current"]["annualized_volatility"] + 1e-6
    )
    assert payload["data_quality"]["source"] == "Synthetic Test Data"
