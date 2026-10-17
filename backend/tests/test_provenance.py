"""Auditable market metadata without changing calculations or using network data."""

from datetime import UTC, datetime, timedelta

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.data.market_data import YahooFinanceProvider, get_market_data_provider
from app.main import app
from tests.test_api import SyntheticProvider


def prices(days: int = 70) -> pd.DataFrame:
    index = pd.bdate_range("2025-01-02", periods=days)
    return pd.DataFrame(
        {"Adj Close": 100 * np.cumprod(1 + 0.001 + 0.01 * np.sin(np.arange(days)))},
        index=index,
    )


def test_cache_provenance_retains_fetch_time_and_expires(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Clock(datetime):
        current = datetime(2025, 6, 1, tzinfo=UTC)

        @classmethod
        def now(cls, tz=None):
            return cls.current

    raw = prices()
    calls = []
    monkeypatch.setattr("app.data.market_data.datetime", Clock)
    monkeypatch.setattr(
        "app.data.market_data.yf.download", lambda *a, **k: calls.append(1) or raw
    )
    provider = YahooFinanceProvider()
    start, end = datetime(2025, 1, 1), datetime(2025, 6, 1)
    first = provider.get_adjusted_prices(["SPY"], start, end)
    fetched = first.provenance.fetched_at
    first.provenance.assets[0].missing_prices = 999
    Clock.current += timedelta(minutes=1)
    second = provider.get_adjusted_prices(["SPY"], start, end)
    assert first.provenance.cache_hit is False
    assert second.provenance.cache_hit is True
    assert second.provenance.fetched_at == fetched
    assert second.provenance.assets[0].missing_prices == 0
    assert len(calls) == 1
    Clock.current += timedelta(minutes=14)
    third = provider.get_adjusted_prices(["SPY"], start, end)
    assert third.provenance.cache_hit is False
    assert third.provenance.fetched_at > fetched
    assert len(calls) == 2


def test_missing_alignment_and_trailing_fill_are_disclosed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw = prices(80)
    raw.iloc[:2, 0] = np.nan
    raw.iloc[10:15, 0] = np.nan
    raw.iloc[-1, 0] = np.nan
    monkeypatch.setattr("app.data.market_data.yf.download", lambda *a, **k: raw)
    history = YahooFinanceProvider().get_adjusted_prices(
        ["SPY"], datetime(2025, 1, 1), datetime(2025, 6, 1)
    )
    meta = history.provenance
    assert meta.raw_price_rows == 80
    assert meta.aligned_price_rows == 76
    assert meta.dropped_price_rows == 4
    assert meta.assets[0].observed_prices == 72
    assert meta.assets[0].missing_prices == 8
    assert meta.assets[0].filled_prices == 4
    assert meta.assets[0].last_observed_date == raw.index[-2].date().isoformat()
    assert meta.price_end_date == raw.index[-1].date().isoformat()
    pd.testing.assert_frame_equal(
        history.prices, raw.rename(columns={"Adj Close": "SPY"}).ffill(limit=3).dropna()
    )


def test_unadjusted_fallback_is_machine_readable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw = prices().rename(columns={"Adj Close": "Close"})
    monkeypatch.setattr("app.data.market_data.yf.download", lambda *a, **k: raw)
    history = YahooFinanceProvider().get_adjusted_prices(
        ["SPY"], datetime(2025, 1, 1), datetime(2025, 6, 1)
    )
    assert history.provenance.price_basis == "unadjusted_close"
    assert any("unadjusted" in warning for warning in history.warnings)


@pytest.mark.parametrize("endpoint", ["analyze", "optimize", "backtest"])
def test_api_propagates_metadata_and_actual_sample(
    endpoint: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    raw = prices(300)
    monkeypatch.setattr("app.data.market_data.yf.download", lambda *a, **k: raw)
    provider = YahooFinanceProvider()
    app.dependency_overrides[get_market_data_provider] = lambda: provider
    try:
        client = TestClient(app)
        payload = {"positions": [{"ticker": "SPY", "weight": 1}], "training_days": 252}
        # Only the backtest request accepts training_days (other models forbid extras).
        if endpoint != "backtest":
            payload.pop("training_days")
        first = client.post(f"/portfolio/{endpoint}", json=payload)
        assert first.status_code == 200, first.text
        second = client.post(f"/portfolio/{endpoint}", json=payload)
        assert second.status_code == 200, second.text
        data = second.json()["data_quality"]
        assert data["observations"] == 299
        assert data["start_date"] == raw.index[1].date().isoformat()
        assert data["provenance"]["aligned_price_rows"] == 300
        assert data["provenance"]["cache_hit"] is True
        assert (
            data["provenance"]["fetched_at"]
            == first.json()["data_quality"]["provenance"]["fetched_at"]
        )
    finally:
        app.dependency_overrides.clear()


def test_provider_without_metadata_does_not_fabricate_fetch_time() -> None:
    app.dependency_overrides[get_market_data_provider] = lambda: SyntheticProvider()
    try:
        response = TestClient(app).post(
            "/portfolio/analyze", json={"positions": [{"ticker": "SPY", "weight": 1}]}
        )
        assert response.status_code == 200
        assert response.json()["data_quality"]["provenance"] is None
    finally:
        app.dependency_overrides.clear()
