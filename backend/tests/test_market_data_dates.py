"""Daily samples require real, unique trading dates before alignment or caching."""

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


ARGS = (["SPY"], datetime(2025, 1, 1), datetime(2025, 6, 1))


def frame(index, multiindex=False):
    result = pd.DataFrame({"Adj Close": np.linspace(100, 120, len(index))}, index=index)
    if multiindex:
        result.columns = pd.MultiIndex.from_product([result.columns, ["SPY"]])
    return result


@pytest.mark.parametrize("multiindex", [False, True])
@pytest.mark.parametrize(
    "index",
    [
        pd.DatetimeIndex(["2025-01-02"] * 70),
        pd.date_range("2025-01-02", periods=70, freq="min"),
        pd.bdate_range("2025-01-02", periods=69).insert(20, pd.NaT),
        pd.RangeIndex(70),
        pd.Index(["not-a-date"] * 70),
        pd.Index(["2025-01-02", 1] * 35),
        pd.Index(pd.bdate_range("2025-01-02", periods=70).strftime("%Y-%m-%d")),
    ],
    ids=["duplicate", "same-day", "nat", "numeric", "invalid", "mixed", "strings"],
)
def test_invalid_dates_are_retryable_and_never_cached(monkeypatch, index, multiindex):
    raw = frame(index, multiindex)
    original = raw.copy(deep=True)
    valid = frame(pd.bdate_range("2025-01-02", periods=70), multiindex)
    responses = iter([raw, valid])
    monkeypatch.setattr(
        "app.data.market_data.yf.download", lambda *a, **k: next(responses)
    )
    provider = YahooFinanceProvider()

    with pytest.raises(MarketDataUnavailableError, match="trading dates"):
        provider.get_adjusted_prices(*ARGS)
    assert not provider._cache
    pd.testing.assert_frame_equal(raw, original)

    recovered = provider.get_adjusted_prices(*ARGS)
    assert recovered.provenance.cache_hit is False
    assert recovered.provenance.aligned_price_rows == 70
    assert provider.get_adjusted_prices(*ARGS).provenance.cache_hit is True


@pytest.mark.parametrize("timezone", [None, "America/New_York", "Pacific/Kiritimati"])
def test_valid_dates_sort_without_shifting_local_dates_or_prices(monkeypatch, timezone):
    dates = pd.bdate_range("2025-01-02", periods=70, tz=timezone)
    raw = frame(dates).iloc[::-1]
    original = raw.copy(deep=True)
    monkeypatch.setattr("app.data.market_data.yf.download", lambda *a, **k: raw)
    result = YahooFinanceProvider().get_adjusted_prices(*ARGS)
    expected = original.sort_index().rename(columns={"Adj Close": "SPY"})
    expected.index = dates.tz_localize(None)
    pd.testing.assert_frame_equal(result.prices, expected)
    pd.testing.assert_frame_equal(raw, original)
    assert result.provenance.price_start_date == "2025-01-02"
    assert result.provenance.price_end_date == dates[-1].date().isoformat()


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
def test_invalid_dates_return_service_unavailable(monkeypatch, path):
    raw = frame(pd.DatetimeIndex(["2025-01-02"] * 70))
    monkeypatch.setattr("app.data.market_data.yf.download", lambda *a, **k: raw)
    provider = YahooFinanceProvider()
    monkeypatch.setitem(
        app.dependency_overrides, get_market_data_provider, lambda: provider
    )
    with TestClient(app, raise_server_exceptions=False) as client:
        response = (
            client.get(path)
            if path.startswith("/market/")
            else client.post(path, json={"positions": [{"ticker": "SPY", "weight": 1}]})
        )
    assert response.status_code == 503
    assert "trading dates" in response.text
    assert "INVALID_TICKER" not in response.text
    assert not provider._cache
