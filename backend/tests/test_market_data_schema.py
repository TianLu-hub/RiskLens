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
    "bad_price", [0, -5, np.inf, -np.inf, True, 1 + 2j, "bad", "100"]
)
def test_invalid_observed_prices_are_rejected_before_caching(
    monkeypatch, yahoo_frame, bad_price
):
    # Preserve the actual provider dtype; do not coerce strings/bools to floats.
    values = (
        [bad_price] * 70
        if isinstance(bad_price, (bool, complex, str))
        else np.linspace(100, 120, 70)
    )
    raw = yahoo_frame({"Adj Close": values})
    raw.iloc[20, 0] = bad_price
    original = raw.copy(deep=True)
    monkeypatch.setattr("app.data.market_data.yf.download", lambda *a, **k: raw)
    provider = YahooFinanceProvider()
    with pytest.raises(MarketDataUnavailableError, match="strictly positive"):
        provider.get_adjusted_prices(
            ["SPY"], datetime(2025, 1, 1), datetime(2025, 6, 1)
        )
    assert not provider._cache
    pd.testing.assert_frame_equal(raw, original)


@pytest.mark.parametrize("dtype", ["float64", "Float64"])
def test_missing_prices_keep_existing_fill_and_provenance(
    monkeypatch, yahoo_frame, dtype
):
    raw = yahoo_frame({"Adj Close": np.linspace(100, 120, 70)}).astype(dtype)
    raw.iloc[20, 0] = np.nan
    monkeypatch.setattr("app.data.market_data.yf.download", lambda *a, **k: raw)
    result = YahooFinanceProvider().get_adjusted_prices(
        ["SPY"], datetime(2025, 1, 1), datetime(2025, 6, 1)
    )
    assert result.prices.iloc[20, 0] == result.prices.iloc[19, 0]
    assert result.provenance.assets[0].missing_prices == 1
    assert result.provenance.assets[0].filled_prices == 1
    assert len(result.prices) == 70


def test_invalid_prices_do_not_poison_retry(monkeypatch, yahoo_frame):
    raw = yahoo_frame({"Adj Close": np.linspace(100, 120, 70)})
    invalid = raw.copy()
    invalid.iloc[20, 0] = 0
    responses = iter([invalid, raw])
    monkeypatch.setattr(
        "app.data.market_data.yf.download", lambda *a, **k: next(responses)
    )
    provider = YahooFinanceProvider()
    args = (["SPY"], datetime(2025, 1, 1), datetime(2025, 6, 1))
    with pytest.raises(MarketDataUnavailableError):
        provider.get_adjusted_prices(*args)
    recovered = provider.get_adjusted_prices(*args)
    assert recovered.provenance.cache_hit is False
    assert recovered.prices.iloc[20, 0] > 0
    assert provider.get_adjusted_prices(*args).provenance.cache_hit is True


@pytest.mark.parametrize(
    "invalid_price", [False, True], ids=["missing-close", "zero-price"]
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
def test_bad_price_data_returns_service_unavailable(
    monkeypatch, yahoo_frame, path, invalid_price
):
    raw = yahoo_frame({"Adj Close": 0} if invalid_price else {"Volume": 1000})
    monkeypatch.setattr(
        "app.data.market_data.yf.download",
        lambda *a, **k: raw,
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
    assert ("strictly positive" if invalid_price else "closing prices") in response.text
    assert "INVALID_TICKER" not in response.text
    assert not provider._cache
