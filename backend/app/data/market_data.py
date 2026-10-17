"""Replaceable market-data access with validation, alignment, and TTL caching."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from threading import Lock

import pandas as pd
import yfinance as yf


class MarketDataError(RuntimeError):
    """Base class for user-safe market-data failures."""


class InvalidTickerError(MarketDataError):
    """Raised when one or more tickers have no usable history."""

    def __init__(self, tickers: list[str]) -> None:
        self.tickers = tickers
        super().__init__(f"No usable price history for: {', '.join(tickers)}")


class MarketDataUnavailableError(MarketDataError):
    """Raised when the upstream provider cannot be reached."""


class InsufficientHistoryError(MarketDataError):
    """Raised when aligned data cannot support reliable analytics."""


@dataclass(frozen=True)
class PriceHistory:
    """Normalized adjusted closing prices plus data-quality notes."""

    prices: pd.DataFrame
    source: str
    warnings: list[str]


class MarketDataProvider(ABC):
    """Interface implemented by all future price-history providers."""

    @abstractmethod
    def get_adjusted_prices(
        self, tickers: list[str], start: datetime, end: datetime
    ) -> PriceHistory:
        """Return aligned adjusted closing prices for all requested tickers."""


class YahooFinanceProvider(MarketDataProvider):
    """Yahoo Finance implementation isolated behind the provider interface."""

    def __init__(self, cache_ttl: timedelta = timedelta(minutes=15)) -> None:
        self.cache_ttl = cache_ttl
        self._cache: dict[
            tuple[tuple[str, ...], str, str], tuple[datetime, PriceHistory]
        ] = {}
        self._lock = Lock()

    def get_adjusted_prices(
        self, tickers: list[str], start: datetime, end: datetime
    ) -> PriceHistory:
        normalized = sorted({ticker.strip().upper() for ticker in tickers})
        key = (tuple(normalized), start.date().isoformat(), end.date().isoformat())
        now = datetime.now(UTC)

        with self._lock:
            cached = self._cache.get(key)
            if cached and now - cached[0] < self.cache_ttl:
                return self._copy_history(cached[1])

        try:
            raw = yf.download(
                normalized,
                start=start.date().isoformat(),
                end=end.date().isoformat(),
                auto_adjust=False,
                progress=False,
                threads=True,
                group_by="column",
            )
        except Exception as exc:  # yfinance exposes several transport exceptions
            raise MarketDataUnavailableError(
                "Market data is temporarily unavailable. Please try again."
            ) from exc

        if raw is None or raw.empty:
            raise InvalidTickerError(normalized)

        if isinstance(raw.columns, pd.MultiIndex):
            has_adjusted_close = "Adj Close" in raw.columns.get_level_values(0)
        else:
            has_adjusted_close = "Adj Close" in raw.columns
        prices = self._extract_adjusted_close(raw, normalized)
        missing = [ticker for ticker in normalized if ticker not in prices.columns]
        empty = [ticker for ticker in prices.columns if prices[ticker].dropna().empty]
        invalid = sorted(set(missing + empty))
        if invalid:
            raise InvalidTickerError(invalid)

        prices = prices[normalized].sort_index()
        prices.index = pd.to_datetime(prices.index).tz_localize(None)
        original_counts = prices.notna().sum()

        # Short exchange-specific gaps are forward-filled. Remaining rows are
        # restricted to the common date range so portfolio returns are aligned.
        prices = prices.ffill(limit=3).dropna(how="any")
        if len(prices) < 60:
            raise InsufficientHistoryError(
                "Fewer than 60 aligned trading days are available for this portfolio."
            )

        warnings: list[str] = []
        if not has_adjusted_close:
            warnings.append(
                "Yahoo Finance did not provide adjusted closes; unadjusted Close was used. "
                "Dividend and split treatment may differ."
            )
        for ticker, count in original_counts.items():
            if count < 252:
                warnings.append(
                    f"{ticker} has only {int(count)} observations; estimates may be less stable."
                )
        if len(prices) < int(original_counts.max()):
            warnings.append(
                "Assets had mismatched histories; analytics use their common aligned date range."
            )

        result = PriceHistory(
            prices=prices.astype(float), source="Yahoo Finance", warnings=warnings
        )
        with self._lock:
            # DataFrames and lists remain mutable inside a frozen dataclass. Keep
            # a private snapshot so a caller cannot corrupt subsequent analyses.
            self._cache[key] = (datetime.now(UTC), self._copy_history(result))
        return self._copy_history(result)

    @staticmethod
    def _copy_history(history: PriceHistory) -> PriceHistory:
        """Return an isolated snapshot of mutable cached market-data fields."""

        return PriceHistory(
            prices=history.prices.copy(deep=True),
            source=history.source,
            warnings=list(history.warnings),
        )

    @staticmethod
    def _extract_adjusted_close(raw: pd.DataFrame, tickers: list[str]) -> pd.DataFrame:
        if isinstance(raw.columns, pd.MultiIndex):
            level_zero = set(raw.columns.get_level_values(0))
            field = "Adj Close" if "Adj Close" in level_zero else "Close"
            extracted = raw[field]
            if isinstance(extracted, pd.Series):
                return extracted.to_frame(name=tickers[0])
            return extracted.rename(columns=str.upper)

        field = "Adj Close" if "Adj Close" in raw.columns else "Close"
        if field not in raw.columns:
            return pd.DataFrame(index=raw.index)
        return raw[field].to_frame(name=tickers[0])


_provider: MarketDataProvider = YahooFinanceProvider()


def get_market_data_provider() -> MarketDataProvider:
    """FastAPI dependency hook, replaceable in tests and future deployments."""

    return _provider
