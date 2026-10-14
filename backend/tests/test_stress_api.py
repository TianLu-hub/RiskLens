"""Phase 2 stress-test API integration tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app


def test_stress_test_endpoint() -> None:
    client = TestClient(app)
    response = client.post(
        "/portfolio/stress-test",
        json={
            "positions": [
                {"ticker": "AAPL", "weight": 0.20},
                {"ticker": "MSFT", "weight": 0.20},
                {"ticker": "NVDA", "weight": 0.15},
                {"ticker": "SPY", "weight": 0.25},
                {"ticker": "TLT", "weight": 0.20},
            ],
            "portfolio_value": 100_000,
            "scenario_name": "Custom Scenario",
            "market_shock": -0.10,
            "tech_shock": -0.15,
            "rates_shock_bps": 100,
            "ticker_shocks": {"NVDA": -0.30},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["scenario_classification"] == "hypothetical"
    assert payload["historical_data_used"] is False
    assert payload["portfolio_value_before"] == 100_000
    assert payload["portfolio_value_after"] == pytest.approx(
        100_000 * (1 + payload["estimated_portfolio_return"])
    )
    assert sum(
        item["portfolio_contribution"] for item in payload["asset_contributions"]
    ) == pytest.approx(payload["estimated_portfolio_return"])


def test_stress_api_rejects_empty_scenario() -> None:
    client = TestClient(app)
    response = client.post(
        "/portfolio/stress-test",
        json={"positions": [{"ticker": "SPY", "weight": 1.0}]},
    )

    assert response.status_code == 422
