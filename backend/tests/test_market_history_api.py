"""History requests validate symbols before calling the external data provider."""

from datetime import datetime
from unittest.mock import Mock
from urllib.parse import quote

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.data.market_data import (
    InsufficientHistoryError,
    InvalidTickerError,
    MarketDataProvider,
    MarketDataUnavailableError,
    PriceHistory,
    get_market_data_provider,
)
from app.main import app
from app.models.portfolio import Position


@pytest.fixture
def history_client():
    provider = Mock(spec=MarketDataProvider)
    # Fail closed: an unexpected provider call must never contact Yahoo.
    provider.get_adjusted_prices.side_effect = AssertionError("Unexpected data fetch")
    previous = app.dependency_overrides.copy()
    app.dependency_overrides[get_market_data_provider] = lambda: provider
    try:
        with TestClient(app) as client:
            yield client, provider
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)


@pytest.mark.parametrize(
    "ticker", [" ", "AAPL MSFT", "AAPL,MSFT", "$AAPL", "^GSPC", ".AAPL", "A" * 16]
)
def test_invalid_ticker_is_rejected_before_fetch(history_client, ticker):
    client, provider = history_client
    response = client.get(f"/market/history/{quote(ticker, safe='')}")

    assert response.status_code == 422
    provider.get_adjusted_prices.assert_not_called()
    # Both entry points enforce the same supported ticker policy.
    with pytest.raises(ValidationError):
        Position(ticker=ticker, weight=1.0)


@pytest.mark.parametrize("ticker", [" aapl ", "brk.b", "brk-b", "0700.hk"])
def test_valid_ticker_is_normalized_and_history_returned(history_client, ticker):
    client, provider = history_client
    normalized = Position(ticker=ticker, weight=1.0).ticker
    provider.get_adjusted_prices.side_effect = None
    provider.get_adjusted_prices.return_value = PriceHistory(
        prices=pd.DataFrame(
            {normalized: [100.0, 102.0]}, index=pd.bdate_range("2024-01-02", periods=2)
        ),
        source="Synthetic Test Data",
        warnings=[],
    )

    response = client.get(f"/market/history/{quote(ticker, safe='')}?lookback_years=3")

    assert response.status_code == 200
    assert response.json() == {
        "ticker": normalized,
        "source": "Synthetic Test Data",
        "history": [
            {"date": "2024-01-02", "adjusted_close": 100.0},
            {"date": "2024-01-03", "adjusted_close": 102.0},
        ],
    }
    provider.get_adjusted_prices.assert_called_once()
    symbols, start, end = provider.get_adjusted_prices.call_args.args
    assert symbols == [normalized]
    assert isinstance(start, datetime) and start < end
    assert (end - start).days == int(3 * 365.25) + 10


@pytest.mark.parametrize("lookback", [0, 11, "invalid"])
def test_invalid_lookback_does_not_fetch(history_client, lookback):
    client, provider = history_client
    response = client.get(f"/market/history/AAPL?lookback_years={lookback}")
    assert response.status_code == 422
    provider.get_adjusted_prices.assert_not_called()


@pytest.mark.parametrize(
    "error,status",
    [
        (InvalidTickerError(["NOTREAL"]), 404),
        (InsufficientHistoryError("History too short"), 422),
        (MarketDataUnavailableError("Network unavailable"), 503),
    ],
)
def test_provider_errors_keep_existing_http_status(history_client, error, status):
    client, provider = history_client
    provider.get_adjusted_prices.side_effect = error
    response = client.get("/market/history/NOTREAL")
    assert response.status_code == status
    provider.get_adjusted_prices.assert_called_once()
    if status == 404:
        assert response.json()["detail"]["tickers"] == ["NOTREAL"]
