"""Replaceable market-data access with validation, alignment, and TTL caching."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections import OrderedDict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from threading import Lock

import pandas as pd
import yfinance as yf

from app.data.provenance import AssetCoverage, MarketDataProvenance


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
    provenance: MarketDataProvenance | None = None


class MarketDataProvider(ABC):
    """Interface implemented by all future price-history providers."""

    @abstractmethod
    def get_adjusted_prices(
        self, tickers: list[str], start: datetime, end: datetime
    ) -> PriceHistory:
        """Return aligned adjusted closing prices for all requested tickers."""


class YahooFinanceProvider(MarketDataProvider):
    """Yahoo Finance implementation isolated behind the provider interface."""

    def __init__(
        self,
        cache_ttl: timedelta = timedelta(minutes=15),
        *,
        max_cache_entries: int = 128,
    ) -> None:
        if max_cache_entries < 1:
            raise ValueError("max_cache_entries must be positive")
        self.cache_ttl = cache_ttl
        self.max_cache_entries = max_cache_entries
        self._cache: OrderedDict[
            tuple[tuple[str, ...], str, str], tuple[datetime, PriceHistory]
        ] = OrderedDict()
        self._lock = Lock()

    def get_adjusted_prices(
        self, tickers: list[str], start: datetime, end: datetime
    ) -> PriceHistory:
        normalized = sorted({ticker.strip().upper() for ticker in tickers})
        key = (tuple(normalized), start.date().isoformat(), end.date().isoformat())
        now = datetime.now(UTC)

        with self._lock:
            self._evict_expired(now)
            cached = self._cache.get(key)
            if cached:
                self._cache.move_to_end(key)
                return self._copy_history(cached[1], cache_hit=True)

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

        fetched_at = datetime.now(UTC)

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
        original_prices = prices.copy()

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

        coverage = [
            AssetCoverage(
                ticker=ticker,
                observed_prices=int(original_counts[ticker]),
                missing_prices=int(original_prices[ticker].isna().sum()),
                filled_prices=int(
                    original_prices.loc[prices.index, ticker].isna().sum()
                ),
                first_observed_date=original_prices[ticker]
                .first_valid_index()
                .date()
                .isoformat(),
                last_observed_date=original_prices[ticker]
                .last_valid_index()
                .date()
                .isoformat(),
            )
            for ticker in normalized
        ]

        result = PriceHistory(
            prices=prices.astype(float),
            source="Yahoo Finance",
            warnings=warnings,
            provenance=MarketDataProvenance(
                data_type="historical",
                fetched_at=fetched_at,
                cache_hit=False,
                cache_ttl_seconds=max(0, int(self.cache_ttl.total_seconds())),
                price_basis="adjusted_close"
                if has_adjusted_close
                else "unadjusted_close",
                price_start_date=prices.index[0].date().isoformat(),
                price_end_date=prices.index[-1].date().isoformat(),
                raw_price_rows=len(original_prices),
                aligned_price_rows=len(prices),
                dropped_price_rows=len(original_prices) - len(prices),
                forward_fill_limit=3,
                assets=coverage,
            ),
        )
        with self._lock:
            # Other requests may have filled the cache during this download.
            # Prune and enforce capacity under the same lock as insertion.
            self._evict_expired(datetime.now(UTC))
            # DataFrames and lists remain mutable inside a frozen dataclass. Keep
            # a private snapshot so a caller cannot corrupt subsequent analyses.
            self._cache[key] = (fetched_at, self._copy_history(result))
            self._cache.move_to_end(key)
            while len(self._cache) > self.max_cache_entries:
                self._cache.popitem(last=False)
        return self._copy_history(result)

    def _evict_expired(self, now: datetime) -> None:
        """Release expired snapshots on access; caller must hold self._lock.

        LRU order is not timestamp order: a hit changes recency, not fetch time.
        Scan the bounded cache so a recently used but expired entry is removed too.
        """

        expired = [
            key
            for key, (fetched_at, _) in self._cache.items()
            if now - fetched_at >= self.cache_ttl
        ]
        for key in expired:
            del self._cache[key]

    @staticmethod
    def _copy_history(
        history: PriceHistory, *, cache_hit: bool = False
    ) -> PriceHistory:
        """Return an isolated snapshot of mutable cached market-data fields."""

        return PriceHistory(
            prices=history.prices.copy(deep=True),
            source=history.source,
            warnings=list(history.warnings),
            provenance=(
                history.provenance.model_copy(
                    deep=True, update={"cache_hit": cache_hit}
                )
                if history.provenance is not None
                else None
            ),
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
