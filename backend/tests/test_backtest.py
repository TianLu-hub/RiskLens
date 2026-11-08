"""Walk-forward chronology, accounting, and API validation."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import Mock

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.data.market_data import (
    MarketDataProvider,
    MarketDataUnavailableError,
    PriceHistory,
    YahooFinanceProvider,
    get_market_data_provider,
)
from app.main import app
from app.models.backtest import BacktestRequest
from app.optimization.backtest import _Account, backtest_portfolio


class BacktestProvider(MarketDataProvider):
    def __init__(self, future_multiplier: float = 1.0, days: int = 580) -> None:
        self.future_multiplier = future_multiplier
        self.days = days

    def get_adjusted_prices(
        self, tickers: list[str], start: datetime, end: datetime
    ) -> PriceHistory:
        index = pd.bdate_range("2023-01-02", periods=self.days)
        time = np.arange(self.days)
        prices = pd.DataFrame(index=index)
        for offset, ticker in enumerate(tickers):
            daily = (
                0.00025
                + 0.0001 * offset
                + (0.003 + 0.001 * offset) * np.sin(time / (7 + offset))
            )
            if self.future_multiplier != 1:
                daily[254:] *= self.future_multiplier
            prices[ticker] = 100 * np.cumprod(1 + daily)
        return PriceHistory(prices=prices, source="Synthetic Test Data", warnings=[])


def request(**overrides: object) -> BacktestRequest:
    payload = {
        "positions": [
            {"ticker": "AAPL", "weight": 0.5},
            {"ticker": "SPY", "weight": 0.5},
        ],
        "lookback_years": 3,
        "training_days": 252,
        "rebalance_days": 21,
        "cost_bps": 10,
        "objective": "minimum_volatility",
    }
    payload.update(overrides)
    return BacktestRequest.model_validate(payload)


def test_first_fold_never_sees_future_returns() -> None:
    normal = backtest_portfolio(request(), BacktestProvider())
    changed_future = backtest_portfolio(
        request(), BacktestProvider(future_multiplier=2)
    )
    first = normal.folds[0]
    assert first.train_end < first.test_start
    assert first.optimized_weights == pytest.approx(
        changed_future.folds[0].optimized_weights
    )
    assert normal.series[0].date == first.test_start
    assert normal.series[-1].date == normal.folds[-1].test_end
    assert len(normal.series) == normal.data_quality.observations - normal.training_days
    assert normal.spy_buy_and_hold is not None


def test_trade_cost_uses_total_traded_notional() -> None:
    account = _Account(wealth=1.0, weights=np.array([0.5, 0.5]))
    turnover = account.rebalance(np.array([1.0, 0.0]), cost_bps=10)
    assert turnover == pytest.approx(0.5)
    assert account.costs == pytest.approx(0.001)
    account.advance(np.array([0.1, 0.0]))
    assert account.wealth == pytest.approx(0.999 * 1.1)


def test_zero_costs_and_fold_reconciliation() -> None:
    result = backtest_portfolio(request(cost_bps=0), BacktestProvider())
    assert result.optimized.total_cost_fraction_of_initial_capital == 0
    assert result.current.total_cost_fraction_of_initial_capital == 0
    assert result.optimized.total_one_way_turnover == pytest.approx(
        sum(fold.optimized_one_way_turnover for fold in result.folds)
    )
    assert result.optimized.final_wealth == pytest.approx(
        result.series[-1].optimized_wealth
    )
    assert result.current.final_wealth == pytest.approx(
        result.series[-1].current_wealth
    )
    assert result.spy_buy_and_hold.final_wealth == pytest.approx(
        result.series[-1].spy_wealth
    )


def test_backtest_api_and_insufficient_history() -> None:
    app.dependency_overrides[get_market_data_provider] = lambda: BacktestProvider()
    client = TestClient(app)
    try:
        response = client.post("/portfolio/backtest", json=request().model_dump())
        assert response.status_code == 200
        data = response.json()
        assert data["data_quality"]["source"] == "Synthetic Test Data"
        assert data["folds"][0]["train_end"] < data["folds"][0]["test_start"]
        assert data["optimized"]["total_cost_fraction_of_initial_capital"] >= 0

        short = client.post(
            "/portfolio/backtest", json=request(training_days=560).model_dump()
        )
        assert short.status_code == 422
        assert short.json()["detail"]["code"] == "INSUFFICIENT_HISTORY"
    finally:
        app.dependency_overrides.clear()


def test_invalid_configuration_rejected() -> None:
    client = TestClient(app)
    response = client.post(
        "/portfolio/backtest", json=request().model_dump() | {"cost_bps": -1}
    )
    assert response.status_code == 422


@pytest.mark.parametrize(
    "problem",
    [
        "unsorted",
        "duplicate_date",
        "same_day",
        "missing_date",
        "numeric_index",
        "missing_ticker",
        "duplicate_ticker",
        "missing_price",
        "zero_price",
        "negative_price",
        "infinite_price",
        "boolean_price",
        "string_price",
        "overflow_return",
    ],
)
def test_malformed_history_is_rejected_before_returns_or_optimization(
    monkeypatch, problem
):
    provider = Mock(spec=MarketDataProvider)
    prices = (
        BacktestProvider()
        .get_adjusted_prices(
            ["AAPL", "SPY"], datetime(2023, 1, 1), datetime(2026, 1, 1)
        )
        .prices
    )
    if problem == "unsorted":
        prices = prices.iloc[::-1]
    elif problem in {"duplicate_date", "same_day", "missing_date"}:
        index = list(prices.index)
        index[10] = (
            pd.NaT
            if problem == "missing_date"
            else index[9] + pd.Timedelta(hours=1 if problem == "same_day" else 0)
        )
        prices.index = pd.DatetimeIndex(index)
    elif problem == "numeric_index":
        prices.index = pd.RangeIndex(len(prices))
    elif problem == "missing_ticker":
        prices = prices.drop(columns="SPY")
    elif problem == "duplicate_ticker":
        prices.columns = ["AAPL", "AAPL"]
    elif problem == "boolean_price":
        prices["AAPL"] = True
    elif problem == "string_price":
        prices["AAPL"] = "100"
    elif problem == "overflow_return":
        prices.iloc[9, 0] = 1e-300
        prices.iloc[10, 0] = 1e300
    else:
        prices.iloc[10, 0] = {
            "missing_price": np.nan,
            "zero_price": 0,
            "negative_price": -1,
            "infinite_price": np.inf,
        }[problem]
    original = prices.copy(deep=True)
    provider.get_adjusted_prices.return_value = PriceHistory(
        prices=prices, source="Synthetic Test Data", warnings=[]
    )
    optimize = Mock(
        side_effect=AssertionError("Invalid history must not reach optimization")
    )
    monkeypatch.setattr("app.optimization.backtest.optimize_weights", optimize)
    if problem != "overflow_return":
        monkeypatch.setattr(
            "app.optimization.backtest.daily_returns",
            Mock(
                side_effect=AssertionError(
                    "Validate history before calculating returns"
                )
            ),
        )
    with pytest.raises(MarketDataUnavailableError, match="invalid price history"):
        backtest_portfolio(request(), provider)
    monkeypatch.setitem(
        app.dependency_overrides, get_market_data_provider, lambda: provider
    )
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post("/portfolio/backtest", json=request().model_dump())
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "MARKET_DATA_UNAVAILABLE"
    optimize.assert_not_called()
    pd.testing.assert_frame_equal(prices, original)


@pytest.mark.parametrize("days", [0, 1])
def test_empty_or_single_price_is_insufficient_history_not_server_error(
    monkeypatch, days
):
    provider = BacktestProvider(days=days)
    monkeypatch.setitem(
        app.dependency_overrides, get_market_data_provider, lambda: provider
    )
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post("/portfolio/backtest", json=request().model_dump())
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "INSUFFICIENT_HISTORY"


def test_unadjusted_price_fallback_is_disclosed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    index = pd.bdate_range("2025-01-02", periods=70)
    raw = pd.DataFrame({"Close": np.linspace(100, 110, len(index))}, index=index)
    monkeypatch.setattr("app.data.market_data.yf.download", lambda *args, **kwargs: raw)
    history = YahooFinanceProvider().get_adjusted_prices(
        ["SPY"], datetime(2025, 1, 1), datetime(2025, 6, 1)
    )
    assert any("unadjusted Close" in warning for warning in history.warnings)
