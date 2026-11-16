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


@pytest.mark.parametrize(
    "problem",
    [
        "duplicate_dates",
        "unsorted",
        "missing_date",
        "numeric_dates",
        "missing_ticker",
        "duplicate_ticker",
        "missing_price",
        "zero_price",
        "infinite_price",
        "string_prices",
        "overflow_return",
        "network",
    ],
)
def test_bad_optional_benchmark_preserves_core_analysis(monkeypatch, problem):
    snapshots = []

    class BrokenBenchmark(SyntheticProvider):
        def get_adjusted_prices(self, tickers, start, end):
            history = super().get_adjusted_prices(tickers, start, end)
            if tickers != ["SPY"]:
                return history
            if problem == "network":
                raise RuntimeError("private-upstream-diagnostic")
            prices = history.prices.copy()
            if problem in {"duplicate_dates", "missing_date"}:
                dates = list(prices.index)
                dates[10] = pd.NaT if problem == "missing_date" else dates[9]
                prices.index = pd.DatetimeIndex(dates)
            elif problem == "unsorted":
                prices = prices.iloc[::-1]
            elif problem == "numeric_dates":
                prices.index = pd.RangeIndex(len(prices))
            elif problem == "missing_ticker":
                prices.columns = ["NOT_SPY"]
            elif problem == "duplicate_ticker":
                prices = pd.concat([prices, prices], axis=1)
            elif problem == "string_prices":
                prices["SPY"] = "100"
            elif problem == "overflow_return":
                prices.iloc[9, 0] = 1e-300
                prices.iloc[10, 0] = 1e300
            else:
                prices.iloc[10, 0] = {
                    "missing_price": np.nan,
                    "zero_price": 0,
                    "infinite_price": np.inf,
                }[problem]
            snapshots.append((prices, prices.copy(deep=True)))
            return PriceHistory(
                prices=prices, source="Synthetic Test Data", warnings=[]
            )

    payload = {"positions": [{"ticker": "AAPL", "weight": 1.0}]}
    with TestClient(app, raise_server_exceptions=False) as client:
        monkeypatch.setitem(
            app.dependency_overrides, get_market_data_provider, SyntheticProvider
        )
        normal = client.post("/portfolio/analyze", json=payload)
        assert normal.status_code == 200
        assert normal.json()["factor_exposure"]["available"] is True
        monkeypatch.setitem(
            app.dependency_overrides, get_market_data_provider, BrokenBenchmark
        )
        response = client.post("/portfolio/analyze", json=payload)
    assert response.status_code == 200
    result = response.json()
    factor = result.pop("factor_exposure")
    expected_core = normal.json()
    expected_core.pop("factor_exposure")
    assert result == expected_core
    assert factor["available"] is False
    for field in (
        "market_beta",
        "alpha_annualized",
        "r_squared",
        "idiosyncratic_volatility",
        "benchmark_source",
    ):
        assert factor[field] is None
    assert factor["rolling_beta"] == []
    assert factor["observations"] == 0
    assert "core portfolio analytics remain valid" in factor["unavailable_reason"]
    assert "private-upstream-diagnostic" not in response.text
    for prices, original in snapshots:
        pd.testing.assert_frame_equal(prices, original)


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
