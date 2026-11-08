"""Provider-independent validation for aligned historical backtest prices."""

import numpy as np
import pandas as pd
from pandas.api.types import is_bool_dtype, is_complex_dtype, is_numeric_dtype

from app.data.market_data import MarketDataUnavailableError


def validated_provider_prices(prices: pd.DataFrame, tickers: list[str]) -> pd.DataFrame:
    """Reject malformed provider history without repairing or mutating its data."""

    if not isinstance(prices, pd.DataFrame):
        raise MarketDataUnavailableError(
            "The market data provider returned invalid price history. Please try again."
        )
    if (
        isinstance(prices.columns, pd.MultiIndex)
        or not prices.columns.is_unique
        or any(ticker not in prices.columns for ticker in tickers)
    ):
        raise MarketDataUnavailableError(
            "The market data provider returned invalid price history: "
            "requested ticker columns are missing or duplicated. Please try again."
        )
    if (
        not isinstance(prices.index, pd.DatetimeIndex)
        or prices.index.hasnans
        or not prices.index.normalize().is_unique
        or not prices.index.is_monotonic_increasing
    ):
        raise MarketDataUnavailableError(
            "The market data provider returned invalid price history: "
            "dates must be valid, unique, and sorted. Please try again."
        )
    selected = prices[tickers]
    invalid_prices_message = (
        "The market data provider returned invalid price history: "
        "prices must be finite, numeric, and strictly positive. Please try again."
    )
    if any(
        not is_numeric_dtype(dtype) or is_bool_dtype(dtype) or is_complex_dtype(dtype)
        for dtype in selected.dtypes
    ):
        raise MarketDataUnavailableError(invalid_prices_message)
    values = selected.to_numpy(dtype=float, na_value=np.nan)
    if not np.isfinite(values).all() or (values <= 0).any():
        raise MarketDataUnavailableError(invalid_prices_message)
    return selected
