"""Historical VaR chronology, arithmetic, input validation, and HTTP behavior."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.data.market_data import (
    InsufficientHistoryError,
    InvalidTickerError,
    MarketDataProvider,
    MarketDataUnavailableError,
    PriceHistory,
    get_market_data_provider,
)
from app.data.provenance import AssetCoverage, MarketDataProvenance
from app.main import app
from app.models.var_backtest import VarBacktestRequest
from app.risk.var import historical_var
from app.risk.var_backtest import backtest_var_portfolio, rolling_var_backtest


def return_frame(days: int = 100) -> pd.DataFrame:
    time = np.arange(days)
    return pd.DataFrame(
        {"AAPL": 0.001 + 0.02 * np.sin(time), "TLT": 0.002 + 0.01 * np.cos(time)},
        index=pd.bdate_range("2024-01-02", periods=days),
    )


def request(**overrides: object) -> VarBacktestRequest:
    payload = {
        "positions": [
            {"ticker": "TLT", "weight": 0.75},
            {"ticker": "AAPL", "weight": 0.25},
        ],
        "lookback_years": 3,
        "window_days": 60,
        "confidence_level": 0.95,
    }
    payload.update(overrides)
    return VarBacktestRequest.model_validate(payload)


class VarProvider(MarketDataProvider):
    def __init__(self, days: int = 100, *, metadata: bool = False) -> None:
        returns = return_frame(days)
        self.prices = pd.concat(
            [
                pd.DataFrame(
                    {ticker: [100.0] for ticker in returns.columns},
                    index=[returns.index[0] - pd.offsets.BDay()],
                ),
                100 * (1 + returns).cumprod(),
            ]
        )
        self.warnings = ["Provider alignment warning."]
        self.calls: list[tuple[list[str], datetime, datetime]] = []
        self.provenance = (
            MarketDataProvenance(
                data_type="synthetic",
                fetched_at=datetime(2025, 1, 1, tzinfo=UTC),
                cache_hit=True,
                cache_ttl_seconds=900,
                price_basis="unadjusted_close",
                price_start_date=self.prices.index[0].date().isoformat(),
                price_end_date=self.prices.index[-1].date().isoformat(),
                raw_price_rows=days + 3,
                aligned_price_rows=days + 1,
                dropped_price_rows=2,
                forward_fill_limit=3,
                assets=[
                    AssetCoverage(
                        ticker=ticker,
                        observed_prices=days + 1,
                        missing_prices=2,
                        filled_prices=1,
                        first_observed_date=self.prices.index[0].date().isoformat(),
                        last_observed_date=self.prices.index[-1].date().isoformat(),
                    )
                    for ticker in self.prices.columns
                ],
            )
            if metadata
            else None
        )

    def get_adjusted_prices(
        self, tickers: list[str], start: datetime, end: datetime
    ) -> PriceHistory:
        self.calls.append((tickers, start, end))
        # The provider's column order intentionally differs from the request.
        return PriceHistory(
            prices=self.prices[sorted(tickers)],
            source="Synthetic Test Data",
            warnings=self.warnings,
            provenance=self.provenance,
        )


@pytest.fixture(autouse=True)
def reset_provider_override():
    yield
    app.dependency_overrides.pop(get_market_data_provider, None)


def test_weighted_returns_use_current_weights_every_day_and_column_order() -> None:
    provider = VarProvider()
    result = backtest_var_portfolio(request(), provider)
    returns = return_frame()
    expected = returns.AAPL * 0.25 + returns.TLT * 0.75
    assert [point.realized_return for point in result.series] == pytest.approx(
        expected.iloc[60:].to_list()
    )
    assert result.series[0].var_loss == pytest.approx(
        historical_var(expected.iloc[:60], 0.95)
    )
    assert [point.realized_loss for point in result.series] == pytest.approx(
        (-expected.iloc[60:]).to_list()
    )
    assert len(provider.calls) == 1
    tickers, start, end = provider.calls[0]
    assert tickers == ["TLT", "AAPL"]
    assert end - start == timedelta(days=int(3 * 365.25) + 10)


def test_hand_computed_quantile_and_rolling_training_boundaries() -> None:
    # Sixty ordered returns from -3% to +2.9%: q_0.05 lies at rank 2.95,
    # interpolating between -2.8% and -2.7%, hence a 2.705% loss threshold.
    frame = pd.DataFrame(
        {"AAPL": np.concatenate((np.arange(60) * 0.001 - 0.03, np.full(20, -0.03)))},
        index=pd.bdate_range("2024-01-02", periods=80),
    )
    points = rolling_var_backtest(
        frame, np.array([1.0]), window_days=60, confidence_level=0.95
    )
    assert len(points) == 20
    assert points[0].var_loss == pytest.approx(0.02705)
    # The second window replaces the initial -3% observation with the test-day
    # -3% return, leaving the quantile unchanged while moving both date bounds.
    assert points[1].var_loss == pytest.approx(0.02705)
    for offset, point in enumerate(points):
        assert point.training_start == frame.index[offset].date().isoformat()
        assert point.training_end == frame.index[offset + 59].date().isoformat()
        assert point.date == frame.index[offset + 60].date().isoformat()
        assert point.training_end < point.date
    assert points[0].breach is True


def test_future_and_forecast_day_returns_never_change_earlier_forecasts() -> None:
    frame = return_frame(120)
    weights = np.array([0.25, 0.75])
    original = rolling_var_backtest(
        frame, weights, window_days=60, confidence_level=0.95
    )
    changed = frame.copy()
    changed.iloc[80:] = -0.8
    future = rolling_var_backtest(
        changed, weights, window_days=60, confidence_level=0.95
    )
    assert original[:20] == future[:20]
    assert original[20].var_loss == future[20].var_loss
    assert original[20].realized_return != future[20].realized_return

    changed.iloc[60] = -0.9
    forecast_day = rolling_var_backtest(
        changed, weights, window_days=60, confidence_level=0.95
    )
    assert original[0].var_loss == forecast_day[0].var_loss
    assert original[0].realized_return != forecast_day[0].realized_return


def test_strict_equality_is_not_a_breach() -> None:
    exact_return = -0.03125
    frame = pd.DataFrame(
        {"AAPL": np.full(80, exact_return)},
        index=pd.bdate_range("2024-01-02", periods=80),
    )
    frame.iloc[61, 0] = np.nextafter(exact_return, -np.inf)
    points = rolling_var_backtest(
        frame, np.array([1.0]), window_days=60, confidence_level=0.95
    )
    assert points[0].var_loss == points[0].realized_loss
    assert points[0].breach is False
    assert points[1].realized_loss > points[1].var_loss
    assert points[1].breach is True


@pytest.mark.parametrize("constant_return", [-0.02, 0.0, 0.02])
def test_zero_variance_retains_signed_threshold_and_has_no_equal_loss_breaches(
    constant_return: float,
) -> None:
    frame = pd.DataFrame(
        {"AAPL": np.full(80, constant_return)},
        index=pd.bdate_range("2024-01-02", periods=80),
    )
    points = rolling_var_backtest(
        frame, np.array([1.0]), window_days=60, confidence_level=0.95
    )
    assert all(point.var_loss == -constant_return for point in points)
    assert not any(point.breach for point in points)


def test_negative_var_can_be_breached_by_a_smaller_positive_return() -> None:
    frame = pd.DataFrame(
        {"AAPL": [0.02] * 60 + [0.01] * 20},
        index=pd.bdate_range("2024-01-02", periods=80),
    )
    first = rolling_var_backtest(
        frame, np.array([1.0]), window_days=60, confidence_level=0.95
    )[0]
    assert first.var_loss == -0.02
    assert first.realized_loss == -0.01
    assert first.breach is True


def test_summary_counts_rates_and_whole_sample_metadata_reconcile() -> None:
    result = backtest_var_portfolio(request(), VarProvider())
    assert result.method == "historical_simulation"
    assert result.forecast_horizon_days == 1
    assert result.test_observations == len(result.series) == 40
    assert result.breach_count == sum(point.breach for point in result.series)
    assert result.breach_rate == result.breach_count / result.test_observations
    assert result.expected_breach_rate == pytest.approx(0.05)
    assert result.expected_breach_count == pytest.approx(2.0)
    assert result.expected_breach_count == (
        result.test_observations * result.expected_breach_rate
    )
    assert result.test_start == result.series[0].date
    assert result.test_end == result.series[-1].date
    assert result.data_quality.observations == 100
    assert result.data_quality.observations == result.window_days + result.test_observations
    assert result.data_quality.start_date == return_frame().index[0].date().isoformat()
    assert result.data_quality.start_date < result.test_start
    assert result.data_quality.end_date == result.test_end
    assert result.data_quality.provenance is None
    assert "risk_free_rate input is unused" in result.methodology
    assert any("no statistical significance test" in item for item in result.limitations)


def test_inherited_risk_free_rate_does_not_change_raw_return_validation() -> None:
    low = backtest_var_portfolio(request(risk_free_rate=-0.1), VarProvider())
    high = backtest_var_portfolio(request(risk_free_rate=0.5), VarProvider())
    assert low.model_dump() == high.model_dump()


def test_small_sample_and_low_expected_count_warnings_preserve_provider_warnings() -> None:
    provider = VarProvider()
    result = backtest_var_portfolio(request(), provider)
    assert result.data_quality.warnings[0] == "Provider alignment warning."
    assert any("fewer than 252" in warning for warning in result.data_quality.warnings)
    assert any("below 5" in warning for warning in result.data_quality.warnings)
    assert provider.warnings == ["Provider alignment warning."]

    large = backtest_var_portfolio(request(), VarProvider(400))
    assert large.data_quality.warnings == ["Provider alignment warning."]
    high_confidence = backtest_var_portfolio(
        request(confidence_level=0.999), VarProvider(400)
    )
    assert any("below 5" in warning for warning in high_confidence.data_quality.warnings)


@pytest.mark.parametrize("days", [0, 1, 59, 60, 79])
def test_insufficient_history_requires_twenty_forecast_returns(days: int) -> None:
    with pytest.raises(InsufficientHistoryError, match="at least 20 out-of-sample"):
        rolling_var_backtest(
            return_frame(days), np.array([0.25, 0.75]), window_days=60, confidence_level=0.95
        )


@pytest.mark.parametrize("bad_value", [np.nan, np.inf, -np.inf])
def test_nonfinite_direct_returns_are_rejected(bad_value: float) -> None:
    frame = return_frame()
    frame.iloc[10, 0] = bad_value
    with pytest.raises(ValueError, match="finite"):
        rolling_var_backtest(
            frame, np.array([0.25, 0.75]), window_days=60, confidence_level=0.95
        )


@pytest.mark.parametrize("index_kind", ["duplicate", "unsorted", "missing", "numeric"])
def test_invalid_direct_return_dates_are_rejected(index_kind: str) -> None:
    frame = return_frame()
    if index_kind == "duplicate":
        index = frame.index.to_list()
        index[10] = index[9]
        frame.index = pd.DatetimeIndex(index)
    elif index_kind == "unsorted":
        frame = frame.iloc[::-1]
    elif index_kind == "missing":
        index = frame.index.to_list()
        index[10] = pd.NaT
        frame.index = pd.DatetimeIndex(index)
    else:
        frame.index = pd.RangeIndex(len(frame))
    with pytest.raises(ValueError, match="dates|DatetimeIndex"):
        rolling_var_backtest(
            frame, np.array([0.25, 0.75]), window_days=60, confidence_level=0.95
        )


@pytest.mark.parametrize(
    "weights",
    [np.array([1.0]), np.array([0.5, np.nan]), np.array([-0.2, 1.2]), np.array([0.1, 0.1])],
)
def test_invalid_direct_weights_are_rejected(weights: np.ndarray) -> None:
    with pytest.raises(ValueError, match="Weights"):
        rolling_var_backtest(
            return_frame(), weights, window_days=60, confidence_level=0.95
        )


@pytest.mark.parametrize(
    "overrides",
    [
        {"window_days": 59},
        {"window_days": 1261},
        {"window_days": 60.5},
        {"confidence_level": 0.89},
        {"confidence_level": 1.0},
        {"lookback_years": 0},
        {"positions": []},
        {"positions": [{"ticker": "AAPL", "weight": 0.8}]},
        {"positions": [{"ticker": "AAPL MSFT", "weight": 1}]},
        {"positions": [{"ticker": "AAPL", "weight": -1}]},
        {"positions": [{"ticker": "AAPL", "weight": 0.5}] * 2},
    ],
)
def test_invalid_request_configuration_rejected_before_provider_fetch(
    overrides: dict[str, object],
) -> None:
    provider = VarProvider()
    app.dependency_overrides[get_market_data_provider] = lambda: provider
    with pytest.raises(ValidationError):
        request(**overrides)
    response = TestClient(app).post(
        "/portfolio/var-backtest", json=request().model_dump() | overrides
    )
    assert response.status_code == 422
    assert provider.calls == []


def test_default_window_matches_analysis_request_defaults() -> None:
    payload = VarBacktestRequest(positions=[{"ticker": "spy", "weight": 1}])
    assert payload.positions[0].ticker == "SPY"
    assert payload.window_days == 252
    assert payload.lookback_years == 3
    assert payload.confidence_level == 0.95


def test_api_success_preserves_provenance_and_actual_sample() -> None:
    provider = VarProvider(metadata=True)
    before = provider.provenance.model_dump(mode="json")
    app.dependency_overrides[get_market_data_provider] = lambda: provider
    response = TestClient(app).post("/portfolio/var-backtest", json=request().model_dump())
    assert response.status_code == 200
    payload = response.json()
    assert payload["data_quality"]["source"] == "Synthetic Test Data"
    assert payload["data_quality"]["observations"] == 100
    assert payload["data_quality"]["provenance"] == before
    assert provider.provenance.model_dump(mode="json") == before
    assert payload["test_observations"] == 40
    assert payload["series"][0]["training_end"] < payload["test_start"]
    assert payload["series"][-1]["date"] == payload["test_end"]


def test_api_insufficient_history_returns_clear_error() -> None:
    app.dependency_overrides[get_market_data_provider] = lambda: VarProvider(79)
    response = TestClient(app).post("/portfolio/var-backtest", json=request().model_dump())
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "INSUFFICIENT_HISTORY"
    assert "at least 20 out-of-sample" in response.json()["detail"]["message"]


@pytest.mark.parametrize(
    "problem",
    [
        "zero",
        "negative",
        "nan",
        "inf",
        "negative_inf",
        "text",
        "boolean",
        "complex",
        "missing_date",
        "duplicate_date",
        "unsorted_dates",
        "numeric_dates",
        "missing_ticker",
        "duplicate_ticker",
    ],
)
def test_invalid_provider_prices_return_structured_503_before_computing_returns(
    problem: str, monkeypatch: pytest.MonkeyPatch,
) -> None:
    class MalformedProvider(VarProvider):
        def get_adjusted_prices(
            self, tickers: list[str], start: datetime, end: datetime
        ) -> PriceHistory:
            return PriceHistory(
                prices=self.prices, source="Synthetic Test Data", warnings=[]
            )

    provider = MalformedProvider()
    invalid_values = {
        "zero": 0.0,
        "negative": -1.0,
        "nan": np.nan,
        "inf": np.inf,
        "negative_inf": -np.inf,
    }
    if problem in invalid_values:
        provider.prices.iloc[10, 0] = invalid_values[problem]
    elif problem == "text":
        provider.prices = provider.prices.astype(object)
        provider.prices.iloc[10, 0] = "invalid price"
    elif problem == "boolean":
        provider.prices["AAPL"] = True
    elif problem == "complex":
        provider.prices["AAPL"] = provider.prices.AAPL.astype(complex)
    elif problem in {"missing_date", "duplicate_date"}:
        dates = provider.prices.index.to_list()
        dates[10] = pd.NaT if problem == "missing_date" else dates[9]
        provider.prices.index = pd.DatetimeIndex(dates)
    elif problem == "unsorted_dates":
        provider.prices = provider.prices.iloc[::-1]
    elif problem == "numeric_dates":
        provider.prices.index = pd.RangeIndex(len(provider.prices))
    elif problem == "missing_ticker":
        provider.prices = provider.prices[["TLT"]]
    elif problem == "duplicate_ticker":
        provider.prices = provider.prices[["AAPL", "AAPL", "TLT"]]
    original = provider.prices.copy(deep=True)

    def unexpected_returns_calculation(*args, **kwargs):
        pytest.fail("Malformed provider prices must be rejected before daily_returns")

    monkeypatch.setattr(
        "app.risk.var_backtest.daily_returns", unexpected_returns_calculation
    )
    with pytest.raises(MarketDataUnavailableError, match="invalid price history"):
        backtest_var_portfolio(request(), provider)

    app.dependency_overrides[get_market_data_provider] = lambda: provider
    response = TestClient(app).post("/portfolio/var-backtest", json=request().model_dump())
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "MARKET_DATA_UNAVAILABLE"
    assert "invalid price history" in response.json()["detail"]["message"]
    pd.testing.assert_frame_equal(provider.prices, original)


def test_finite_prices_that_overflow_daily_returns_return_structured_503() -> None:
    provider = VarProvider()
    provider.prices.iloc[10, 0] = np.finfo(float).tiny
    provider.prices.iloc[11, 0] = np.finfo(float).max
    app.dependency_overrides[get_market_data_provider] = lambda: provider
    response = TestClient(app).post("/portfolio/var-backtest", json=request().model_dump())
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "MARKET_DATA_UNAVAILABLE"
    assert "finite daily returns" in response.json()["detail"]["message"]


@pytest.mark.parametrize("price_rows", [0, 1])
def test_short_valid_provider_history_still_returns_insufficient_history(
    price_rows: int,
) -> None:
    provider = VarProvider()
    provider.prices = provider.prices.iloc[:price_rows]
    app.dependency_overrides[get_market_data_provider] = lambda: provider
    response = TestClient(app).post("/portfolio/var-backtest", json=request().model_dump())
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "INSUFFICIENT_HISTORY"


@pytest.mark.parametrize(
    ("error", "status", "code"),
    [
        (InvalidTickerError(["AAPL"]), 422, "INVALID_TICKER"),
        (MarketDataUnavailableError("Provider unavailable"), 503, "MARKET_DATA_UNAVAILABLE"),
    ],
)
def test_api_provider_errors_are_user_safe(
    error: Exception, status: int, code: str,
) -> None:
    class ErrorProvider(MarketDataProvider):
        def get_adjusted_prices(
            self, tickers: list[str], start: datetime, end: datetime
        ) -> PriceHistory:
            raise error

    app.dependency_overrides[get_market_data_provider] = ErrorProvider
    response = TestClient(app).post("/portfolio/var-backtest", json=request().model_dump())
    assert response.status_code == status
    assert response.json()["detail"]["code"] == code
    if code == "INVALID_TICKER":
        assert response.json()["detail"]["tickers"] == ["AAPL"]
