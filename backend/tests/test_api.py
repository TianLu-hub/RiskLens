"""API integration tests with an in-memory market-data provider."""

from __future__ import annotations

from datetime import datetime

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.data.market_data import (
    InvalidTickerError,
    MarketDataProvider,
    PriceHistory,
    get_market_data_provider,
)
from app.main import app


class SyntheticProvider(MarketDataProvider):
    def get_adjusted_prices(
        self, tickers: list[str], start: datetime, end: datetime
    ) -> PriceHistory:
        index = pd.bdate_range("2023-01-02", periods=520)
        time = np.arange(len(index), dtype=float)
        prices = pd.DataFrame(index=index)
        for offset, ticker in enumerate(tickers):
            daily = 0.0003 + 0.0001 * offset + 0.006 * np.sin(time / (8 + offset))
            prices[ticker] = 100 * np.cumprod(1 + daily)
        return PriceHistory(prices=prices, source="Synthetic Test Data", warnings=[])


class InvalidProvider(MarketDataProvider):
    def get_adjusted_prices(
        self, tickers: list[str], start: datetime, end: datetime
    ) -> PriceHistory:
        raise InvalidTickerError(tickers)


def test_health() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_cors_preflight_allows_browser_client_headers() -> None:
    client = TestClient(app)
    response = client.options(
        "/portfolio/analyze",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type,x-risklens-client",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert "x-risklens-client" in response.headers["access-control-allow-headers"]


def test_analyze_portfolio_response() -> None:
    app.dependency_overrides[get_market_data_provider] = lambda: SyntheticProvider()
    client = TestClient(app)
    response = client.post(
        "/portfolio/analyze",
        json={
            "positions": [
                {"ticker": "AAPL", "weight": 0.4},
                {"ticker": "MSFT", "weight": 0.35},
                {"ticker": "TLT", "weight": 0.25},
            ],
            "lookback_years": 3,
            "risk_free_rate": 0.04,
        },
    )
    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["data_quality"]["observations"] == 519
    assert payload["data_quality"]["source"] == "Synthetic Test Data"
    assert len(payload["correlation"]["matrix"]) == 3
    assert (
        abs(
            sum(item["risk_contribution"] for item in payload["risk_contributions"]) - 1
        )
        < 1e-6
    )
    assert payload["concentration"]["hhi"] == pytest.approx(0.345)
    assert payload["factor_exposure"]["available"] is True
    assert payload["factor_exposure"]["benchmark_ticker"] == "SPY"
    assert payload["factor_exposure"]["smb_beta"] is None
    assert payload["factor_exposure"]["hml_beta"] is None
    assert payload["factor_exposure"]["observations"] == 519
    assert payload["factor_exposure"]["rolling_window_days"] == 60
    assert len(payload["factor_exposure"]["rolling_beta"]) == 460


def test_invalid_ticker_handling() -> None:
    app.dependency_overrides[get_market_data_provider] = lambda: InvalidProvider()
    client = TestClient(app)
    response = client.post(
        "/portfolio/analyze",
        json={"positions": [{"ticker": "NOTREAL", "weight": 1.0}]},
    )
    app.dependency_overrides.clear()

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["code"] == "INVALID_TICKER"
    assert detail["tickers"] == ["NOTREAL"]


def test_api_rejects_bad_weight_sum_before_data_fetch() -> None:
    client = TestClient(app)
    response = client.post(
        "/portfolio/analyze",
        json={
            "positions": [
                {"ticker": "AAPL", "weight": 0.6},
                {"ticker": "MSFT", "weight": 0.3},
            ]
        },
    )
    assert response.status_code == 422
