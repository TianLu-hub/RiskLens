"""Market-data provider cache behavior."""

from datetime import datetime

import numpy as np
import pandas as pd
import pytest

from app.data.market_data import YahooFinanceProvider


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
