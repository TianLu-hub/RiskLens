"""Rolling historical VaR forecasts evaluated only on subsequent daily returns."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import numpy as np
import pandas as pd
from pandas.api.types import is_bool_dtype, is_complex_dtype, is_numeric_dtype

from app.data.market_data import (
    InsufficientHistoryError,
    MarketDataProvider,
    MarketDataUnavailableError,
)
from app.models.portfolio import WEIGHT_TOLERANCE
from app.models.responses import DataQuality
from app.models.var_backtest import (
    VarBacktestPoint,
    VarBacktestRequest,
    VarBacktestResponse,
)
from app.risk.metrics import TRADING_DAYS, daily_returns, portfolio_returns
from app.risk.var import historical_var

MIN_TEST_OBSERVATIONS = 20


def rolling_var_backtest(
    asset_returns: pd.DataFrame,
    weights: np.ndarray,
    *,
    window_days: int,
    confidence_level: float,
) -> list[VarBacktestPoint]:
    """Forecast from [t - window_days:t], then compare the loss observed at t.

    Weights are in the same order as the return columns and remain fixed for every
    day, modeling daily rebalancing. Inputs are validated without sorting, filling,
    or dropping observations so the training chronology stays explicit.
    """

    _validate_inputs(asset_returns, weights, window_days, confidence_level)
    required = window_days + MIN_TEST_OBSERVATIONS
    if len(asset_returns) < required:
        raise InsufficientHistoryError(
            f"Need at least {required} aligned daily returns: {window_days} training "
            f"observations and at least {MIN_TEST_OBSERVATIONS} out-of-sample returns. "
            f"Received {len(asset_returns)}. Select a longer lookback or shorter VaR window."
        )

    returns = portfolio_returns(asset_returns, weights)
    points: list[VarBacktestPoint] = []
    for test_index in range(window_days, len(returns)):
        training = returns.iloc[test_index - window_days : test_index]
        var_loss = historical_var(training, confidence_level)
        realized_return = float(returns.iloc[test_index])
        realized_loss = -realized_return
        points.append(
            VarBacktestPoint(
                date=returns.index[test_index].date().isoformat(),
                training_start=training.index[0].date().isoformat(),
                training_end=training.index[-1].date().isoformat(),
                var_loss=var_loss,
                realized_return=realized_return,
                realized_loss=realized_loss,
                breach=realized_loss > var_loss,
            )
        )
    return points


def backtest_var_portfolio(
    request: VarBacktestRequest, provider: MarketDataProvider
) -> VarBacktestResponse:
    """Fetch aligned history and evaluate the current portfolio's one-day VaR."""

    tickers = [position.ticker for position in request.positions]
    weights = np.asarray(
        [position.weight for position in request.positions], dtype=float
    )
    end = datetime.now(UTC)
    start = end - timedelta(days=int(request.lookback_years * 365.25) + 10)
    history = provider.get_adjusted_prices(tickers, start, end)
    prices = _validated_provider_prices(history.prices, tickers)
    if len(prices) < 2:
        raise InsufficientHistoryError(
            "At least two aligned prices are needed to calculate a daily return; "
            f"VaR validation requires {request.window_days} training observations and "
            f"at least {MIN_TEST_OBSERVATIONS} out-of-sample returns."
        )
    returns = daily_returns(prices)
    if not np.isfinite(returns.to_numpy(dtype=float)).all():
        raise MarketDataUnavailableError(
            "The market data provider returned invalid price history: "
            "prices cannot produce finite daily returns. Please try again."
        )
    points = rolling_var_backtest(
        returns,
        weights,
        window_days=request.window_days,
        confidence_level=request.confidence_level,
    )
    test_observations = len(points)
    breach_count = sum(point.breach for point in points)
    expected_breach_rate = 1.0 - request.confidence_level
    expected_breach_count = test_observations * expected_breach_rate
    warnings = list(history.warnings)
    if test_observations < TRADING_DAYS:
        warnings.append(
            f"Only {test_observations} out-of-sample returns are available (fewer than "
            "252 trading days); the observed breach rate may be unstable."
        )
    if expected_breach_count < 5:
        warnings.append(
            f"The nominal expected breach count is {expected_breach_count:.2f}, below 5; "
            "this sample provides limited evidence about tail coverage."
        )

    return VarBacktestResponse(
        confidence_level=request.confidence_level,
        window_days=request.window_days,
        test_observations=test_observations,
        breach_count=breach_count,
        expected_breach_count=expected_breach_count,
        breach_rate=breach_count / test_observations,
        expected_breach_rate=expected_breach_rate,
        test_start=points[0].date,
        test_end=points[-1].date,
        series=points,
        data_quality=DataQuality(
            source=history.source,
            observations=len(returns),
            start_date=returns.index[0].date().isoformat(),
            end_date=returns.index[-1].date().isoformat(),
            requested_lookback_years=request.lookback_years,
            warnings=warnings,
            provenance=history.provenance,
        ),
        methodology=(
            "For each test day, estimate one-day historical VaR using only the preceding "
            "window_days aligned portfolio returns, excluding that test day's return. "
            "Use the negative (1 - confidence_level) sample quantile with linear interpolation. "
            "Current weights are fixed and rebalanced daily, without trading costs. "
            "A breach occurs strictly when realized_loss = -realized_return exceeds var_loss; "
            "equality is not a breach and negative VaR values are retained. "
            "Returns and loss thresholds are fractions of portfolio value. "
            "The inherited risk_free_rate input is unused because VaR uses raw returns."
        ),
        limitations=[
            "Historical hypothetical validation does not guarantee future risk coverage or performance.",
            "Current holdings and weights were selected today and can embed hindsight or survivorship bias.",
            "Daily rebalancing excludes transaction costs, taxes, spreads, slippage, and market impact.",
            "Overlapping training windows and dependent returns limit interpretation of breach counts; "
            "no statistical significance test or pass/fail judgment is provided.",
            "Historical sample quantiles have limited tail resolution, especially at high confidence "
            "levels, and may miss losses beyond the observed sample.",
        ],
    )


def _validated_provider_prices(
    prices: pd.DataFrame, tickers: list[str]
) -> pd.DataFrame:
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


def _validate_inputs(
    returns: pd.DataFrame,
    weights: np.ndarray,
    window_days: int,
    confidence_level: float,
) -> None:
    if (
        isinstance(window_days, bool)
        or not isinstance(window_days, (int, np.integer))
        or not 60 <= window_days <= 1260
    ):
        raise ValueError("VaR window must be an integer between 60 and 1260 days")
    if not np.isfinite(confidence_level) or not 0.90 <= confidence_level <= 0.999:
        raise ValueError("Confidence level must be between 0.90 and 0.999")
    if not isinstance(returns.index, pd.DatetimeIndex) or returns.index.hasnans:
        raise ValueError("Daily returns must have a valid DatetimeIndex")
    if (
        not returns.index.normalize().is_unique
        or not returns.index.is_monotonic_increasing
    ):
        raise ValueError("Daily return dates must be unique and sorted in increasing order")
    if returns.shape[1] == 0 or not returns.columns.is_unique:
        raise ValueError("Daily returns must contain unique asset columns")
    if not np.isfinite(returns.to_numpy(dtype=float)).all():
        raise ValueError("Daily returns must contain only finite values")
    if (
        weights.ndim != 1
        or len(weights) != returns.shape[1]
        or not np.isfinite(weights).all()
        or (weights < 0).any()
        or (weights > 1).any()
        or abs(float(weights.sum()) - 1.0) > WEIGHT_TOLERANCE
    ):
        raise ValueError("Weights must match the asset columns, be long-only, and sum to 1.0")
