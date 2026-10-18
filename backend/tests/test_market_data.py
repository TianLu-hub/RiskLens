"""Market-data provider cache behavior."""

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Barrier

import numpy as np
import pandas as pd
import pytest

from app.data.market_data import MarketDataUnavailableError, YahooFinanceProvider


@pytest.fixture
def raw_prices() -> pd.DataFrame:
    index = pd.bdate_range("2025-01-02", periods=70)
    return pd.DataFrame({"Adj Close": np.linspace(100, 110, len(index))}, index=index)


def fetch(provider: YahooFinanceProvider, ticker: str):
    return provider.get_adjusted_prices(
        [ticker], datetime(2025, 1, 1), datetime(2025, 6, 1)
    )


def test_expired_entries_are_reclaimed_even_when_not_requested_again(
    monkeypatch: pytest.MonkeyPatch, raw_prices: pd.DataFrame
) -> None:
    class Clock(datetime):
        current = datetime(2025, 6, 1, tzinfo=UTC)

        @classmethod
        def now(cls, tz=None):
            return cls.current

    monkeypatch.setattr("app.data.market_data.datetime", Clock)
    monkeypatch.setattr("app.data.market_data.yf.download", lambda *a, **k: raw_prices)
    provider = YahooFinanceProvider()
    fetch(provider, "OLD")
    Clock.current += timedelta(minutes=1)
    newer = fetch(provider, "NEWER")
    # Make OLD most recently used: expiry must not depend on LRU order,
    # and a cache hit must not renew its original fetch timestamp.
    assert fetch(provider, "OLD").provenance.cache_hit is True
    Clock.current += timedelta(minutes=14)
    fetch(provider, "LATEST")
    assert {key[0] for key in provider._cache} == {("NEWER",), ("LATEST",)}
    cached = fetch(provider, "NEWER")
    assert cached.provenance.cache_hit is True
    assert cached.provenance.fetched_at == newer.provenance.fetched_at


def test_capacity_evicts_least_recently_used_and_refetches_it(
    monkeypatch: pytest.MonkeyPatch, raw_prices: pd.DataFrame
) -> None:
    downloads = []

    def download(tickers, **kwargs):
        downloads.append(tickers[0])
        return raw_prices

    monkeypatch.setattr("app.data.market_data.yf.download", download)
    provider = YahooFinanceProvider(max_cache_entries=2)
    first = fetch(provider, "AAA")
    fetch(provider, "BBB")
    assert fetch(provider, "AAA").provenance.cache_hit is True
    fetch(provider, "CCC")
    assert len(provider._cache) == 2
    assert {key[0] for key in provider._cache} == {("AAA",), ("CCC",)}
    assert fetch(provider, "AAA").provenance.fetched_at == first.provenance.fetched_at
    assert fetch(provider, "BBB").provenance.cache_hit is False
    assert downloads == ["AAA", "BBB", "CCC", "BBB"]
    assert len(provider._cache) == 2


def test_failed_download_does_not_evict_valid_cache(
    monkeypatch: pytest.MonkeyPatch, raw_prices: pd.DataFrame
) -> None:
    def download(tickers, **kwargs):
        if tickers == ["FAIL"]:
            raise RuntimeError("transport failed")
        return raw_prices

    monkeypatch.setattr("app.data.market_data.yf.download", download)
    provider = YahooFinanceProvider(max_cache_entries=1)
    fetch(provider, "SPY")
    with pytest.raises(MarketDataUnavailableError):
        fetch(provider, "FAIL")
    assert fetch(provider, "SPY").provenance.cache_hit is True
    assert len(provider._cache) == 1


def test_concurrent_insertions_obey_cache_capacity(
    monkeypatch: pytest.MonkeyPatch, raw_prices: pd.DataFrame
) -> None:
    barrier = Barrier(4)

    def download(*args, **kwargs):
        barrier.wait(timeout=5)
        return raw_prices.copy()

    monkeypatch.setattr("app.data.market_data.yf.download", download)
    provider = YahooFinanceProvider(max_cache_entries=2)
    with ThreadPoolExecutor(max_workers=4) as executor:
        histories = list(
            executor.map(lambda ticker: fetch(provider, ticker), ["A", "B", "C", "D"])
        )
    assert len(provider._cache) == 2
    assert all(history.provenance.cache_hit is False for history in histories)
    assert all(len(history.prices) == 70 for history in histories)


@pytest.mark.parametrize("capacity", [0, -1])
def test_nonpositive_cache_capacity_is_rejected(capacity: int) -> None:
    with pytest.raises(ValueError, match="max_cache_entries"):
        YahooFinanceProvider(max_cache_entries=capacity)


def test_cached_history_is_isolated_from_caller_mutation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    index = pd.bdate_range("2025-01-02", periods=70)
    raw = pd.DataFrame({"Adj Close": np.linspace(100, 110, len(index))}, index=index)
    download_calls = 0

    def fake_download(*args: object, **kwargs: object) -> pd.DataFrame:
        nonlocal download_calls
        download_calls += 1
        return raw

    monkeypatch.setattr("app.data.market_data.yf.download", fake_download)
    provider = YahooFinanceProvider()
    start = datetime(2025, 1, 1)
    end = datetime(2025, 6, 1)

    first = provider.get_adjusted_prices(["SPY"], start, end)
    expected_first_price = first.prices.iloc[0, 0]
    expected_warnings = list(first.warnings)
    first.prices.iloc[0, 0] = -1
    first.warnings.append("caller mutation")

    second = provider.get_adjusted_prices(["SPY"], start, end)

    assert download_calls == 1
    assert second.prices.iloc[0, 0] == expected_first_price
    assert second.warnings == expected_warnings
    assert second.prices is not first.prices
    assert second.warnings is not first.warnings
