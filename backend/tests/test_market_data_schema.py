"""Incomplete Yahoo responses must fail safely without poisoning the cache."""

from datetime import datetime

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.data.market_data import (
    MarketDataUnavailableError,
    YahooFinanceProvider,
    get_market_data_provider,
)
from app.main import app


@pytest.fixture(params=[False, True], ids=["flat", "multiindex"])
def yahoo_frame(request):
    def make(fields):
        frame = pd.DataFrame(fields, index=pd.bdate_range("2025-01-02", periods=70))
        if request.param:
            frame.columns = pd.MultiIndex.from_product([frame.columns, ["SPY"]])
        return frame

    return make


def test_missing_close_is_retryable_and_not_cached(monkeypatch, yahoo_frame):
    malformed = yahoo_frame({"Volume": 1000})
    valid = yahoo_frame({"Adj Close": np.linspace(100, 120, 70)})
    downloads = []

    def download(*args, **kwargs):
        downloads.append(args)
        return malformed if len(downloads) == 1 else valid

    monkeypatch.setattr("app.data.market_data.yf.download", download)
    provider = YahooFinanceProvider()
    args = (["SPY"], datetime(2025, 1, 1), datetime(2025, 6, 1))
    with pytest.raises(MarketDataUnavailableError, match="closing prices"):
        provider.get_adjusted_prices(*args)
    assert not provider._cache

    recovered = provider.get_adjusted_prices(*args)
    assert recovered.provenance.cache_hit is False
    assert recovered.prices["SPY"].iloc[-1] == 120
    assert provider.get_adjusted_prices(*args).provenance.cache_hit is True
    assert len(downloads) == 2


@pytest.mark.parametrize("adjusted", [False, True])
def test_close_selection_and_provenance_are_preserved(
    monkeypatch, yahoo_frame, adjusted
):
    fields = {"Close": np.linspace(200, 240, 70)}
    if adjusted:
        fields["Adj Close"] = np.linspace(100, 120, 70)
    monkeypatch.setattr(
        "app.data.market_data.yf.download", lambda *a, **k: yahoo_frame(fields)
    )
    history = YahooFinanceProvider().get_adjusted_prices(
        ["SPY"], datetime(2025, 1, 1), datetime(2025, 6, 1)
    )
    assert history.prices["SPY"].iloc[-1] == (120 if adjusted else 240)
    assert history.provenance.price_basis == (
        "adjusted_close" if adjusted else "unadjusted_close"
    )
    assert (
        any("unadjusted Close was used" in note for note in history.warnings)
        is not adjusted
    )


@pytest.mark.parametrize(
    "path",
    [
        "/portfolio/analyze",
        "/portfolio/optimize",
        "/portfolio/backtest",
        "/portfolio/var-backtest",
        "/market/history/SPY",
    ],
)
def test_missing_close_returns_service_unavailable(monkeypatch, yahoo_frame, path):
    monkeypatch.setattr(
        "app.data.market_data.yf.download",
        lambda *a, **k: yahoo_frame({"Volume": 1000}),
    )
    provider = YahooFinanceProvider()
    monkeypatch.setitem(
        app.dependency_overrides, get_market_data_provider, lambda: provider
    )
    client = TestClient(app, raise_server_exceptions=False)
    if path.startswith("/market/"):
        response = client.get(path)
    else:
        response = client.post(
            path, json={"positions": [{"ticker": "SPY", "weight": 1}]}
        )
    assert response.status_code == 503
    assert "closing prices" in response.text
    assert "INVALID_TICKER" not in response.text
    assert not provider._cache
